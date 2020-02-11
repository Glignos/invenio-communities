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
from flask_security import current_user
from sqlalchemy.exc import SQLAlchemyError
from invenio_records_rest.errors import PIDResolveRESTError

from .api import CommunityMembersAPI, MembershipRequestAPI
from .models import CommunityMember, MembershipRequest


def create_blueprint_from_app(app):
    community_members_rest_blueprint = Blueprint(
        'invenio_communities',
        __name__,
        template_folder="../templates",
    )
    comm_view = CommunityMembersResource.as_view(
        'community_members_api'

    )
    community_members_rest_blueprint.add_url_rule(
        '/communities/<{0}:pid_value>/members'.format(
            'pid(comid,record_class="invenio_communities.api:Community",'
            'object_type="com")'),
        view_func=comm_view,
    )

    request_management_view = CommunityRequestsResource.as_view(
        'community_requests_management_api'

    )
    community_members_rest_blueprint.add_url_rule(
        '/communities/<{0}:pid_value>/members/requests'.format(
            'pid(comid,record_class="invenio_communities.api:Community",'
            'object_type="com")'),
        view_func=request_management_view,
    )

    request_view = MembershipRequestResource.as_view(
        'community_requests_api'
    )
    community_members_rest_blueprint.add_url_rule(
        '/communities/members/requests/<membership_request_id>',
        view_func=request_view,
    )
    return community_members_rest_blueprint


def pass_community(f):
    """Decorator to retrieve persistent identifier and community.
    This decorator will resolve the ``pid_value`` parameter from the route
    pattern and resolve it to a PID and a community, which are then available
    in the decorated function as ``pid`` and ``community`` kwargs respectively.
    """
    @wraps(f)
    def inner(self, pid_value, *args, **kwargs):
        try:
            pid, community = request.view_args['pid_value'].data
            return f(self, pid=pid, community=community, *args, **kwargs)
        except SQLAlchemyError:
            raise PIDResolveRESTError(pid)

    return inner


def pass_community_function(f):
    """Decorator to retrieve persistent identifier and community.
    This decorator will resolve the ``pid_value`` parameter from the route
    pattern and resolve it to a PID and a community, which are then available
    in the decorated function as ``pid`` and ``community`` kwargs respectively.
    """
    @wraps(f)
    def inner(pid_value, *args, **kwargs):
        try:
            pid, community = request.view_args['pid_value'].data
            return f(pid=pid, community=community, *args, **kwargs)
        except SQLAlchemyError:
            raise PIDResolveRESTError(pid)

    return inner


class CommunityMembersResource(MethodView):
    post_args = {
        'role': fields.Raw(
            location='json',
            required=False,
            validate=[validate.OneOf(['M', 'A', 'C'])]
        ),  # TODO add valid options
        'email': fields.Email(
            location='json',
            required=False
        ),
        'invite_type': fields.Raw(
            location='json',
            required=True,
            validate=[validate.OneOf(['invitation', 'request'])]
        )

    }

    put_args = {
        'role': fields.Raw(
            location='json',
            required=False,
            validate=[validate.OneOf(['M', 'A', 'C'])]
        ),  # TODO add valid options
        'user_id': fields.Raw(
            location='json',
            required=False
        ),
        'email': fields.Email(
            location='json',
            required=False
        ),
    }

    delete_args = {
        'user_id': fields.Raw(
            location='query',
            required=False
        ),
    }
    # TODO: change invite_type name
    @use_kwargs(post_args)
    @pass_community
    def post(self, email=None, pid=None, community=None, role=None,
             invite_type=None, **kwargs):
        if invite_type == 'invitation':
            admin_ids = \
                [admin.user.id for admin in CommunityMember.get_admins(
                    community.id)]
            if int(current_user.get_id()) not in admin_ids:
                abort(404)
            existing_membership_req = MembershipRequest.query.filter_by(
                    comm_id=community.id,
                    email=email
                    ).one_or_none()
            if existing_membership_req:
                abort(400, 'This is an already existing relationship.')
            CommunityMembersAPI.invite_member(community, email, role)
        elif invite_type == 'request':
            user_id = int(current_user.get_id())
            email = current_user.email
            CommunityMembersAPI.join_community(user_id, email, community)
        db.session.commit()
        return 'Succesfully Invited', 200

    # @use_kwargs(put_args)
    # @pass_community
    # def put(self, user_id, pid=None, community=None,
    #         role=None, email=None):
    #     # TODO I really dislike having 1 view for both models
    #     admin_ids = \
    #         [admin.user.id for admin in CommunityMember.get_admins(
    #             community.id)]
    #     if int(current_user.get_id()) not in admin_ids:
    #         abort(404)
    #     member = CommunityMembersAPI.modify_membership(
    #         user_id, community.id, role)
    #     if member:
    #         db.session.commit()
    #         return 'Succesfully edited', 200
    #     membership_request = MembershipRequestAPI.modify_membership_request(
    #         community.id, email, role)
    #     if membership_request:
    #         db.session.commit()
    #         return 'Succesfully edited', 200
    #     return 'The invite does not exist or it has already expired.', 404

    @pass_community
    def get(self, pid=None, community=None):
        admin_ids = \
            [admin.user.id for admin in CommunityMember.get_admins(
                community.id)]
        if int(current_user.get_id()) not in admin_ids:
            abort(404)
        ui_members = []
        for member in CommunityMembersAPI.get_members(community.id).all():
            add_member = {}
            add_member['user_id'] = str(member.user_id)
            add_member['email'] = member.user.email
            add_member['role'] = str(member.role.title)
            ui_members.append(add_member)
        return jsonify(ui_members), 200

    @use_kwargs(delete_args)
    @pass_community
    def delete(self, user_id=None, community=None, pid=None):
        admin_ids = \
            [admin.user.id for admin in CommunityMember.get_admins(
                community.id)]
        if int(current_user.get_id()) not in admin_ids:
            abort(404)
        CommunityMembersAPI.delete_member(community.id, user_id)
        db.session.commit()
        return 'Succesfully removed', 204


class CommunityRequestsResource(MethodView):
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
    def get(self, community=None, pid=None, outgoing_only=False,
            incoming_only=False, page_size=20):
        admin_ids = \
            [admin.user.id for admin in CommunityMember.get_admins(
                community.id)]
        if int(current_user.get_id()) not in admin_ids:
            abort(404)
        response_object = {}
        if not outgoing_only:
            count, requests = \
                MembershipRequestAPI.get_community_incoming_requests(
                    community.id, page_size=page_size)
            response_object['inc_count'] = count
            response_object['inc_requests'] = []
            for req in requests:
                response_object['inc_requests'].append({
                    'email': req.email,
                    'req_id': req.id
                })
        if not incoming_only:
            count, requests = \
                MembershipRequestAPI.get_community_outgoing_requests(
                    community.id, page_size=page_size)
            response_object['out_count'] = count
            response_object['out_requests'] = []
            for req in requests:
                response_object['out_requests'].append({
                    'email': req.email,
                    'req_id': req.id,
                    'role': str(req.role.title)
                })
        return jsonify(response_object), 200

    # Maybe we could add a POST method here for batch requests modifications


class MembershipRequestResource(MethodView):
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

    def get(self, membership_request_id):
        request, community = MembershipRequestAPI.get_invitation(
            membership_request_id)
        response_object = {}
        response_object['community_name'] = community.json['title']
        response_object['community_id'] = community.json['id']
        response_object['role'] = str(request.role.title)
        return jsonify(response_object), 200

    @use_kwargs(post_args)
    def post(self, membership_request_id, response=None, role=None):
        if not current_user.is_authenticated:
            abort(404)
        user_id = int(current_user.get_id())
        request = MembershipRequest.query.get(membership_request_id)
        if not request.is_invite:  # and current_user.email == request.email):
            community_admins = [admin.user.id for admin in
                                CommunityMember.get_admins(request.comm_id)]
            if not (user_id in community_admins and not request.is_invite):
                abort(404)
        if response == 'accept':
            MembershipRequestAPI.accept_invitation(
                request, role, user_id)
            db.session.commit()
            return 'Succesfully accepted.', 200
        else:
            MembershipRequestAPI.decline_or_cancel_invitation(request.id)
            db.session.commit()
            return 'Succesfully rejected.', 200

    @use_kwargs(put_args)
    def put(self, membership_request_id, role=None):
        if not current_user.is_authenticated:
            abort(404)
        request = MembershipRequest.query.get(membership_request_id)
        community_admins = [admin.user.id for admin in
                            CommunityMember.get_admins(request.comm_id)]
        if not (int(current_user.get_id()) in community_admins and
                request.is_invite):
            abort(404)
        request.role = role
        db.session.commit()
        return 'Succesfully modified invitaion.', 200

    def delete(self, membership_request_id):
        if not current_user.is_authenticated:
            abort(404)
        user_id = int(current_user.get_id())
        request = MembershipRequest.query.get(membership_request_id)
        if not (current_user.email == request.email and not request.is_invite):
            community_admins = [admin.user.id for admin in
                                CommunityMember.get_admins(request.comm_id)]
            if not (user_id in community_admins and request.is_invite):
                abort(404)
        MembershipRequestAPI.decline_or_cancel_invitation(request.id)

        db.session.commit()
        return 'Succesfully cancelled invitation.', 204


ui_blueprint = Blueprint(
    'invenio_communities',
    __name__,
    template_folder='../templates',
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
    """Create a new community."""
    return render_template('invenio-communities/new.html')


@ui_blueprint.route('/communities/')
def index():
    """Search for a new community."""
    return render_template('invenio-communities/index.html')


@ui_blueprint.route('/communities/<{0}:pid_value>/settings'.format(
            'pid(comid,record_class="invenio_communities.api:Community",'
            'object_type="com")'))
@pass_community_function
def settings(community, pid):
    """Modify a community."""
    return render_template(
        'invenio-communities/settings.html', community=community, pid=pid)


@ui_blueprint.route('/communities/<{0}:pid_value>/members'.format(
            'pid(comid,record_class="invenio_communities.api:Community",'
            'object_type="com")'))
@pass_community_function
def members(community, pid):
    """Members of a community."""
    return render_template(
        'invenio-communities/members.html', community=community, pid=pid)


@ui_blueprint.route('/communities/<{0}:pid_value>'.format(
            'pid(comid,record_class="invenio_communities.api:Community",'
            'object_type="com")'))
@pass_community_function
def community_page(community, pid):
    """Members of a community."""
    return render_template(
        'invenio-communities/community_page.html',
        community=community,
        pid=pid
    )


@ui_blueprint.route('/communities/members/requests/<membership_request_id>')
def requests(membership_request_id):
    """Requests of communities."""
    return render_template('invenio-communities/request.html')
