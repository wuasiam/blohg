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


class BlohgImporter(object):
    """Loader and Finder to import Python plugins from the Mercurial
    repository. Mostly based on:
    https://github.com/mitsuhiko/flask/blob/master/flask/exthook.py

    See PEP 302 for details.
    """

    def __init__(self, wrapper_module):
        self.wrapper_module = wrapper_module
        self.prefix = wrapper_module + '.'

    def __eq__(self, other):
        return self.__class__.__module__ == other.__class__.__module__ and \
               self.__class__.__name__ == other.__class__.__name__ and \
               self.wrapper_module == other.wrapper_module

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def new(*args,  **kwargs):
        obj = BlohgImporter(*args, **kwargs)
        sys.meta_path[:] = [x for x in sys.meta_path if obj != x] + [obj]
        return obj

    def find_module(self, fullname, path=None):
        if fullname.startswith(self.prefix):
            return self

    def load_module(self, fullname):
        name = fullname[len(self.prefix):]
        modules = self.lookup_modules()
        if name in modules:
            filename = modules[name].path()
            sys.modules[fullname] = mod = new_module(fullname)
            mod.__loader__ = self
            mod.__file__ = 'repo:' + filename
            if filename.endswith(posixpath.sep + '__init__.py'):
                mod.__path__ = [filename.rsplit(posixpath.sep, 1)[0]]
            exec modules[name].data() in mod.__dict__
            return mod

    def lookup_modules(self):
        plugin_dir = current_app.config['PLUGIN_DIR']
        modules = {}
        for f in current_app.hg.revision:
            module_name = None
            if f.startswith(plugin_dir + posixpath.sep):
                if f.endswith(posixpath.sep + '__init__.py'):
                    module_name = f[len(plugin_dir) + 1:-12]
                elif f.endswith('.py'):
                    module_name = f[len(plugin_dir) + 1:-3]
            if module_name is not None and len(module_name) > 0:
                module_name = module_name.replace(posixpath.sep, '.')
                modules[module_name] = current_app.hg.revision[f]
        return modules
