# -*- coding: utf-8 -*-
"""
    blohg.tests.hg
    ~~~~~~~~~~~~~~

    Package with tests for blohg integration with mercurial.

    :copyright: (c) 2010-2012 by Rafael Goncalves Martins
    :license: GPL-2, see LICENSE for more details.
"""

import unittest
from mercurial import commands, ui
from shutil import rmtree
from tempfile import mkdtemp

from blohg.hg import HgRepository, REVISION_DEFAULT, REVISION_WORKING_DIR
from blohg.hg.changectx import ChangeCtxDefault, ChangeCtxWorkingDir


class HgRepositoryTestCase(unittest.TestCase):

    def setUp(self):
        self.repo_path = mkdtemp()
        self.ui = ui.ui()
        self.ui.setconfig('ui', 'quiet', True)
        commands.init(self.ui, self.repo_path)

    def tearDown(self):
        try:
            rmtree(self.repo_path)
        except:
            pass

    def test_get_changectx_rev_default(self):
        hg_repo = HgRepository(self.repo_path, self.ui)
        self.assertTrue(isinstance(hg_repo.get_changectx(REVISION_DEFAULT),
                                   ChangeCtxDefault),
                        'changectx object is not an instance of '
                        'ChangeCtxDefault')

    def test_get_changectx_rev_working_dir(self):
        hg_repo = HgRepository(self.repo_path, self.ui)
        self.assertTrue(isinstance(hg_repo.get_changectx(REVISION_WORKING_DIR),
                                   ChangeCtxWorkingDir),
                        'changectx object is not an instance of '
                        'ChangeCtxWorkingDir')
