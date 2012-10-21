# -*- coding: utf-8 -*-
#
# blohg.hgext
# ~~~~~~~~~~~
#
# Mercurial extension to manage blohg-based repositories
#
# :copyright: (c) 2010-2012 by Rafael Goncalves Martins
# :license: GPL-2, see LICENSE for more details.
#

'''manages a blohg-enabled repository
'''

import os
import sys
from mercurial import commands, cmdutil, demandimport, extensions, hg, util

demandimport.ignore.extend(['roman', 'pkg_resources', '_frozen_importlib',
                            'cStringIO'])
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blohg.utils import create_repo

cmdtable = {}
command = cmdutil.command(cmdtable)

testedwith = '2.3'
buglink = 'mailto:blohg@librelist.com'


def initblohg(orig, ui, *args, **opts):
    '''Copy the blohg template files to the repository after init if the
    latter has been invoked with --blohg
    '''
    # This function is based on code from the mq extension, that is:
    # Copyright 2005, 2006 Chris Mason <mason@suse.com>
    if not opts.pop('blohg', None):
        return orig(ui, *args, **opts)
    if args:
        repopath = args[0]
        if not hg.islocal(repopath):
            raise util.Abort('blohg only works with local repositories')
    else:
        repopath = os.getcwd()
    repopath = ui.expandpath(repopath)
    if not os.path.isdir(os.path.join(repopath, '.hg')):
        orig(ui, repopath, *args[1:], **opts)
    try:
        create_repo(repopath, ui=ui, init=False)
    except RuntimeError, e:
        raise util.Abort(e.message)


def uisetup(ui):
    entry = extensions.wrapcommand(commands.table, 'init', initblohg)
    entry[1].append(('', 'blohg', None,
                     'copy blohg templates files to the repository'))



