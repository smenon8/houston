# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
import tests.modules.keywords.resources.utils as keyword_utils
from app.modules.keywords.models import Keyword
from tests import utils as test_utils


def test_get_keyword_not_found(flask_app_client, researcher_1):
    import uuid

    keyword_utils.read_keyword(flask_app_client, None, str(uuid.uuid4()), 401)
    keyword_utils.read_keyword(flask_app_client, researcher_1, str(uuid.uuid4()), 404)


def test_create_keyword(db, flask_app_client, researcher_1):
    orig_ct = test_utils.row_count(db, Keyword)
    val = 'test_keyword_0'
    response = keyword_utils.create_keyword(flask_app_client, researcher_1, val)
    assert response.json.get('value', None) == val
    assert test_utils.row_count(db, Keyword) == orig_ct + 1

    # anon should *not* be able to create/write
    response = keyword_utils.create_keyword(
        flask_app_client, None, 'keyword_fail', expected_status_code=403
    )
    assert test_utils.row_count(db, Keyword) == orig_ct + 1

    # this should fail due to non-uniqueness (conflict/409)
    response = keyword_utils.create_keyword(
        flask_app_client, researcher_1, val, expected_status_code=409
    )

    # this should fail due to invalid source (422)
    response = keyword_utils.create_keyword(
        flask_app_client, researcher_1, 'FAIL', source='FAIL', expected_status_code=422
    )


def test_read_all_keywords(db, flask_app_client, researcher_1, staff_user):
    orig_ct = test_utils.row_count(db, Keyword)
    keyword_utils.create_keyword(
        flask_app_client, researcher_1, 'list_test'
    )  # lets have at least one
    response = keyword_utils.read_all_keywords(flask_app_client, None)
    assert len(response.json) == orig_ct + 1

    # Clean-up
    for keyword in response.json:
        guid = keyword.get('guid', None)
        keyword_utils.delete_keyword(flask_app_client, staff_user, guid)


def test_modify_keyword(db, flask_app_client, researcher_1, staff_user):
    orig_ct = test_utils.row_count(db, Keyword)
    val1 = 'test_keyword_1'
    response = keyword_utils.create_keyword(flask_app_client, researcher_1, val1)
    guid = response.json.get('guid', None)
    assert guid
    assert response.json.get('value', None) == val1
    assert test_utils.row_count(db, Keyword) == orig_ct + 1
    response = keyword_utils.read_keyword(flask_app_client, researcher_1, guid)
    assert guid == response.json.get('guid', None)
    assert response.json.get('value', None) == val1

    # patch and verify
    val2 = 'test_keyword_2'
    patch = [{'op': 'replace', 'path': '/value', 'value': val2}]
    response = keyword_utils.patch_keyword(flask_app_client, staff_user, guid, patch)
    assert response.json.get('value', None) == val2
    # doublecheck by reading back in
    response = keyword_utils.read_keyword(flask_app_client, researcher_1, guid)
    assert response.json.get('value', None) == val2

    # both of these should not be allowed (403)
    response = keyword_utils.patch_keyword(
        flask_app_client, researcher_1, guid, patch, 403
    )
    response = keyword_utils.delete_keyword(flask_app_client, researcher_1, guid, 403)

    # should not be allowed to patch source (422)
    patch = [{'op': 'replace', 'path': '/source', 'value': 'user'}]
    response = keyword_utils.patch_keyword(flask_app_client, staff_user, guid, patch, 422)

    # should successfully kill this
    response = keyword_utils.delete_keyword(flask_app_client, staff_user, guid)
    assert orig_ct == test_utils.row_count(db, Keyword)
