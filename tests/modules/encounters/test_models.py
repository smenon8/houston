# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,missing-docstring

from app.modules.users.models import User
from app.modules.encounters.models import Encounter

import logging

log = logging.getLogger(__name__)


def test_encounter_add_owner(db):

    test_user = User(
        email='testuser@localhost',
        password='testpassword',
        full_name='Gregor Samsa ',
    )

    test_encounter = Encounter()

    with db.session.begin():
        db.session.add(test_encounter)
        db.session.add(test_user)

    db.session.refresh(test_encounter)
    db.session.refresh(test_user)

    assert test_encounter.get_owner() is None

    test_user.owned_encounters.append(test_encounter)

    with db.session.begin():
        db.session.add(test_encounter)
        db.session.add(test_user)

    db.session.refresh(test_encounter)
    db.session.refresh(test_user)

    assert test_encounter.get_owner() is not None
    assert test_encounter.get_owner().guid == test_user.guid


def test_encounter_set_individual(db, empty_individual, encounter_1):

    assert empty_individual is not None
    encounter_1.set_individual(empty_individual)
    assert encounter_1.individual is not None
    assert encounter_1.individual.guid == empty_individual.guid
