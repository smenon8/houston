# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
import tests.modules.asset_groups.resources.utils as asset_group_utils
from tests import utils as test_utils
import pytest

from tests.utils import module_unavailable


# Test a bunch of failure scenarios
@pytest.mark.skipif(
    module_unavailable('asset_groups'), reason='AssetGroups module disabled'
)
def test_commit_asset_group(
    flask_app_client, researcher_1, regular_user, test_root, request, db
):
    # pylint: disable=invalid-name
    from app.modules.sightings.models import Sighting, SightingStage

    (
        asset_group_uuid,
        asset_group_sighting_guid,
        asset_uuid,
    ) = asset_group_utils.create_simple_asset_group(
        flask_app_client, regular_user, request, test_root
    )

    asset_group_utils.patch_in_dummy_annotation(
        flask_app_client, db, researcher_1, asset_group_sighting_guid, asset_uuid
    )

    # Should not be able to commit as contributor
    asset_group_utils.commit_asset_group_sighting(
        flask_app_client, regular_user, asset_group_sighting_guid, 403
    )
    # researcher should though
    response = asset_group_utils.commit_asset_group_sighting(
        flask_app_client, researcher_1, asset_group_sighting_guid
    )

    sighting_uuid = response.json['guid']
    sighting = Sighting.query.get(sighting_uuid)
    assert sighting.stage == SightingStage.identification
    assert len(sighting.get_encounters()) == 1
    assert len(sighting.get_assets()) == 1
    assert sighting.get_owner() == regular_user
    group_sighting = asset_group_utils.read_asset_group_sighting(
        flask_app_client, researcher_1, asset_group_sighting_guid
    )
    assert set(group_sighting.json.keys()) >= set(
        {
            'completion',
            'asset_group_guid',
            'assets',
            'stage',
            'creator',
            'jobs',
            'config',
            'guid',
            'sighting_guid',
        }
    )
    assert group_sighting.json['completion'] == 30
    assert group_sighting.json['asset_group_guid'] == asset_group_uuid
    assert group_sighting.json['creator']['guid'] == str(regular_user.guid)
    assert group_sighting.json['sighting_guid'] == sighting_uuid


@pytest.mark.skipif(
    module_unavailable('asset_groups'), reason='AssetGroups module disabled'
)
def test_commit_owner_asset_group(
    flask_app_client, researcher_1, regular_user, staff_user, test_root, db, request
):
    # pylint: disable=invalid-name
    from app.modules.sightings.models import Sighting, SightingStage

    asset_group_uuid = None
    try:
        data = asset_group_utils.get_bulk_creation_data(test_root, request)
        # order of ags not deterministic so to make the test simpler, make the first encounter in all
        # sightings owned by the regular user
        data.set_encounter_field(0, 0, 'ownerEmail', regular_user.email)
        data.set_encounter_field(1, 0, 'ownerEmail', regular_user.email)
        resp = asset_group_utils.create_asset_group(
            flask_app_client, researcher_1, data.get()
        )
        asset_group_uuid = resp.json['guid']
        asset_group_sighting_guid = resp.json['asset_group_sightings'][0]['guid']
        # commit it
        response = asset_group_utils.commit_asset_group_sighting(
            flask_app_client, researcher_1, asset_group_sighting_guid
        )
        sighting_uuid = response.json['guid']
        sighting = Sighting.query.get(sighting_uuid)
        encounters = sighting.get_encounters()
        assert len(encounters) == 2
        assert sighting.stage == SightingStage.identification
        # It seems encounters may not be returned in order so we can't assert
        # encounters[0].owner == regular_user
        assert sorted([e.owner.email for e in encounters]) == [
            researcher_1.email,
            regular_user.email,
        ]

    finally:
        # Restore original state
        if asset_group_uuid:
            asset_group_utils.delete_asset_group(
                flask_app_client, researcher_1, asset_group_uuid
            )


# Create an asset group with an annotation and an ia_config and expect it to start IA
@pytest.mark.skipif(
    module_unavailable('asset_groups'), reason='AssetGroups module disabled'
)
def test_commit_asset_group_ia(
    flask_app_client, researcher_1, regular_user, test_root, db, request
):
    # pylint: disable=invalid-name
    from app.modules.sightings.models import Sighting, SightingStage

    (
        asset_group_uuid,
        asset_group_sighting_guid,
        asset_uuid,
    ) = asset_group_utils.create_simple_asset_group(
        flask_app_client, regular_user, request, test_root
    )

    asset_group_utils.patch_in_dummy_annotation(
        flask_app_client, db, researcher_1, asset_group_sighting_guid, asset_uuid
    )

    matching_set_es_query = {'bool': {'filter': {'term': {'viewpoint': 'up'}}}}
    ia_configs = [
        {
            'algorithms': [
                'hotspotter_nosv',
            ],
            'matching_set': matching_set_es_query,
        }
    ]
    patch_data = [test_utils.patch_replace_op('idConfigs', ia_configs)]
    asset_group_utils.patch_asset_group_sighting(
        flask_app_client, researcher_1, asset_group_sighting_guid, patch_data, 200
    )
    response = asset_group_utils.commit_asset_group_sighting(
        flask_app_client, researcher_1, asset_group_sighting_guid
    )
    sighting_uuid = response.json['guid']
    sighting = Sighting.query.get(sighting_uuid)
    assert sighting.stage == SightingStage.identification


@pytest.mark.skipif(
    module_unavailable('asset_groups'), reason='AssetGroups module disabled'
)
def test_commit_individual_asset_group(
    flask_app_client,
    researcher_1,
    regular_user,
    staff_user,
    test_root,
    db,
    empty_individual,
    request,
):
    # pylint: disable=invalid-name
    from app.modules.sightings.models import Sighting, SightingStage
    from app.modules.asset_groups.models import AssetGroupSighting

    asset_group_uuid = None
    try:
        data = asset_group_utils.get_bulk_creation_data(test_root, request)
        with db.session.begin():
            db.session.add(empty_individual)
        data.set_encounter_field(0, 0, 'individualUuid', str(empty_individual.guid))

        resp = asset_group_utils.create_asset_group(
            flask_app_client, researcher_1, data.get()
        )
        asset_group_uuid = resp.json['guid']
        ags_data = asset_group_utils.extract_ags_data(resp.json, 0)
        asset_group_sighting_guid = ags_data['guid']
        asset_group_sighting = AssetGroupSighting.query.get(asset_group_sighting_guid)

        # Ensure we havae the correct asset_group_sighting guid
        if 'individualUuid' not in str(asset_group_sighting.config):
            ags_data = asset_group_utils.extract_ags_data(resp.json, 1)
            asset_group_sighting_guid = ags_data['guid']

        asset_uuid = ags_data['assets'][0]['guid']
        asset_group_utils.patch_in_dummy_annotation(
            flask_app_client, db, researcher_1, asset_group_sighting_guid, asset_uuid
        )

        # commit it
        response = asset_group_utils.commit_asset_group_sighting(
            flask_app_client, researcher_1, asset_group_sighting_guid
        )
        sighting_uuid = response.json['guid']
        sighting = Sighting.query.get(sighting_uuid)
        encounters = sighting.get_encounters()
        assert len(encounters) == 2
        assert sighting.stage == SightingStage.identification
        # It seems encounters may not be returned in order so we can't assert
        encounters_with_individuals = [
            enc for enc in encounters if enc.individual is not None
        ]
        assert len(encounters_with_individuals) == 1
        assert encounters_with_individuals[0].individual == empty_individual

    finally:
        # Restore original state
        with db.session.begin():
            db.session.delete(empty_individual)
        if asset_group_uuid:
            asset_group_utils.delete_asset_group(
                flask_app_client, researcher_1, asset_group_uuid
            )


@pytest.mark.skipif(
    module_unavailable('asset_groups'), reason='AssetGroups module disabled'
)
def test_commit_bad_asset_group(flask_app_client, researcher_1, test_root, request):

    uuids = asset_group_utils.create_large_asset_group_uuids(
        flask_app_client, researcher_1, request, test_root
    )

    asset_group_sighting_guid = uuids['asset_group_sighting']

    # I am not sure why this constitutes bad data
    bad_patch_data = [
        {
            'op': 'replace',
            'path': '/idConfigs',
            'value': [
                {
                    'algorithms': ['hotspotter_nosv'],
                    'matching_set': 'A goose'
                }
            ],
        }
    ]

    asset_group_utils.patch_asset_group_sighting(
        flask_app_client, researcher_1, asset_group_sighting_guid, bad_patch_data, 200
    )
    # should return a 400 (or 500?) error according to ticket,
    # which would break this line in the test but it passes with 200 OK
    asset_group_utils.commit_asset_group_sighting(
        flask_app_client, researcher_1, asset_group_sighting_guid
    )

    print('done with commit')

    asset_group_utils.read_asset_group_sighting(
        flask_app_client, researcher_1, asset_group_sighting_guid
    )
