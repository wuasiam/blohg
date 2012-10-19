# -*- coding: utf-8 -*-
"""
    blohg
    ~~~~~

    Main package.

    :copyright: (c) 2010-2012 by Rafael Goncalves Martins
    :license: GPL-2, see LICENSE for more details.
"""

import os
import yaml
from flask import Flask, render_template, request, _app_ctx_stack
from flask.config import ConfigAttribute
from flask.ext.babel import Babel
from jinja2.loaders import ChoiceLoader

# import blohg stuff
from blohg.hg import HgRepository, REVISION_DEFAULT, REVISION_WORKING_DIR
from blohg.models import Blog
from blohg.plugins import MercurialImporter
from blohg.static import BlohgStaticFile
from blohg.templating import BlohgLoader
from blohg.version import version as __version__
from blohg.views import views


class _GlobalsCtx(object):
    pass


class BlohgPlugin(object):

    def __init__(self, name):
        self.name = name
        # id is used as prefix for most of the plugin related stuff naming
        self.id = self.name.replace('.', '_')
        self._callbacks = []

    @property
    def globals(self):
        ctx = _app_ctx_stack.top
        if ctx is not None:
            key = self.id + '_globals'
            if not hasattr(ctx, key):
                setattr(ctx, key, _GlobalsCtx())
            return getattr(ctx, key)
        raise RuntimeError('Failed to initialize plugin globals.')

    def setup_plugin(self, f):
        self._callbacks.append(f)
        return f

    def _register_plugin(self, app):
        for callback in self._callbacks:
            if callable(callback):
                callback(app)


def register_plugin(plugin):
    ctx = _app_ctx_stack.top
    if ctx is not None:
        if not hasattr(ctx, 'plugin_registry'):
            ctx.plugin_registry = []
        ctx.plugin_registry.append(plugin)
        return
    raise RuntimeError('Failed to initialize plugin registry.')


class BlohgApp(Flask):

    enable_plugins = ConfigAttribute('ENABLE_PLUGINS')
    repo_path = ConfigAttribute('REPO_PATH')

    def wsgi_app(self, *args, **kwargs):
        if not self.got_first_request and self.enable_plugins:
            self.blohg.reload()
            MercurialImporter.new(self, 'blohg.ext')
            with self.app_context():
                try:
                    __import__('blohg.ext')
                except ImportError:
                    pass
                else:
                    ctx = _app_ctx_stack.top
                    if hasattr(ctx, 'plugin_registry'):
                        for plugin in ctx.plugin_registry:
                            if isinstance(plugin, BlohgPlugin):
                                plugin._register_plugin(self)
        return Flask.wsgi_app(self, *args, **kwargs)


class Blohg(object):

    def __init__(self, app, ui=None):
        self.app = app
        self.repo = HgRepository(self.app.config['REPO_PATH'], ui)
        self.changectx = None
        self.content = []
        app.blohg = self

    def _load_config(self):
        config = yaml.load(self.changectx.get_filectx('config.yaml').content)

        # revision can't be defined by the config.yaml file. filter it.
        if 'CHANGECTX' in config:
            del config['CHANGECTX']

        # monkey-patch configs when running from built-in server
        if 'RUNNING_FROM_CLI' in os.environ:
            if 'GOOGLE_ANALYTICS' in config:
                del config['GOOGLE_ANALYTICS']
            config['DISQUS_DEVELOPER'] = True

        self.app.config.update(config)

    def reload(self):
        # the state comes from the Flask configuration, but NOT from the yaml
        # file in the repository.
        revision_name = self.app.config['CHANGECTX'].lower()
        if revision_name == 'default':
            self.revision_id = REVISION_DEFAULT
        elif revision_name == 'working_dir':
            self.revision_id = REVISION_WORKING_DIR
        else:
            raise RuntimeError('Invalid revision: %s' % revision_name)

        # if called from the initrepo script command the repository will not
        # exists, then it shouldn't be loaded
        if not os.path.exists(self.repo.path):
            return

        if self.changectx is not None and not self.changectx.needs_reload():
            return

        self.changectx = self.repo.get_changectx(self.revision_id)
        self._load_config()

        # build a regular expression for search posts/pages.
        content_dir = self.app.config.get('CONTENT_DIR', 'content')
        post_ext = self.app.config.get('POST_EXT', '.rst')
        rst_header_level = self.app.config['RST_HEADER_LEVEL']

        self.content = Blog(self.changectx, content_dir, post_ext,
                            rst_header_level)


def create_app(repo_path=None, ui=None):
    """Application factory.

    :param repo_path: the path to the mercurial repository.
    :return: the WSGI application (Flask instance).
    """

    # create the app object
    app = BlohgApp(__name__)

    # register some sane default config values
    app.config.setdefault('AUTHOR', u'Your Name Here')
    app.config.setdefault('POSTS_PER_PAGE', 10)
    app.config.setdefault('TAGLINE', u'Your cool tagline')
    app.config.setdefault('TITLE', u'Your title')
    app.config.setdefault('TITLE_HTML', u'Your HTML title')
    app.config.setdefault('CONTENT_DIR', 'content')
    app.config.setdefault('TEMPLATES_DIR', 'templates')
    app.config.setdefault('STATIC_DIR', 'static')
    app.config.setdefault('ATTACHMENT_DIR', 'content/attachments')
    app.config.setdefault('PLUGIN_DIR', 'plugins')
    app.config.setdefault('ROBOTS_TXT', True)
    app.config.setdefault('SHOW_RST_SOURCE', True)
    app.config.setdefault('POST_EXT', '.rst')
    app.config.setdefault('ENABLE_PLUGINS', False)
    app.config.setdefault('OPENGRAPH', True)
    app.config.setdefault('TIMEZONE', 'UTC')
    app.config.setdefault('RST_HEADER_LEVEL', 3)
    app.config.setdefault('CHANGECTX', 'default')

    app.config['REPO_PATH'] = repo_path

    Blohg(app, ui)

    # setup our jinja2 custom loader and static file handlers
    old_loader = app.jinja_loader
    app.jinja_loader = ChoiceLoader([BlohgLoader(app), old_loader])
    app.add_url_rule(app.static_url_path + '/<path:filename>',
                     endpoint='static',
                     view_func=BlohgStaticFile(app, 'STATIC_DIR'))
    app.add_url_rule('/attachments/<path:filename>', endpoint='attachments',
                     view_func=BlohgStaticFile(app, 'ATTACHMENT_DIR'))

    # setup extensions
    babel = Babel(app)

    @app.before_request
    def before_request():
        app.blohg.reload()

    @app.context_processor
    def setup_jinja2():
        return dict(
            version=__version__,
            is_post=lambda x: x.startswith('post/'),
            current_path=request.path.strip('/'),
            active_page=request.path.strip('/').split('/')[0],
            tags=app.blohg.content.tags,
            config=app.config,
        )

    @babel.timezoneselector
    def get_timezone():
        return app.config['TIMEZONE']

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('404.html'), 404

    app.register_blueprint(views)

    return app
