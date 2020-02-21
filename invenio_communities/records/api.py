# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Records API."""

from __future__ import absolute_import, print_function

from invenio_db import db
from invenio_records.api import Record
from invenio_records.models import RecordMetadata

from invenio_communities.records.models import \
    CommunityRecord as CommunityRecordModel
from invenio_communities.records.models import CommunityRecordAlreadyExists, \
    CommunityRecordStatus
from invenio_communities.records.models import Request as RequestModel


class RequestRecord(Record):
    """Request API class."""

    model_cls = RequestModel

    @property
    def comments(self):
        """Request comments."""
        return self.model.comments if self.model else None

    # def add_message(self, user_id, message):
    #     self['messages'].append({user_id: message})
    #     return self



def record_add_community(self, record, community):
    comm_record = record.communities.add(community)
    if self.context.user in community.curators:
        comm_record.status = CommunityRecordStatus.ACCEPTED
    else:
        send_email_to_curators(comm_record)


# /api/records/1234/communities
def get_record_communities(self, record):
    community_data = record.communities.as_dict()
    """
    {
        "pending": [<biosyslit>, <openaire>],
        "rejected": ["zenodo"],
    }
    """
    self.context.user.communities
    community_data['pending']
    return community_data


class CommunityRecord(Record):
    """Community-record API class."""

    model_cls = CommunityRecordModel

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
    def create(cls, record_pid, community_pid, request, status=None,
            auto_approve=False, can_curate=False, data=None):
        data = data or {}
        # data['can_curate'] = can_curate
        # TODO figure out which data we need
        # TODO send email notification
        # data['auto_approved'] = auto_approve
        # if auto_approve:
        #     status = 'A'
        # else:
        #     status = 'P'

        model = CommunityRecordModel.create(
            community_pid=community_pid.id,
            record_pid=record_pid.id,
            status=status,
            request=request.id,
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

    def delete(self):
        """Delete the community record."""
        db.session.delete(self.model)


class CommunityRecordsCollectionBase:

    community_record_cls = CommunityRecord
    record_cls = RecordMetadata

    def __init__(self, comm_pid_id, query):
        self.comm_pid_id = comm_pid_id
        self.query = query

    def __len__(self):
        """Get number of community records."""
        return self.query.count()

    def __iter__(self):
        self._it = iter(self.query.all())
        return self

    def __next__(self):
        """Get next community record item."""
        obj = next(self._it)
        return self.community_record_cls(obj)


class CommunityRecordsCollection(CommunityRecordsCollectionBase):

    def __init__(self, comm_pid, query):
        self.comm_pid = comm_pid
        self.query = query

    def __getitem__(self, record_pid):
        """Get a specific community record."""
        obj = self.query.filter_by(record_pid=record_pid).one_or_none()
        if obj:
            return self.community_record_cls(obj)
        raise KeyError(record_pid)

    def add(self, record=None, recid=None, **kwargs):
        if not record:
            if recid:
                #TODO by recid we mean via PID?
                record = self.record_cls.query.get(recid)
            else:
                raise Exception('Too few arguments provided')
        return CommunityRecord.create(
            self.comm_pid, record, **kwargs)

    # Maybe it is not needed since you can use the get item
    def remove(self, record=None, recid=None, **kwargs):
        if not record:
            if recid:
                #TODO by recid we mean via PID?
                record = self.record_cls.query.get(recid)
            else:
                raise Exception('Too few arguments provided')
        return CommunityRecord.get(
            self.comm_pid, record).delete()


class RecordCommunitiesCollection(CommunityRecordsCollectionBase):

    def __init__(self, record_pid, query):
        self.record_pid = record_pid
        self.query = query

    def __getitem__(self, comm_pid):
        """Get a specific community record."""
        obj = self.query.filter_by(comm_pid=comm_pid).one_or_none()
        if obj:
            return self.community_record_cls(obj)
        raise KeyError(comm_pid)

    def add(self, community=None, comm_pid=None, **kwargs):
        if not community:
            if comm_pid:
                # TODO by comm_pid we mean via PID?
                community = self.record_cls.query.get(comm_pid)
            else:
                raise Exception('Too few arguments provided')
        community_record = CommunityRecord.create(
            comm_pid, self.record_pid, **kwargs)
        return community_record


class CommunityRecordsMixin(object):

    community_records_iter_cls = CommunityRecordsCollection

    def __init__(self, comm_pid_id):
        self.comm_pid_id = comm_pid_id

    @property
    def pending_records_query(self):
        return CommunityRecordModel.query.filter_by(
                    comm_pid=self.comm_pid_id, status='P')

    @property
    def records_query(self):
        return CommunityRecordModel.query.filter_by(
                    comm_pid=self.comm_pid_id, status='A')

    @property
    def records(self):
        return self.community_records_iter_cls(
            self.comm_pid_id, self.records_query)

    @property
    def pending_records(self):
        return self.community_records_iter_cls(
            self.comm_pid_id, self.pending_records_query)

    @property
    def notified_members(self):
        pass

    @property
    def allowed_record_integrators(self):
        pass

    @property
    def banned_record_integrators(self):
        pass


class RecordCommunitiesMixin:

    record_communities_iter_cls = CommunityRecordsCollection

    def __init__(self, record_pid):
        self.record_pid = record_pid

    @property
    def pending_communities_query(self):
        return CommunityRecordModel.query.filter_by(
                    record_pid=self.record_pid, status='P')

    @property
    def communities_query(self):
        return CommunityRecordModel.query.filter_by(
                    record_pid=self.record_pid, status='A')

    @property
    def communities(self):
        return self.record_communities_iter_cls(
            self.record_pid, self.communities_query)

    @property
    def pending_communities(self):
        return self.record_communities_iter_cls(
            self.record_pid, self.communities_query)


    # Add method to community APIS
    # @classmethod
    # def block_user(cls, user_id, comm_id, user_to_block):
    #     # TODO create a CommunityMember relationship restricting this
    #     pass
