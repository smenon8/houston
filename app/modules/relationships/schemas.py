# -*- coding: utf-8 -*-
"""
Serialization schemas for Relationships resources RESTful API
----------------------------------------------------
"""

from flask_marshmallow import base_fields
from flask_restx_patched import ModelSchema

from .models import Relationship


class BaseRelationshipSchema(ModelSchema):
    """
    Base Relationship schema exposes only the most general fields.
    """

    class Meta:
        # pylint: disable=missing-docstring
        model = Relationship
        fields = (
            Relationship.guid.key,
        )
        dump_only = (
            Relationship.guid.key,
        )


class DetailedRelationshipSchema(BaseRelationshipSchema):
    """
    Detailed Relationship schema exposes all useful fields.
    """

    class Meta(BaseRelationshipSchema.Meta):
        fields = BaseRelationshipSchema.Meta.fields + (
            Relationship.created.key,
            Relationship.updated.key,
        )
        dump_only = BaseRelationshipSchema.Meta.dump_only + (
            Relationship.created.key,
            Relationship.updated.key,
        )