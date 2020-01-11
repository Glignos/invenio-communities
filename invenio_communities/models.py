# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2020 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Community database models."""

from __future__ import absolute_import, print_function

import uuid
from enum import Enum

from flask_babelex import gettext
from invenio_accounts.models import User
from invenio_db import db
from invenio_records.models import RecordMetadataBase
from speaklater import make_lazy_gettext
from sqlalchemy.exc import IntegrityError
from sqlalchemy_utils.types import ChoiceType, UUIDType

# TODO make sure well what this does and that we need this dependency
_ = make_lazy_gettext(lambda: gettext)


class CommunityMetadata(db.Model, RecordMetadataBase):
    """Represent a community."""

    __tablename__ = 'community_metadata'
    __versioned__ = {'versioning': False}


class CommunityMemberAlreadyExists(Exception):
    """Community membership already exists error."""

    def __init__(self, user_id, pid_id, role):
        """Initialize Exception."""
        self.user_id = user_id
        self.pid_id = pid_id
        self.role = role


class CommunityMemberDoesNotExist(CommunityMemberAlreadyExists):
    """Community membership does not exist error."""

    pass


COMMUNITY_MEMBER_TITLES = {
    'MEMBER': _('Member'),
    'ADMIN': _('Admin'),
    'CURATOR': _('Curator')
}


class CommunityRoles(Enum):
    """Constants for possible roles of any given Community member."""

    MEMBER = 'M'
    """Member of the community."""

    ADMIN = 'A'
    """Admin of the community."""

    CURATOR = 'C'
    """Curator of the community."""

    @property
    def title(self):
        """Return human readable title."""
        return COMMUNITY_MEMBER_TITLES[self.name]


class CommunityMembers(db.Model):
    """Represent a community member role."""

    __tablename__ = 'community_members'

    "Community PID ID"
    comm_id = db.Column(
        db.String,
        db.ForeignKey(CommunityMetadata.id),
        primary_key=True,
        nullable=False,
    )

    "USER ID"
    user_id = db.Column(
        db.Integer,
        db.ForeignKey(User.id),
        primary_key=True,
        nullable=False,
    )

    role = db.Column(
        ChoiceType(CommunityRoles, impl=db.CHAR(1)), nullable=False)

    @classmethod
    def create_or_modify(cls, membership_request):
        """Create or modify existing membership."""
        existing_membership = cls.query.filter_by(
                    comm_id=membership_request.comm_id,
                    user_id=membership_request.user_id
                    ).one_or_none()
        if existing_membership:
            with db.session.begin_nested():
                existing_membership.role = membership_request.role
        else:
            cls.create(membership_request)

    @classmethod
    def create(cls, membership_request):
        """Create Community Membership Role."""
        try:
            with db.session.begin_nested():
                obj = cls(
                    comm_id=membership_request.comm_id,
                    user_id=membership_request.user_id,
                    role=membership_request.role)
                db.session.add(obj)
                db.session.delete(membership_request)
        except IntegrityError:
            raise CommunityMemberAlreadyExists(
                comm_id=membership_request.comm_id,
                user_id=membership_request.user_id,
                role=membership_request.role)
        return obj

    @classmethod
    def delete(cls, comm_id, user_id):
        """Delete a community membership."""
        try:
            with db.session.begin_nested():
                membership = cls.query.filter_by(
                    comm_id=comm_id, user_id=user_id)
                db.session.delete(membership)
        except IntegrityError:
            raise CommunityMemberDoesNotExist(comm_id=comm_id, user_id=user_id)


class MembershipRequests(db.Model):
    """Represent a community member role."""

    __tablename__ = 'membership_requests'

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(User.id),
        nullable=True,
    )

    comm_id = db.Column(
        db.Integer,
        db.ForeignKey(CommunityMetadata.id),
        nullable=False,
    )

    role = db.Column(
        ChoiceType(CommunityRoles, impl=db.CHAR(1)), nullable=False)

    is_invite = db.Column(db.Boolean(name='is_invite'), nullable=False,
                          default=True)

    @classmethod
    def create(cls, comm_id, user_id, role):
        """Create Community Membership request."""
        try:
            with db.session.begin_nested():
                obj = cls(
                    comm_id=comm_id, user_id=user_id, role=role)
                db.session.add(obj)
        except IntegrityError:
            raise CommunityMemberAlreadyExists(
                comm_id=comm_id, user_id=user_id, role=role)
        return obj

    @classmethod
    def delete(cls, id):
        """Delete a community membership request."""
        try:
            with db.session.begin_nested():
                membership = cls.query.get(id)
                db.session.delete(membership)
        except IntegrityError:
            raise CommunityMemberDoesNotExist(id)
