# -*- coding: utf-8 -*-
"""
Audit Logs module
============
"""

from app.extensions.api import api_v1


def init_app(app, **kwargs):
    # pylint: disable=unused-argument,unused-variable
    """
    Init Audit Logs module.
    """
    api_v1.add_oauth_scope('audit_logs:read', 'Provide access to Audit Logs details')

    # Touch underlying modules
    from . import models, resources  # NOQA

    api_v1.add_namespace(resources.api)