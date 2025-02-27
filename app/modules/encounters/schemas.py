# -*- coding: utf-8 -*-
"""
Serialization schemas for Encounters resources RESTful API
----------------------------------------------------
"""

from flask_marshmallow import base_fields

from flask_restx_patched import ModelSchema

from .models import Encounter


class BaseEncounterSchema(ModelSchema):
    """
    Base Encounter schema exposes only the most general fields.
    """

    annotations = base_fields.Nested('BaseAnnotationSchema', many=True)
    submitter = base_fields.Nested('PublicUserSchema', many=False)
    owner = base_fields.Nested('PublicUserSchema', many=False)
    hasView = base_fields.Function(lambda enc: enc.current_user_has_view_permission())
    hasEdit = base_fields.Function(lambda enc: enc.current_user_has_edit_permission())
    time = base_fields.Function(lambda enc: enc.get_time_isoformat_in_timezone())
    timeSpecificity = base_fields.Function(lambda enc: enc.get_time_specificity())

    class Meta:
        # pylint: disable=missing-docstring
        model = Encounter
        fields = (Encounter.guid.key,)
        dump_only = (Encounter.guid.key,)


class ElasticsearchEncounterSchema(ModelSchema):
    """
    Base Encounter schema exposes only the most general fields.
    """

    annotations = base_fields.Nested('AnnotationElasticsearchSchema', many=True)
    hasView = base_fields.Function(lambda enc: enc.current_user_has_view_permission())
    hasEdit = base_fields.Function(lambda enc: enc.current_user_has_edit_permission())
    time = base_fields.Function(lambda enc: enc.get_time_isoformat_in_timezone())
    timeSpecificity = base_fields.Function(lambda enc: enc.get_time_specificity())
    owner_guid = base_fields.Function(lambda enc: enc.get_owner_guid_str())
    sighting_guid = base_fields.Function(lambda enc: enc.get_sighting_guid_str())
    locationId = base_fields.Function(lambda enc: enc.get_location_id())
    taxonomy_guid = base_fields.Function(lambda enc: enc.get_taxonomy_guid())
    point = base_fields.Function(lambda enc: enc.get_point())
    customFields = base_fields.Function(lambda enc: enc.get_custom_fields())

    class Meta:
        # pylint: disable=missing-docstring
        model = Encounter
        fields = (
            Encounter.guid.key,
            Encounter.submitter_guid.key,
            'elasticsearchable',
            Encounter.indexed.key,
            'annotations',
            'time',
            'timeSpecificity',
            'owner_guid',
            'sighting_guid',
            'locationId',
            'taxonomy_guid',
            'point',
            'customFields',
        )
        dump_only = (Encounter.guid.key,)


class DetailedEncounterSchema(BaseEncounterSchema):
    """
    Detailed Encounter schema exposes all useful fields.
    """

    annotations = base_fields.Nested(
        'DetailedAnnotationSchema',
        many=True,
        only=('guid', 'asset_guid', 'ia_class', 'asset_src', 'bounds'),
    )

    createdHouston = base_fields.DateTime(attribute='created')
    created = base_fields.DateTime(attribute='created')
    updated = base_fields.DateTime(attribute='updated')
    taxonomy = base_fields.Function(lambda enc: enc.get_taxonomy_guid())
    individual = base_fields.Nested('NamedIndividualSchema', many=False)
    customFields = base_fields.Function(lambda enc: enc.get_custom_fields())
    verbatimLocality = base_fields.String(attribute='verbatim_locality')
    locationId = base_fields.Function(lambda enc: enc.get_location_id())
    locationId_value = base_fields.Function(lambda enc: enc.get_location_id_value())
    sighting = base_fields.UUID(attribute='sighting_guid')
    decimalLatitude = base_fields.Float(attribute='decimal_latitude')
    decimalLongitude = base_fields.Float(attribute='decimal_longitude')

    class Meta(BaseEncounterSchema.Meta):
        fields = BaseEncounterSchema.Meta.fields + (
            # send both for a while until FE removes use of old createdHouston field
            'createdHouston',
            'created',
            Encounter.updated.key,
            Encounter.owner.key,
            Encounter.owner_guid.key,
            Encounter.submitter.key,
            'hasView',
            'hasEdit',
            'annotations',
            'time',
            'timeSpecificity',
            'individual',
            'customFields',
            'verbatimLocality',
            'locationId',
            'locationId_value',
            'sighting',
            'taxonomy',
            'asset_group_sighting_encounter_guid',
            'decimalLatitude',
            'decimalLongitude',
            Encounter.sex.key,
        )
