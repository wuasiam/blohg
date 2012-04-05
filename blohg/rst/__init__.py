# -*- coding: utf-8 -*-
"""
    blohg.rst
    ~~~~~~~~~

    Package with reStructuredText-related stuff needed by blohg, like
    directives and roles.

    :copyright: (c) 2010-2012 by Rafael Goncalves Martins
    :license: GPL-2, see LICENSE for more details.
"""

from docutils.core import publish_parts
from docutils.parsers.rst.directives import register_directive
from docutils.parsers.rst.roles import register_local_role

from blohg.rst.directives import index as directives_index
from blohg.rst.roles import index as roles_index
from blohg.rst.writer import BlohgWriter

# registering docutils' directives
for directive in directives_index:
    register_directive(directive, directives_index[directive])

# registering docutils' roles
for role in roles_index:
    register_local_role(role, roles_index[role])


def parser(content):
    parts = publish_parts(source=content, writer=BlohgWriter(),
                          settings_overrides={'input_encoding': 'utf-8',
                                              'output_encoding': 'utf-8',
                                              'initial_header_level': 3,
                                              'docinfo_xform': 0,
                                              'field_name_limit': None})
    return {'title': parts['title'], 'fragment': parts['fragment']}
