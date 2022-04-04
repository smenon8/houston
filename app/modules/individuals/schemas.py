# -*- coding: utf-8 -*-
"""
Serialization schemas for Individuals resources RESTful API
----------------------------------------------------
"""

from flask_restx_patched import ModelSchema
from flask_marshmallow import base_fields

from .models import Individual

from app.modules.names.schemas import DetailedNameSchema
from app.modules.encounters.schemas import (
    DetailedEncounterSchema,
    ElasticsearchEncounterSchema,
)


class BaseIndividualSchema(ModelSchema):
    """
    Base Individual schema exposes only the most general fields.
    """

    hasView = base_fields.Function(Individual.current_user_has_view_permission)
    hasEdit = base_fields.Function(Individual.current_user_has_edit_permission)

    class Meta:
        # pylint: disable=missing-docstring
        model = Individual
        fields = (
            Individual.guid.key,
            'hasView',
            'hasEdit',
            'elasticsearchable',
            Individual.indexed.key,
        )
        dump_only = (Individual.guid.key,)


class NamedIndividualSchema(BaseIndividualSchema):
    """
    Detailed Individual schema exposes all useful fields.
    """

    names = base_fields.Nested(
        DetailedNameSchema,
        attribute='names',
        many=True,
    )

    class Meta(BaseIndividualSchema.Meta):
        fields = BaseIndividualSchema.Meta.fields + ('names',)


class DetailedIndividualSchema(NamedIndividualSchema):
    """
    Detailed Individual schema exposes all useful fields.
    """

    featuredAssetGuid = base_fields.Function(Individual.get_featured_asset_guid)
    social_groups = base_fields.Function(Individual.get_social_groups_json)

    class Meta(NamedIndividualSchema.Meta):
        fields = NamedIndividualSchema.Meta.fields + (
            Individual.created.key,
            Individual.updated.key,
            'featuredAssetGuid',
            'social_groups',
        )
        dump_only = NamedIndividualSchema.Meta.dump_only + (
            Individual.created.key,
            Individual.updated.key,
        )


class ElasticsearchIndividualSchema(ModelSchema):
    """
    Base Individual schema exposes only the most general fields.
    """

    featuredAssetGuid = base_fields.Function(Individual.get_featured_asset_guid)
    names = base_fields.Nested(
        DetailedNameSchema,
        attribute='names',
        many=True,
    )
    encounters = base_fields.Nested(ElasticsearchEncounterSchema, many=True)
    social_groups = base_fields.Function(Individual.get_social_groups_json)
    sex = base_fields.Function(Individual.get_sex)
    birth = base_fields.Function(Individual.get_time_of_birth)
    death = base_fields.Function(Individual.get_time_of_death)

    class Meta:
        # pylint: disable=missing-docstring
        model = Individual
        fields = (
            Individual.guid.key,
            'elasticsearchable',
            Individual.indexed.key,
            Individual.created.key,
            Individual.updated.key,
            'featuredAssetGuid',
            'names',
            'social_groups',
            'sex',
            'encounters',
            'birth',
            'death',
        )
        dump_only = (
            Individual.guid.key,
            Individual.created.key,
            Individual.updated.key,
        )


class DebugIndividualSchema(DetailedIndividualSchema):
    """
    Debug Individual schema exposes all fields.
    """

    houston_encounters = base_fields.Nested(
        DetailedEncounterSchema,
        attribute='encounters',
        many=True,
    )

    class Meta(DetailedIndividualSchema.Meta):
        fields = DetailedIndividualSchema.Meta.fields + ('houston_encounters',)
