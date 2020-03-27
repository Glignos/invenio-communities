# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Records API."""

from __future__ import absolute_import, print_function

from flask import current_app
from invenio_jsonschemas import current_jsonschemas
from invenio_records.api import Record
from werkzeug.local import LocalProxy
from invenio_db import db

from invenio_communities.members.models import CommunityMetadata
from invenio_pidstore.models import PersistentIdentifier

from .members.api import CommunityMembersAPI


# TODO: Move somewhere appropriate (`invenio-records-pidstore`)
class PIDRecordMixin:
    """."""

    pid_object_type = None
    primary_pid_type = None

    @property
    def pid(self):
        """."""
        return PersistentIdentifier.query.filter_by(
            object_uuid=self.id,
            object_type=self.pid_object_type,
            pid_type=self.primary_pid_type
        ).one()

    @property
    def pids(self):
        """."""
        return PersistentIdentifier.query.filter_by(
            object_uuid=self.id,
            object_type=self.pid_object_type,
        ).all()


class Community(Record, PIDRecordMixin):
    """Define API for community creation and manipulation."""

    pid_object_type = 'com'
    primary_pid_type = 'comid'

    # TODO: Communities model doesn't have versioninig, some methods from
    # "invenio_records.api.RecordBase" have to be overridden/removed
    model_cls = CommunityMetadata

    schema = LocalProxy(lambda: current_jsonschemas.path_to_url(
        current_app.config.get(
            'COMMUNITY_SCHEMA', 'communities/communities-v1.0.0.json')))

    @classmethod
    def create_community_record(cls, data, *args, **kwargs):
        """Create community record with default '$schema'."""
        data['$schema'] = str(cls.schema)
        return cls(data)

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        r"""Create a new community instance and store it in the database..
        """
        with db.session.begin_nested():
            community = cls.create_community_record(data)

            community.validate(**kwargs)

            community.model = cls.model_cls(id=id_, json=community)

            db.session.add(community.model)

            CommunityMembersAPI.set_default_admin(community.model)

        return community

    def delete(self, force=False):
        """Delete a community."""
        with db.session.begin_nested():
            if force:
                db.session.delete(self.model)
            else:
                self.model.delete()

        return self
