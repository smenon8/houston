# -*- coding: utf-8 -*-
"""
Encounters database models
--------------------
"""
import logging
import uuid

import app.extensions.logging as AuditLog
from app.extensions import CustomFieldMixin, HoustonModel, db

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Encounter(db.Model, HoustonModel, CustomFieldMixin):
    """
    Encounters database model.
    """

    __mapper_args__ = {
        'confirm_deleted_rows': False,
    }

    guid = db.Column(
        db.GUID, default=uuid.uuid4, primary_key=True
    )  # pylint: disable=invalid-name

    sighting_guid = db.Column(
        db.GUID, db.ForeignKey('sighting.guid'), index=True, nullable=True
    )
    sighting = db.relationship('Sighting', back_populates='encounters')

    individual_guid = db.Column(
        db.GUID, db.ForeignKey('individual.guid'), index=True, nullable=True
    )
    individual = db.relationship('Individual', back_populates='encounters')

    owner_guid = db.Column(
        db.GUID, db.ForeignKey('user.guid'), index=True, nullable=False
    )
    # owner = db.relationship(
    #     'User', back_populates='owned_encounters', foreign_keys=[owner_guid]
    # )
    owner = db.relationship(
        'User',
        backref=db.backref(
            'owned_encounters',
            primaryjoin='User.guid == Encounter.owner_guid',
            order_by='Encounter.guid',
        ),
        foreign_keys=[owner_guid],
    )

    submitter_guid = db.Column(
        db.GUID, db.ForeignKey('user.guid'), index=True, nullable=True
    )
    # submitter = db.relationship(
    #     'User', back_populates='submitted_encounters', foreign_keys=[submitter_guid]
    # )
    submitter = db.relationship(
        'User',
        backref=db.backref(
            'submitted_encounters',
            primaryjoin='User.guid == Encounter.submitter_guid',
            order_by='Encounter.guid',
        ),
        foreign_keys=[submitter_guid],
    )

    # Asset group sighting stores the configuration for this encounter,
    # Instead of duplicating the storage of it here, just store a reference into the structure
    # has to be nullable for db upgrade. Providing a default dummy guid would cause more problems
    # than it would solve
    asset_group_sighting_encounter_guid = db.Column(db.GUID, nullable=True)

    # projects = db.relationship(
    #     'ProjectEncounter',
    #     back_populates='encounter',
    #     order_by='ProjectEncounter.project_guid',
    # )

    # annotations = db.relationship(
    #     'Annotation', back_populates='encounter', order_by='Annotation.guid'
    # )

    time_guid = db.Column(
        db.GUID, db.ForeignKey('complex_date_time.guid'), index=True, nullable=True
    )
    time = db.relationship('ComplexDateTime')

    decimal_latitude = db.Column(db.Float, nullable=True)
    decimal_longitude = db.Column(db.Float, nullable=True)

    # Matches guid in site.custom.regions
    location_guid = db.Column(db.GUID, index=True, nullable=True)
    verbatim_locality = db.Column(db.String(), nullable=True)
    sex = db.Column(db.String(length=40), nullable=True)

    custom_fields = db.Column(db.JSON, default=lambda: {}, nullable=True)

    # Matches guid in site.species
    taxonomy_guid = db.Column(db.GUID, index=True, nullable=True)

    def user_is_owner(self, user) -> bool:
        return user is not None and user == self.owner

    @classmethod
    def get_elasticsearch_schema(cls):
        from app.modules.encounters.schemas import ElasticsearchEncounterSchema

        return ElasticsearchEncounterSchema

    @classmethod
    def patch_elasticsearch_mappings(cls, mappings):
        mappings = super(Encounter, cls).patch_elasticsearch_mappings(mappings)

        mappings['point'] = {
            'type': 'geo_point',
        }

        return mappings

    # index of encounter must trigger index of its annotations (so they can update)
    def index_hook_obj(self, *args, **kwargs):
        for annot in self.annotations:
            annot.index(force=True)

    def __repr__(self):
        return (
            '<{class_name}('
            'guid={self.guid}, '
            'owner={self.owner},'
            'individual={self.individual_guid},'
            'sighting={self.sighting_guid},'
            ')>'.format(class_name=self.__class__.__name__, self=self)
        )

    def get_owner(self):
        return self.owner

    def get_owner_guid_str(self):
        return str(self.owner.guid)

    def get_sighting(self):
        return self.sighting

    def get_sighting_guid_str(self):
        return str(self.sighting.guid)

    def get_assets(self):
        return {ann.asset for ann in self.annotations}

    def get_custom_fields(self):
        return self.custom_fields

    # first tries encounter.locationId, but will use sighting.locationId if none on encounter,
    #   unless sighting_fallback=False
    def get_location_id(self, sighting_fallback=True):
        location_id = self.location_guid
        if not location_id and sighting_fallback and self.sighting:
            location_id = self.sighting.get_location_id()
        return location_id

    def get_location_id_value(self):
        from app.modules.site_settings.models import Regions

        return Regions.get_region_name(str(self.get_location_id()))

    def get_point(self):
        if self.decimal_latitude is None or self.decimal_longitude is None:
            return None
        return {'lat': self.decimal_latitude, 'lon': self.decimal_longitude}

    # first tries encounter.taxonomy_guid, but will use sighting.taxonomy_guids if none on encounter,
    #   unless sighting_fallback=False
    #  NOTE: now sighting has MULTIPLE taxonomy_guids -- this will return 0th; so caveat emptor
    def get_taxonomy_guid(self, sighting_fallback=True):
        taxonomy_guid = self.taxonomy_guid
        if not taxonomy_guid and sighting_fallback and self.sighting:
            guids = self.sighting.get_taxonomy_guids()
            if guids:
                taxonomy_guid = guids[0]
        return taxonomy_guid

    def get_taxonomy_names(self, **kwargs):
        taxonomy_guid = self.get_taxonomy_guid(**kwargs)
        if taxonomy_guid:
            from app.modules.site_settings.models import Taxonomy

            return Taxonomy(taxonomy_guid).get_all_names()

        return []

    def get_time_isoformat_in_timezone(self, sighting_fallback=True):
        time = self.get_time(sighting_fallback=sighting_fallback)
        return time.isoformat_in_timezone() if time else None

    def get_time(self, sighting_fallback=True):
        if self.time:
            return self.time
        if self.sighting and sighting_fallback:
            return self.sighting.time
        return None

    def get_time_specificity(self, sighting_fallback=True):
        time = self.get_time(sighting_fallback=sighting_fallback)
        return time.specificity if time else None

    # not going to check for ownership by User.get_public_user() because:
    #  a) this allows for other-user-owned data to be toggled to public
    #  b) allows for us to _disallow_ public access to public-user-owned data
    def set_individual(self, individual):
        from app.modules.individuals.models import Individual

        if isinstance(individual, Individual):
            self.individual = individual

    def add_annotation(self, annotation):
        if annotation not in self.annotations:
            with db.session.begin(subtransactions=True):
                self.annotations.append(annotation)

    def merge_request_hash(self):
        parts = [
            self.guid.int,
            # this covers weird cases where things arent persisted to db yet
            (self.owner and self.owner.guid or self.owner_guid).int,
            (self.individual and self.individual.guid or self.individual_guid).int,
        ]
        parts.sort()
        return hash(tuple(parts))

    def delete(self):
        AuditLog.delete_object(log, self)
        with db.session.begin(subtransactions=True):
            db.session.delete(self)

    def delete_cascade(self):
        with db.session.begin(subtransactions=True):
            db.session.delete(self)

    def delete_frontend_request(self, delete_individual, delete_sighting):
        response = {}

        if self.sighting and (len(self.sighting.encounters) == 1) and not delete_sighting:
            response['vulnerableSighting'] = str(self.sighting.guid)

        if (
            self.individual
            and (len(self.individual.encounters) == 1)
            and not delete_individual
        ):
            response['vulnerableIndividual'] = str(self.individual.guid)

        if response:
            return False, response

        # we need to do this first, as we will be messing with self(enc) and sighting below
        #   deleting the individual does *not* cascade to encounters, so this is ok to do now
        indiv = self.individual
        if indiv and len(indiv.encounters) == 1:
            response['deletedIndividual'] = str(indiv.guid)
            self.individual_guid = None
            indiv.delete()

        # this will *also delete this encounter (self)* so we have to take that into account
        if self.sighting and len(self.sighting.encounters) == 1:
            response['deletedSighting'] = str(self.sighting.guid)
            self.sighting.delete()  # goodbye also self!
        else:
            self.delete()
        return True, response
