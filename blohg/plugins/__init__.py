# -*- coding: utf-8 -*-
"""
    blohg.plugins
    ~~~~~~~~~~~~~

    Fake module to import plugins from the Mercurial repository.

    :copyright: (c) 2011 by Rafael Goncalves Martins
    :license: GPL-2, see LICENSE for more details.
"""


def setup():
    from blohg.hgapi.plugins import MercurialImporter
    MercurialImporter.new(__name__)


setup()
del setup
