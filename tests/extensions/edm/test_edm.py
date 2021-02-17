# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,missing-docstring

import uuid

# this tests edm hostname & credentials configs


def test_edm_initializes(flask_app):
    flask_app.edm._ensure_initialized()
    # if we get this far, we may be a valid user but not one with sufficient privs on edm, so lets find out:
    response = flask_app.edm.get_dict('encounter.data', uuid.uuid4())
    # one should *only* get a 404 here (request allowed for user -- but not found) versus 401/403 or 5xx
    # a 401 or 403 means valid login for edm, but that login has bad permissions!
    # if you get a 200 here, see jon for a prize
    assert response.status_code == 404
