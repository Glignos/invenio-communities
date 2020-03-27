# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Records API."""

from __future__ import absolute_import, print_function

from collections import defaultdict

from invenio_db import db
from invenio_records.api import Record
from invenio_records.models import RecordMetadata

from invenio_communities.records.models import \
    CommunityRecord as CommunityRecordModel
from invenio_communities.records.models import CommunityRecordAlreadyExists, \
    CommunityRecordStatus, RequestComment
from invenio_communities.records.models import Request as RequestModel
from invenio_communities.api import Community, PIDRecordMixin
from invenio_indexer.api import RecordIndexer

"""
/api/communities/<comid>/requests/inclusion [LIST|POST]


/api/communities/<comid>/requests/inclusion/<req_id> [GET|PUT|DELETE]
/api/communities/<comid>/requests/inclusion/<req_id>/<accept,reject,comment> [POST]
"""


"""
LIST /api/records?provsional_communities=biosyslit

q="communities.pending.id:biosyslit"
[
    {
        "communities": {
            "pending": [
                {
                    "id": "biosyslit",
                    "title": "BLR",
                    "created": "2020-04-06T12:00:00",
                    "request_id": "abcdef-...",
                }
            ]
        }
    }
]
"""


# /api/communities/<comid>/requests/inclusion [POST]
def post(comid):
    # def create(cls, record_pid, community_pid, request, status=None, data=None)
    community = resolve_comid(comid)
    recid, record = resolve_recid(request.json['recid'])

    request = CommunityInclusionRequest.create(current_user)
    if current_user in community.members:
        request.routing_key = f'record:{recid.pid_value}:owners'
    else:
        request.routing_key = f'community:{comid.pid_value}:curators'
    com_rec = CommunityRecord.create(record.pid, community.pid, request)
    db.session.commit()

    # Notify request owners and receivers
    # TODO: implement mail sending
    send_request_emails(request)

    # Index record with new inclusion request info
    # TODO: Implement indexer receiver to include community info in record
    RecordIndexer().index_by_id(record.id)

    return make_response(com_rec.dumps(), 201)

#Do we need filtering args?
# /api/communities/<comid>/requests/inclusion [LIST]
def get(comid):
    community = resolve_comid(comid)
    community_records = Community.records.list

    # Notify request owners and receivers
    #TODO
    send_request_emails(request)

    return make_response(com_rec, ...)

# /api/communities/<comid>/requests/inclusion/<request_id> [GET]
def get(comid, request_id):
    community = resolve_comid(comid)
    request = CommunityInclusionRequest.get_record(request_id)
    {
        'request_id': request.id,
        'created_by': request.owner_id,
        'comments': [
            {'message': c.message, 'created_by': 567}
            for c in request.comments
        ]
    }
    return make_response(request, ...)

# /api/communities/<comid>/requests/inclusion/<request_id> [PUT]
def put(comid, request_id):
    community = resolve_comid(comid)
    record_request = CommunityInclusionRequest.get_record(request_id)
    record_request.add_comment(record_request.id, user, request.json)
    return make_response(request, ...)

# /api/communities/<comid>/requests/inclusion/<request_id> [DELETE]
def delete(comid, request_id):
    community = resolve_comid(comid)
    record_request = CommunityInclusionRequest.get_record(request_id)

    record_request.remove()

    return make_response(request, ...)


class Request(Record):
    """Request API class."""

    model_cls = RequestModel

    schema = {
        "type": {
            "type": "string",
            # "enum": ["community-inclusion"],
        },
        "state": {
            "type": "string",
            # "enum": ["pending", "closed"],
        },
        "assignees": {"type": "int[]"},
        "created_by": {"type": "int"},
    }

    @property
    def routing_key(self):
        """Get request routing key."""
        return self.model.routing_key if self.model else None

    @routing_key.setter
    def routing_key(self, new_routing_key):
        """Set request routing key."""
        self.model.routing_key = new_routing_key

    @property
    def comments(self):
        """Request comments."""
        return self.model.comments if self.model else None

    def add_comment(self, user, message):
        """Request comments."""
        # TODO: do we need a comment API Class?
        return RequestComment.create(self.id, user.id, message)


class CommunityInclusionRequest(Request):

    TYPE = 'community-inclusion-request'

    # TODO: Override
    schema = {
        "type": {
            "type": "string",
            # "enum": ["community-inclusion"],
        },
        "state": {
            "type": "string",
            # "enum": ["pending", "closed"],
        },
        "assignees": {"type": "int[]"},
        "created_by": {"type": "int"},
    }

    class State(Enum):
        OPEN = 'open'
        CLOSED = 'closed'

    @property
    def community_record(self):
        """Get request's community record relatinship."""
        if not getattr(self, '_community_record', None):
            self._community_record = CommunityRecord.get_by_request_id(
                request_id=self.id)
        return self._community_record

    @property
    def community(self):
        """Get request community."""
        return self.community_record.community

    @property
    def record(self):
        """Get request record."""
        return self.community_record.record

    @classmethod
    def create(cls, owner, **kwargs):
        """Create a community inclusion request."""
        data = {
            'type': cls.TYPE,
            'state': State.OPEN,
            'created_by': owner.id,
            **kwargs,
        }
        model = self.model_cls(
            owner_id=owner.id,
            json=data,
        )
        return cls(data, model=model)

    def as_dict(self):
        return {
            'id': self.id,
            'created': self.created,
            'updated': self.updated,
            'comments': [
                {
                    'id': c.id,
                    'message': c.message,
                    'created_by': c.created_by,
                    'created': c.created,
                    'updated': c.updated,
                } for c in self.comments
            ]
        }


class CommunityRecord(Record):
    """Community-record API class."""

    model_cls = CommunityRecordModel

    schema = {
        # TODO: Define schema
    }

    @property
    def request(self):
        """Community record request."""
        # TODO: Return a RequestRecord object, not the SQLAlchemy model
        return self.model.request if self.model else None

    @property
    def status(self):
        """Get community record relationship status."""
        return self.model.status if self.model else None

    @status.setter
    def status(self, new_status):
        """Set community record relationship status."""
        self.model.status = new_status

    @classmethod
    def create(cls, record, community, request, status=None,
               auto_approve=False, can_curate=False, data=None):
        data = data or {}
        model = CommunityRecordModel.create(
            community_pid=community.pid.id,
            record_pid=record.pid.id,
            request_id=request.id,
            status=status,
            json=data,
        )

        return cls(data, model=model)

    @classmethod
    def get_by_pids(cls, community_pid, record_pid):
        """Get by community and record PIDs."""
        model = CommunityRecordModel.query.filter_by(
            community_pid_id=community_pid.id,
            record_pid_id=record_pid.id,
        ).one_or_none()
        if not model:
            return None
        return cls(model.json, model=model)

    @classmethod
    def get_by_request_id(cls, request_id):
        """Get by request ID."""
        model = CommunityRecordModel.query.filter_by(
            request_id=request_id
        ).one_or_none()
        if not model:
            return None
        return cls(model.json, model=model)

    def as_dict(self, record=True, request=True):
        res = {
            'status': self.status,
            'record_pid': self.record.pid
        }
        if request:
            res['request'] = self.request.as_dict()
        return res


class CommunityRecordsCollectionBase:

    community_record_cls = CommunityRecord

    def __len__(self):
        """Get number of community records."""
        return self.query.count()

    def __iter__(self):
        self._it = iter(self.query)
        return self

    def __next__(self):
        """Get next community record item."""
        obj = next(self._it)
        return self.community_record_cls(obj.json, model=obj)

    def __getitem__(self, key):
        raise NotImplementedError()

    @property
    def query(self):
        raise NotImplementedError()


class CommunityRecordsCollection(CommunityRecordsCollectionBase):

    def __init__(self, community):
        self.community = community

    @property
    def query(self):
        return CommunityRecord.query.filter_by(
            community_pid_id=self.community.pid.id)

    def __getitem__(self, record):
        """Get a specific community record by record PID."""
        return self.community_record_cls.get_by_pids(
            self.community.pid, record.pid)

    def add(self, record, request):
        return self.community_record_cls.create(
            self.community, record, request)

    def remove(self, record):
        community_record = self[record]
        return community_record.delete()

    def as_dict(self):
        community_records = defaultdict(list)
        for community_record in self:
            status = community_record.status.title
            community_records[status].append(community_record.as_dict())
        return community_records


class RecordCommunitiesCollection(CommunityRecordsCollectionBase):

    def __init__(self, record):
        self.record = record

    @property
    def query(self):
        return CommunityRecord.query.filter_by(
            record=self.record.pid.id)

    def __getitem__(self, community):
        """Get a specific community record."""
       return self.community_record_cls.get_by_pids(
            community.pid, self.record.pid)

    def add(self, community, request):
        return self.community_record_cls.create(
            community, self.record, request)

    def remove(self, community):
        community_record = self[community]
        return community_record.delete()

    def as_dict(self):
        community_records = defaultdict(list)
        for community_record in self:
            status = community_record.status.title
            community_records[status].append(community_record.community_pid)
        return community_records


class CommunityRecordsMixin:

    community_records_iter_cls = CommunityRecordsCollection

    @property
    def records(self):
        return self.community_records_iter_cls(self)

    # TODO: Take into account in the controllers
    # @property
    # def notified_members(self):
    #     pass
    # @property
    # def allowed_record_integrators(self):
    #     pass
    # @property
    # def banned_record_integrators(self):
    #     pass


class RecordCommunitiesMixin(PIDMixin):

    record_communities_iter_cls = RecordCommunitiesCollection

    pid_object_type = 'rec'
    primary_pid_type = 'recid'

    @property
    def communities(self):
        return self.record_communities_iter_cls(self.pid.id)

    # TODO: Take into account in the controllers
    # def block_community(cls, community):
    #     # TODO: should this be implemented on the level of Request API
    #     # TODO create a CommunityMember relationship restricting this
    #     pass
