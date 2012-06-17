# -*- coding: utf-8 -*-
"""
    blohg.script
    ~~~~~~~~~~~~

    Module with the CLI script related stuff.

    :copyright: (c) 2010-2012 by Rafael Goncalves Martins
    :license: GPL-2, see LICENSE for more details.
"""

import os
import sys
import posixpath
from flask_frozen import Freezer, MissingURLGeneratorWarning
from flaskext.script import Command, Manager, Server, Option
from warnings import filterwarnings
from werkzeug.routing import Map

from blohg import create_app
from blohg.utils import create_repo

# filter MissingURLGeneratorWarning warnings.
filterwarnings('ignore', category=MissingURLGeneratorWarning)


class InitRepo(Command):
    """initialize a blohg repo, using the default template."""

    def handle(self, app):
        try:
            create_repo(app)
        except RuntimeError, err:
            print >> sys.stderr, str(err)


class Freeze(Command):
    """ freeze the blog into a set of static files. """

    option_list = (Option('--serve', '-s', dest='serve', default=False,
                          action='store_true'),
                   Option('--noindex', dest='no_index', default=False,
                          action='store_true'))

    def remap_rules(self, map, map_html):
        """remaping the rules with files extensions"""
        mapping = {'views.source': 'txt',
                   'views.atom': 'atom'}
        if map_html:
            mapping['views.tag'] = 'html'
            mapping['views.content'] = 'html'
            mapping['views.post_list'] = 'html'
            mapping['views.posts'] = 'html'
            mapping['views.home'] = 'html'
        rules = []
        for rule in map.iter_rules():
            rule = rule.empty()
            if rule.is_leaf:
                # Add the leafs without modif.
                rules.append(rule)
                continue

            # special treatment for the robot.txt url
            if rule.rule == '/source/':
                rules.append(rule)
                continue

            try:
                extension = mapping[rule.endpoint]
            except KeyError:
                # the rest can go through
                rules.append(rule)
                continue
            # It becomes a leaf
            rule.is_leaf = True
            # and we add an extension
            url = rule.rule[:-1]
            if url == '':
                url = '/index'
            rule.rule = url + '.' + extension
            # and we add the modified rule
            rules.append(rule)
        return Map(rules)

    def handle(self, app, serve, no_index):

        app.url_map = self.remap_rules(app.url_map, no_index)

        # That's a risky one, it woud be better to give a parameter to the
        # freezer
        app.root_path = app.config.get('REPO_PATH')

        freezer = Freezer(app)

        def static_generator(static_dir):
            for f in app.hg.revision.manifest():
                if f.startswith(static_dir):
                    yield dict(filename=f[len(static_dir):] \
                               .strip(posixpath.sep))

        @freezer.register_generator
        def static():
            """Walk the static dir and freeze everything"""
            return static_generator(app.config['STATIC_DIR'])

        @freezer.register_generator
        def attachments():
            """Walk the attachment dir and freeze everything"""
            return static_generator(app.config['ATTACHMENT_DIR'])

        freezer.freeze()
        if serve:
            freezer.serve()


class BlohgServer(Server):

    description = 'runs the blohg local server.'

    def __init__(self, enable_plugins=True, *args, **kwargs):
        Server.__init__(self, *args, **kwargs)
        self.enable_plugins = enable_plugins

    def get_options(self):
        options = Server.get_options(self)
        if self.enable_plugins:
            options += (Option('--disable-plugins',
                               action='store_false',
                               dest='enable_plugins',
                               default=self.enable_plugins),)
        else:
            options += (Option('--enable-plugins',
                               action='store_true',
                               dest='enable_plugins',
                               default=self.enable_plugins),)
        return options

    def handle(self, app, enable_plugins, *args, **kwargs):
        app.enable_plugins = enable_plugins

        # find plugin files
        def _listfiles(directory, files):
            if not os.path.exists(directory):
                return
            for f in os.listdir(directory):
                fname = os.path.join(directory, f)
                if os.path.isdir(fname):
                    _listfiles(fname, files)
                else:
                    files.append(os.path.abspath(fname))
        app.hg.reload()
        extra_files = []
        _listfiles(os.path.join(app.repo_path, app.config['PLUGIN_DIR']),
                   extra_files)

        if 'extra_files' in self.server_options \
           and self.server_options['extra_files'] is not None:
            self.server_options['extra_files'] = \
                list(self.server_options['extra_files']) + extra_files
        else:
            self.server_options['extra_files'] = extra_files

        return Server.handle(self, app, *args, **kwargs)


def create_script():
    """Script object factory

    :param repo_path: the path to the mercurial repository.
    :return: the script object (Flask-Script' Manager instance).
    """

    script = Manager(create_app, with_default_commands=False)
    script.add_option('-r', '--repo-path', dest='repo_path',
                      default=os.getcwd(), required=False)
    script.add_command('runserver', BlohgServer(use_debugger=True,
                                                use_reloader=True,
                                                enable_plugins=True))
    script.add_command('initrepo', InitRepo())
    script.add_command('freeze', Freeze())

    return script
