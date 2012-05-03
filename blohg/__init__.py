# -*- coding: utf-8 -*-
"""
    blohg
    ~~~~~

    Main package.

    :copyright: (c) 2010-2012 by Rafael Goncalves Martins
    :license: GPL-2, see LICENSE for more details.
"""

from flask import Flask, render_template, request, _app_ctx_stack
from flask.config import ConfigAttribute
from flaskext.babel import Babel

# import blohg stuff
from blohg.hgapi import setup_mercurial
from blohg.hgapi.plugins import lookup_plugins, MercurialImporter
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

    def init_plugin(self, f):
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


class Blohg(Flask):

    enable_plugins = ConfigAttribute('ENABLE_PLUGINS')
    repo_path = ConfigAttribute('REPO_PATH')

    def wsgi_app(self, *args, **kwargs):
        if not self.got_first_request and self.enable_plugins:
            self.hg.reload()
            MercurialImporter.new(self, 'blohg.plugins')
            with self.app_context():
                __import__('blohg.plugins')
                ctx = _app_ctx_stack.top
                if hasattr(ctx, 'plugin_registry'):
                    for plugin in ctx.plugin_registry:
                        if isinstance(plugin, BlohgPlugin):
                            plugin._register_plugin(self)
        return Flask.wsgi_app(self, *args, **kwargs)


def create_app(repo_path=None, hgui=None):
    """Application factory.

    :param repo_path: the path to the mercurial repository.
    :return: the WSGI application (Flask instance).
    """

    # create the app object
    app = Blohg(__name__)

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

    app.config['REPO_PATH'] = repo_path

    # init mercurial stuff
    setup_mercurial(app, hgui=hgui)

    # setup extensions
    babel = Babel(app)

    @app.context_processor
    def setup_jinja2():
        return dict(
            version=__version__,
            is_post=lambda x: x.startswith('post/'),
            current_path=request.path.strip('/'),
            active_page=request.path.strip('/').split('/')[0],
            tags=app.hg.tags,
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
