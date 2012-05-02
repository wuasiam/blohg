# -*- coding: utf-8 -*-
"""
    blohg.hgapi.plugins
    ~~~~~~~~~~~~~~~~~~~

    Module with stuff to import Python plugins from Mercurial repositories.

    :copyright: (c) 2011 by Rafael Goncalves Martins
    :license: GPL-2, see LICENSE for more details.
"""

from flask import current_app
from imp import new_module

import posixpath
import sys


class MercurialImporter(object):
    """Loader and Finder to import Python plugins from the Mercurial
    repository. Mostly based on:
    https://github.com/mitsuhiko/flask/blob/master/flask/exthook.py

    See PEP 302 for details.
    """

    def __init__(self, wrapper_module):
        self.wrapper_module = wrapper_module

    def __eq__(self, other):
        return self.__class__.__module__ == other.__class__.__module__ and \
               self.__class__.__name__ == other.__class__.__name__ and \
               self.wrapper_module == other.wrapper_module

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def new(*args, **kwargs):
        obj = MercurialImporter(*args, **kwargs)
        sys.meta_path[:] = [x for x in sys.meta_path if obj != x] + [obj]
        return obj

    def find_module(self, fullname, path=None):
        if fullname == self.wrapper_module or \
           fullname.startswith(self.wrapper_module + '.'):
            return self

    def load_module(self, fullname):
        name = fullname[len(self.wrapper_module)+1:]
        modules = lookup_plugins()
        if name in modules:
            fctx = modules[name]
            fname = fctx.path()
            sys.modules[fullname] = mod = new_module(fullname)
            mod.__loader__ = self
            mod.__file__ = 'repo:' + fname
            if fname.endswith(posixpath.sep + '__init__.py'):
                mod.__path__ = [fname.rsplit(posixpath.sep, 1)[0]]
            code = compile(fctx.data(), mod.__file__, 'exec')
            exec code in mod.__dict__
            return mod


def lookup_plugins():
    plugin_dir = current_app.config['PLUGIN_DIR']
    modules = {}
    for f in current_app.hg.revision.manifest():
        module_name = None
        if f.startswith(plugin_dir + posixpath.sep):
            if f.endswith(posixpath.sep + '__init__.py'):
                module_name = f[len(plugin_dir) + 1:-12]
            elif f.endswith('.py'):
                module_name = f[len(plugin_dir) + 1:-3]
        if module_name is not None:
            module_name = module_name.replace(posixpath.sep, '.')
            modules[module_name] = current_app.hg.revision[f]
    return modules
