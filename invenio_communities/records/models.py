# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2020 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Record database models."""

from __future__ import absolute_import, print_function

import uuid
from enum import Enum

from flask_babelex import gettext
from invenio_accounts.models import User
from invenio_db import db
from invenio_records.models import RecordMetadataBase, RecordMetadata
from speaklater import make_lazy_gettext
from sqlalchemy.exc import IntegrityError
from sqlalchemy_utils.types import ChoiceType, UUIDType

from invenio_communities.models import CommunityMetadata
# TODO make sure well what this does and that we need this dependency
_ = make_lazy_gettext(lambda: gettext)


class CommunityRecordAlreadyExists(Exception):
    """Record inclusion already exists error."""

    def __init__(self, user_id, pid_id):
        """Initialize Exception."""
        self.user_id = user_id
        self.pid_id = pid_id


class CommunityRecordDoesNotExist(CommunityRecordAlreadyExists):
    """Record inclusion does not exist error."""

    pass


COMMUNITY_RECORD_STATUS = {
    'ACCEPTED': _('Accepted'),
    'REJECTED': _('Rejected'),
    'PENDING': _('Pending'),
    'REMOVED': _('Removed')
}


class CommunityRecordStatus(Enum):
    """Constants for possible states of a Community Record."""
    # TODO Make roles configurable.
    ACCEPTED = 'A'

    REJECTED = 'R'

    PENDING = 'P'

    REMOVED = 'D'

    @property
    def title(self):
        """Return human readable title."""
        return COMMUNITY_RECORD_STATUS[self.name]


class CommunityRecordInclusion(db.Model, RecordMetadataBase):
    """Represent a record member."""

    __tablename__ = 'community_record'
    __table_args__ = {'extend_existing': True}
    __versioned__ = {'versioning': False}

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )

    "Record PID ID"
    pid_type = db.Column(
        UUIDType,
        nullable=False,
    )

    pid_value = db.Column(
        UUIDType,
        nullable=False,
    )

    comm_id = db.Column(
        UUIDType,
        db.ForeignKey(CommunityMetadata.id),
        nullable=False,
    )

    # requesting_user_id = db.Column(
    #     db.Integer,
    #     db.ForeignKey(User.id),
    #     nullable=True,
    # )

    # handling_user_id = db.Column(
    #     db.Integer,
    #     db.ForeignKey(User.id),
    #     nullable=True,
    # )

    status = db.Column(
        ChoiceType(CommunityRecordStatus, impl=db.CHAR(1)), nullable=False)

    is_invite = db.Column(db.Boolean(name='is_invite'), nullable=False,
                          default=True)

    communities = db.relationship(CommunityMetadata, backref='records')

    @classmethod
    def create(cls, comm_id, is_invite, pid_value, pid_type, user_id=None):
        """Create Record Membership request."""
        try:
            with db.session.begin_nested():
                obj = cls(
                    comm_id=comm_id, user_id=user_id,
                    is_invite=is_invite, pid_value=pid_value,
                    pid_type=pid_type)
                db.session.add(obj)
        except IntegrityError:
            raise CommunityRecordAlreadyExists(
                comm_id=comm_id, user_id=user_id)
        return obj

    @classmethod
    def delete(cls, inclusion_id, force=False):
        """Delete a record inclusion request."""
        try:
            with db.session.begin_nested():
                inclusion = cls.query.get(inclusion_id)
                db.session.delete(inclusion)
        except IntegrityError:
            raise CommunityRecordDoesNotExist(id)

    @classmethod
    def get_records(cls, id):
        """Get all the records of a community."""
        return cls.query.filter_by(comm_id=id)
