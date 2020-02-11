# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Records API."""

from __future__ import absolute_import, print_function

from invenio_communities.members.models import CommunityMetadata, \
    CommunityMember, MembershipRequest
from invenio_communities.records.models import CommunityRecordInclusion
from invenio_records.models import RecordMetadata

from invenio_communities.records.models import CommunityRecordInclusion

from ..email import send_email_invitation


class CommunityRecordsAPI(object):

    @classmethod
    def invite_record(cls, community, pid_value, pid_type, comment=None, send_email=True):
        membership_request = CommunityRecordInclusion.create(
            community.id, True, comment=comment, rec_id=rec_id)
        RecordMetadata
        if send_email:
            send_email_invitation(
                membership_request.id, comment, community, comment)
        return membership_request

    @classmethod
    def join_community(cls, community, pid_value, pid_type, user_id, comment, send_email=True):
        membership_request = MembershipRequest.create(
            community.id, False, user_id=user_id, comment=comment,
            pid_value=pid_value, pid_type=pid_type
            )
        if send_email:
            community_admins = CommunityMember.get_admins(community.id)
            admin_emails = [admin.email for admin in community_admins]
            send_email_invitation(
                membership_request.id, admin_emails, community)
        return membership_request

    @classmethod
    def get_records(cls, comm_id):
        return CommunityRecordInclusion.get_records(comm_id)

    @classmethod
    def delete_inclusion(cls, inclusion_request_id, user_id, force=False):
        if force:
            CommunityRecordInclusion.delete(inclusion_request_id)
            return None

        request = CommunityRecordInclusion.query.get(inclusion_request_id)
        if request:
            request.status = 'D'
            request.json['handling_user_id'] = user_id
            return request
        else:
            return None

    @classmethod
    def push_message(cls, user_id, inclusion_request_id, message):
        record_inclusion = CommunityRecordInclusion.query.get(
            inclusion_request_id)
        if record_inclusion:
            record_inclusion.json['messages'].append({user_id: message})
            # TODO: How will the user be notified?
            return record_inclusion
        else:
            return None


class CommunityRecordInclusionRequestAPI():

    @classmethod
    def get_invitation(cls, inclusion_request_id):
        request = CommunityRecordInclusion.query.get(inclusion_request_id)
        community = CommunityMetadata.query.get(request.comm_id)
        return (request, community)

    @classmethod
    def accept_invitation(cls, inclusion_request_id, user_id):
        request = CommunityRecordInclusion.query.get(inclusion_request_id)
        if request:
            request.status = 'A'
            request.json['handling_user_id'] = user_id
            return request
        else:
            return None

    @classmethod
    def decline_or_cancel_invitation(cls, inclusion_request_id, user_id):
        request = CommunityRecordInclusion.query.get(inclusion_request_id)
        if request:
            request.status = 'R'
            request.json['handling_user_id'] = user_id
            return request
        else:
            return None

    @classmethod
    def get_community_outgoing_requests(
            cls, comm_id, page_size=20, page_number=0):
        incoming_count = CommunityRecordInclusion.query.filter_by(
            is_invite=True, comm_id=comm_id).count()
        incoming_requests = CommunityRecordInclusion.query.filter_by(
            is_invite=True, comm_id=comm_id)[page_number*page_size:page_size]
        return (incoming_count, incoming_requests)

    @classmethod
    def get_community_incoming_requests(
            cls, comm_id, page_size=20, page_number=0):
        outgoing_count = CommunityRecordInclusion.query.filter_by(
            is_invite=False, comm_id=comm_id).count()
        outgoing_requests = CommunityRecordInclusion.query.filter_by(
            is_invite=False, comm_id=comm_id)[page_number*page_size:page_size]
        return (outgoing_count, outgoing_requests)

