# -*- coding: utf-8 -*-
"""
    blohg.plugins
    ~~~~~~~~~~~~~

    Module with stuff to import Python plugins from Mercurial repositories.

    :copyright: (c) 2010-2012 by Rafael Goncalves Martins
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

    def __init__(self, app, wrapper_module):
        self.app = app
        self.wrapper_module = wrapper_module
        with self.app.app_context():
            self.plugins = lookup_plugins()

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
        name = fullname[len(self.wrapper_module) + 1:]
        with self.app.app_context():
            if (fullname == self.wrapper_module or \
                fullname.startswith(self.wrapper_module + '.')) \
               and name in self.plugins:
                return self

    def load_module(self, fullname):
        code = self.get_code(fullname)
        ispkg = self.is_package(fullname)
        mod = sys.modules.setdefault(fullname, new_module(fullname))
        mod.__file__ = self.get_filename(fullname)
        mod.__loader__ = self
        if ispkg:
            mod.__path__ = [mod.__file__.rsplit(posixpath.sep, 1)[0]]
            mod.__package__ = fullname
        else:
            mod.__package__ = fullname.rpartition('.')[0]
        exec(code, mod.__dict__)
        return mod

    def get_fctx(self, fullname):
        with self.app.app_context():
            name = fullname[len(self.wrapper_module) + 1:]
            if name in self.plugins:
                return self.plugins[name]
        raise ImportError('Module not found: %s' % fullname)

    def is_package(self, fullname):
        fctx = self.get_fctx(fullname)
        return fctx.path.endswith(posixpath.sep + '__init__.py')

    def get_code(self, fullname):
        fctx = self.get_fctx(fullname)
        return compile(fctx.data, 'repo:%s' % fctx.path, 'exec')

    def get_source(self, fullname):
        fctx = self.get_fctx(fullname)
        return fctx.data

    def get_filename(self, fullname):
        fctx = self.get_fctx(fullname)
        return 'repo:%s' % fctx.path


def lookup_plugins():
    plugin_dir = current_app.config['PLUGIN_DIR']
    modules = {}
    for f in current_app.blohg.changectx.files:
        module_name = None
        if f.startswith(plugin_dir + posixpath.sep):
            if f.endswith(posixpath.sep + '__init__.py'):
                module_name = f[len(plugin_dir) + 1:-12]
            elif f.endswith('.py'):
                module_name = f[len(plugin_dir) + 1:-3]
        if module_name is not None:
            module_name = module_name.replace(posixpath.sep, '.')
            modules[module_name] = current_app.blohg.changectx.get_filectx(f)
    return modules
