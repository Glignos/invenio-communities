# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Blueprint definitions."""

from __future__ import absolute_import, print_function

from flask_menu import current_menu
from flask.views import MethodView
from webargs.flaskparser import use_kwargs
from webargs import fields, validate
from invenio_db import db

from functools import wraps
from flask import Blueprint, abort, request, render_template, jsonify
from invenio_communities.records.api import CommunityRecordsAPI
from flask_security import current_user
from sqlalchemy.exc import SQLAlchemyError
from invenio_records_rest.errors import PIDResolveRESTError

from .models import RecordMember, recordInclusionRequest
from ..members.models import CommunityMember, MembershipRequest


def create_blueprint_from_app(app):
    community_records_rest_blueprint = Blueprint(
        'invenio_communities',
        __name__,
        template_folder="templates",
    )
    comm_view = CommunityRecordResource.as_view(
        'community_records_api'

    )
    community_records_rest_blueprint.add_url_rule(
        '/communities/<{0}:pid_value>/records'.format(
            'pid(comid,record_class="invenio_communities.api:Record")'
        ),
        view_func=comm_view,
    )

    request_management_view = RecordRequestsResource.as_view(
        'community_record_requests_management_api'

    )
    community_records_rest_blueprint.add_url_rule(
        '/communities/<{0}:pid_value>/records/requests'.format(
            'pid(comid,record_class="invenio_communities.api:Record")'),
        view_func=request_management_view,
    )

    request_view = recordshipRequestResource.as_view(
        'community_record_requests_api'
    )
    community_records_rest_blueprint.add_url_rule(
        '/communities/records/requests/<community_record_request_id>',
        view_func=request_view,
    )
    return community_records_rest_blueprint


def pass_community(f):
    """Decorator to retrieve persistent identifier and community.
    This decorator will resolve the ``pid_value`` parameter from the route
    pattern and resolve it to a PID and a community, which are then available
    in the decorated function as ``pid`` and ``community`` kwargs respectively.
    """
    @wraps(f)
    def inner(self, pid_value, *args, **kwargs):
        try:
            comm_pid, community = request.view_args['pid_value'].data
            return f(self, comm_pid=comm_pid, community=community, *args, **kwargs)
        except SQLAlchemyError:
            raise PIDResolveRESTError(comm_pid)

    return inner


def pass_community_function(f):
    """Decorator to retrieve persistent identifier and community.
    This decorator will resolve the ``pid_value`` parameter from the route
    pattern and resolve it to a PID and a community, which are then available
    in the decorated function as ``comm_pid`` and ``community`` kwargs respectively.
    """
    @wraps(f)
    def inner(pid_value, *args, **kwargs):
        try:
            comm_pid, community = request.view_args['pid_value'].data
            return f(comm_pid=comm_pid, community=community, *args, **kwargs)
        except SQLAlchemyError:
            raise PIDResolveRESTError(comm_pid)

    return inner


class CommunityRecordResource(MethodView):
    post_args = {
        'pid_value': fields.Raw(
            location='json',
            required=True
        ),
        'pid_type': fields.Raw(
            location='json',
            required=True
        ),
        'invite_type': fields.Raw(
            location='json',
            required=True,
            validate=[validate.OneOf(['invitation', 'request'])]
        ),
        'comment': fields.Raw(
            location='json',
            required=False
        )

    }

    put_args = {
        'comment': fields.Raw(
            location='json',
            required=False
        ),
    }

    # TODO: change invite_type name
    @use_kwargs(post_args)
    @pass_community
    def post(self, pid_value, pid_type, community, comment=None,
             invite_type=None, **kwargs):
        user_id = int(current_user.get_id())
        if invite_type == 'invitation':
            admin_ids = \
                [admin.user.id for admin in CommunityMember.get_admins(
                    community.id)]
            if user_id not in admin_ids:
                abort(404)
            CommunityRecordsAPI.invite_record(
                community, pid_value, pid_type, user_id, comment)
        elif invite_type == 'request':
            CommunityRecordsAPI.join_community(
                community, pid_value, pid_type, user_id, comment)
        db.session.commit()
        return 'Success', 200

    @use_kwargs(put_args)
    @pass_community
    def put(self, user_id, comm_pid=None, Record=None,
            role=None, email=None):
        # TODO I really dislike having 1 view for both models
        admin_ids = \
            [admin.user.id for admin in RecordMember.get_admins(
                Record.id)]
        if int(current_user.get_id()) not in admin_ids:
            abort(404)
        member = CommunityRecordsAPI.modify_recordship(
            user_id, Record.id, role)
        if member:
            db.session.commit()
            return 'Oki', 200
        recordship_request = recordshipRequestAPI.modify_recordship_request(
            Record.id, email, role)
        if recordship_request:
            db.session.commit()
            return 'Oki', 200
        return 'Cant find it', 404

    @pass_community
    def get(self, comm_pid=None, Record=None):
        admin_ids = \
            [admin.user.id for admin in RecordMember.get_admins(
                Record.id)]
        if int(current_user.get_id()) not in admin_ids:
            abort(404)
        ui_records = []
        for member in CommunityRecordAPI.get_records(Record.id).all():
            add_member = {}
            add_member['user_id'] = str(member.user_id)
            add_member['email'] = member.user.email
            add_member['role'] = str(member.role.title)
            ui_records.append(add_member)
        return jsonify(ui_records), 200

    @use_kwargs(delete_args)
    @pass_community
    def delete(self, user_id=None, Record=None, comm_pid=None):
        admin_ids = \
            [admin.user.id for admin in RecordMember.get_admins(
                Record.id)]
        if int(current_user.get_id()) not in admin_ids:
            abort(404)
        CommunityRecordAPI.delete_member(Record.id, user_id)
        db.session.commit()
        return 'Oki', 204


class RecordRequestsResource(MethodView):
    post_args = {
        'response': fields.Raw(
            location='json',
            required=True,
            validate=[validate.OneOf(['accept', 'decline'])]
        ),
        'role': fields.Raw(
            location='json',
            required=False,
            validate=[validate.OneOf(['M', 'A', 'C'])]
        )
    }

    @pass_community
    def get(self, Record=None, comm_pid=None, outgoing_only=False,
            incoming_only=False, page_size=20):
        admin_ids = \
            [admin.user.id for admin in RecordMember.get_admins(
                Record.id)]
        if int(current_user.get_id()) not in admin_ids:
            abort(404)
        response_object = {}
        if not outgoing_only:
            count, requests = recordshipRequestAPI.get_record_incoming_requests(
                Record.id, page_size=page_size)
            response_object['inc_count'] = count
            response_object['inc_requests'] = []
            for req in requests:
                response_object['inc_requests'].append({
                    'email': req.email,
                    'req_id': req.id
                })
        if not incoming_only:
            count, requests = recordshipRequestAPI.get_record_outgoing_requests(
                Record.id, page_size=page_size)
            response_object['out_count'] = count
            response_object['out_requests'] = []
            for req in requests:
                response_object['out_requests'].append({
                    'email': req.email,
                    'req_id': req.id,
                    'role': str(req.role.title)
                })
        return jsonify(response_object), 200

    #Maybe we could add a POST method here regarding batch requests modifications

class recordshipRequestResource(MethodView):
    post_args = {
        'response': fields.Raw(
            location='json',
            required=True,
            validate=[validate.OneOf(['accept', 'decline'])]
        ),
        'role': fields.Raw(
            location='json',
            required=False,
            validate=[validate.OneOf(['M', 'A', 'C'])]
        )
    }

    put_args = {
        'role': fields.Raw(
            location='json',
            required=True,
            validate=[validate.OneOf(['M', 'A', 'C'])]
        )
    }

    def get(self, recordship_request_id):
        request, Record = recordshipRequestAPI.get_invitation(
            recordship_request_id)
        response_object = {}
        response_object['record_name'] = Record.json['title']
        response_object['record_id'] = Record.json['id']
        response_object['role'] = str(request.role.title)
        return jsonify(response_object), 200


    @use_kwargs(post_args)
    def post(self, recordship_request_id, response=None, role=None):
        if not current_user.is_authenticated:
            abort(404)
        user_id = int(current_user.get_id())
        request = recordshipRequest.query.get(recordship_request_id)
        if not (request.is_invite and current_user.email == request.email):
            record_admins = [admin.user.id for admin in
                                RecordMember.get_admins(request.comm_id)]
            if not (user_id in record_admins and not request.is_invite):
                abort(404)
        if response == 'accept':
            recordshipRequestAPI.accept_invitation(
                request, role, user_id)
        else:
            recordshipRequestAPI.decline_or_cancel_invitation(request.id)

        db.session.commit()
        return 'Cool', 200

    @use_kwargs(put_args)
    def put(self, recordship_request_id, role=None):
        if not current_user.is_authenticated:
            abort(404)
        request = recordshipRequest.query.get(recordship_request_id)
        record_admins = [admin.user.id for admin in
                            RecordMember.get_admins(request.comm_id)]
        if not (int(current_user.get_id()) in record_admins and request.is_invite):
            abort(404)
        request.role = role
        db.session.commit()
        return 'OK', 200

    def delete(self, recordship_request_id):
        if not current_user.is_authenticated:
            abort(404)
        user_id = int(current_user.get_id())
        request = recordshipRequest.query.get(recordship_request_id)
        if not (current_user.email == request.email and not request.is_invite):
            record_admins = [admin.user.id for admin in
                                RecordMember.get_admins(request.comm_id)]
            if not (user_id in record_admins and request.is_invite):
                abort(404)
        recordshipRequestAPI.decline_or_cancel_invitation(request.id)

        db.session.commit()
        return 'Cool', 204


ui_blueprint = Blueprint(
    'invenio_communities',
    __name__,
    template_folder='templates',
    static_folder='static',
)


@ui_blueprint.before_app_first_request
def init_menu():
    """Initialize menu before first request."""
    item = current_menu.submenu('main.communities')
    item.register(
        'invenio_communities.index',
        'Communities',
        order=3,
    )


@ui_blueprint.route('/communities/new')
def new():
    """Create a new Record."""
    return render_template('new.html')


@ui_blueprint.route('/communities/')
def index():
    """Search for a new Record."""
    return render_template('index.html')


@ui_blueprint.route('/communities/<{0}:pid_value>/settings'.format(
            'pid(comid,record_class="invenio_communities.api:Record",'
            'object_type="com")'))
@pass_community_function
def settings(Record, comm_pid):
    """Modify a Record."""
    return render_template('settings.html', Record=Record, comm_pid=comm_pid)


@ui_blueprint.route('/communities/<{0}:pid_value>/records'.format(
            'pid(comid,record_class="invenio_communities.api:Record",'
            'object_type="com")'))
@pass_community_function
def records(Record, comm_pid):
    """records of a Record."""
    return render_template('records.html', Record=Record, comm_pid=comm_pid)


@ui_blueprint.route('/communities/<{0}:pid_value>'.format(
            'pid(comid,record_class="invenio_communities.api:Record",'
            'object_type="com")'))
@pass_community_function
def record_page(Record, comm_pid):
    """records of a Record."""
    return render_template('record_page.html', Record=Record, comm_pid=comm_pid)


@ui_blueprint.route('/communities/requests/<id>')
def requests(id):
    """Requests of communities."""
    return render_template('request.html')
