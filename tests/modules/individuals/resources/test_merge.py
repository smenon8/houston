# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

from tests.modules.individuals.resources import utils as individual_utils
import pytest
from tests import utils as test_utils
import logging

log = logging.getLogger(__name__)


@pytest.mark.skipif(
    test_utils.module_unavailable('individuals', 'encounters', 'sightings'),
    reason='Individuals module disabled',
)
def test_merge_basics(db, flask_app_client, researcher_1, request, test_root):
    from app.modules.individuals.models import Individual

    individual1_uuids = individual_utils.create_individual_and_sighting(
        flask_app_client,
        researcher_1,
        request,
        test_root,
    )
    individual2_uuids = individual_utils.create_individual_and_sighting(
        flask_app_client,
        researcher_1,
        request,
        test_root,
    )

    individual1_id = individual1_uuids['individual']
    individual2_id = individual2_uuids['individual']

    data_in = {}  # first try with bunk data
    response = individual_utils.merge_individuals(
        flask_app_client,
        researcher_1,
        individual1_id,
        data_in,
        expected_status_code=500,
    )
    assert 'message' in response and 'list of individuals' in response['message']

    # send an invalid guid
    bad_id = '00000000-0000-0000-0000-000000002170'
    data_in = [bad_id]
    response = individual_utils.merge_individuals(
        flask_app_client,
        researcher_1,
        individual1_id,
        data_in,
        expected_status_code=500,
    )
    assert 'message' in response and f'{bad_id} is invalid' in response['message']

    # now with valid list of from-individuals
    data_in = {
        'fromIndividualIds': [individual2_id],
    }
    # data_in = [individual2_id]  # would also be valid
    # note: this tests positive permission case as well (user owns everything)
    response = individual_utils.merge_individuals(
        flask_app_client,
        researcher_1,
        individual1_id,
        data_in,
    )
    individual2 = Individual.query.get(individual2_id)
    assert not individual2


@pytest.mark.skipif(
    test_utils.module_unavailable('individuals', 'encounters', 'sightings'),
    reason='Individuals module disabled',
)
def test_merge_permissions(
    db,
    flask_app_client,
    researcher_1,
    researcher_2,
    contributor_1,
    request,
    test_root,
):
    from app.modules.individuals.models import Individual

    individual1_uuids = individual_utils.create_individual_and_sighting(
        flask_app_client,
        researcher_1,
        request,
        test_root,
    )
    # Second one owned by different researcher
    individual2_uuids = individual_utils.create_individual_and_sighting(
        flask_app_client,
        researcher_2,
        request,
        test_root,
    )

    individual1_id = individual1_uuids['individual']
    encounter1_id = individual1_uuids['encounters'][0]
    individual2_id = individual2_uuids['individual']

    # this tests as researcher_2, which should trigger a merge-request (owns just 1 encounter)
    data_in = [individual2_id]
    response = individual_utils.merge_individuals(
        flask_app_client,
        researcher_2,
        individual1_id,
        data_in,
        expected_fields={
            'merge_request',
            'request_id',
            'deadline',
            'blocking_encounters',
        },
    )
    assert response['merge_request']
    assert response['blocking_encounters'] == [encounter1_id]
    # check that the celery task is there and contains what it should
    assert response['request_id']
    try:
        req_data = Individual.get_merge_request_data(response['request_id'])
        assert req_data
        assert req_data['request']['args'][0] == individual1_id
    except NotImplementedError:
        log.info('Merge-request test skipped; no celery workers available')

    # a user who owns none (403 fail, no go)
    response = individual_utils.merge_individuals(
        flask_app_client,
        contributor_1,
        individual1_id,
        data_in,
        expected_status_code=403,
    )

    # anonymous (401)
    response = individual_utils.merge_individuals(
        flask_app_client,
        None,
        individual1_id,
        data_in,
        expected_status_code=401,
    )


@pytest.mark.skipif(
    test_utils.module_unavailable('individuals', 'encounters', 'sightings'),
    reason='Individuals module disabled',
)
def test_get_data_and_voting(
    db,
    flask_app_client,
    researcher_1,
    researcher_2,
    contributor_1,
    request,
    test_root,
):
    from app.modules.individuals.models import Individual, IndividualMergeRequestVote
    from app.modules.notifications.models import NotificationType

    bad_id = '00000000-0000-0000-0000-000000002170'
    # first anon permission check (401)
    response = individual_utils.get_merge_request(
        flask_app_client,
        None,
        bad_id,
        expected_status_code=401,
    )

    # first lets see if we have celery running, cuz things go south if we do not
    try:
        data = Individual.get_merge_request_data(bad_id)
        assert not data
    except NotImplementedError:
        pytest.skip('celery not running')

    # invalid id (404)
    response = individual_utils.get_merge_request(
        flask_app_client,
        contributor_1,  # just needs to not be anon
        bad_id,
        expected_status_code=404,
    )

    # now we need real data
    ind1_name = 'Archibald'
    ind1_data = {'names': [{'context': 'Top', 'value': ind1_name}]}
    individual1_uuids = individual_utils.create_individual_and_sighting(
        flask_app_client, researcher_1, request, test_root, individual_data=ind1_data
    )
    # Second one owned by different researcher
    individual2_uuids = individual_utils.create_individual_and_sighting(
        flask_app_client,
        researcher_2,
        request,
        test_root,
    )

    individual1_id = individual1_uuids['individual']
    encounter1_id = individual1_uuids['encounters'][0]
    individual2_id = individual2_uuids['individual']

    # do not need to delete individual2, as merge succeeds with vote below
    # request.addfinalizer(
    #    lambda: individual_res_utils.delete_individual(
    #        flask_app_client, researcher_2, individual2_id
    #    )
    # )

    from tests.modules.notifications.resources import utils as notif_utils

    notif_utils.mark_all_notifications_as_read(flask_app_client, researcher_1)

    # this tests as researcher_2, which should trigger a merge-request (owns just 1 encounter)
    data_in = [individual2_id]
    response = individual_utils.merge_individuals(
        flask_app_client,
        researcher_2,
        individual1_id,
        data_in,
        expected_fields={
            'merge_request',
            'request_id',
            'deadline',
            'blocking_encounters',
        },
    )

    assert response['merge_request']
    assert response['blocking_encounters'] == [encounter1_id]
    request_id = response.get('request_id')
    assert request_id

    # Researcher 1 should have been notified
    from tests.modules.notifications.resources import utils as notif_utils

    # to check that reading does not resolve the merge request notif
    notif_utils.mark_all_notifications_as_read(flask_app_client, researcher_1)
    res1_notifs = notif_utils.read_all_notifications(flask_app_client, researcher_1)
    assert len(res1_notifs.json) == 1
    notif_message = res1_notifs.json[0]
    assert notif_message['is_read']
    assert not notif_message['is_resolved']
    assert str(researcher_2.guid) == notif_message['sender_guid']
    assert 'individual_merge_request' == notif_message['message_type']
    assert len(notif_message['message_values']['individual_list']) == 1
    individual_notif = notif_message['message_values']['individual_list'][0]
    assert individual_notif['guid'] == individual1_id
    assert individual_notif['primaryName'] == ind1_name

    # we should have a valid merge request now to test against
    #   also should have 1 auto-vote by researcher_2
    voters = IndividualMergeRequestVote.get_voters(request_id)
    assert len(voters) == 1
    assert voters[0] == researcher_2

    # so now we test unauthorized user (403)
    response = individual_utils.get_merge_request(
        flask_app_client,
        contributor_1,
        request_id,
        expected_status_code=403,
    )

    # now this get-data should work
    response = individual_utils.get_merge_request(
        flask_app_client,
        researcher_1,
        request_id,
    )
    assert response.json
    assert 'request' in response.json
    assert response.json['request'].get('id') == request_id

    # we also make sure the req shows up in /users/me
    with flask_app_client.login(researcher_1, auth_scopes=('users:read',)):
        response = flask_app_client.get('/api/v1/users/me')
    assert response.json
    assert 'individual_merge_requests' in response.json
    assert len(response.json['individual_merge_requests']) > 0
    match = False
    for req in response.json['individual_merge_requests']:
        if 'request' in req and req['request'].get('id') == request_id:
            match = True
    assert match

    # invalid vote (422)
    response = individual_utils.vote_merge_request(
        flask_app_client,
        researcher_1,
        request_id,
        'fubar',
        expected_status_code=422,
    )

    # valid vote (will incidentally also do merge!)
    response = individual_utils.vote_merge_request(
        flask_app_client,
        researcher_1,
        request_id,
        'allow',
    )
    assert response.json
    assert response.json.get('vote') == 'allow'
    voters = IndividualMergeRequestVote.get_voters(request_id)
    assert len(voters) == 2
    assert set(voters) == set([researcher_1, researcher_2])

    # test the is_resolved field on merge notifications
    res1_notifs = notif_utils.read_all_notifications(flask_app_client, researcher_1)
    assert len(res1_notifs.json) == 2
    merge_req_notif = notif_utils.filter_notif_type(
        res1_notifs.json, NotificationType.individual_merge_request
    )[0]
    merge_approved_notif = notif_utils.filter_notif_type(
        res1_notifs.json, NotificationType.individual_merge_complete
    )[0]
    # request is resolved now that the merge has occurred
    assert merge_req_notif.get('is_resolved')
    assert not merge_approved_notif.get('is_read')
    assert not merge_approved_notif.get('is_resolved')
    notif_utils.mark_all_notifications_as_read(flask_app_client, researcher_1)
    res1_notifs = notif_utils.read_all_notifications(flask_app_client, researcher_1)
    merge_approved_notif = notif_utils.filter_notif_type(
        res1_notifs.json, NotificationType.individual_merge_complete
    )[0]
    assert merge_approved_notif.get('is_read')
    assert merge_approved_notif.get('is_resolved')

    IndividualMergeRequestVote.query.delete()
