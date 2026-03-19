# SPDX-FileCopyrightText: 2025-2026 LoveYokado
# SPDX-License-Identifier: GPL-2.0-or-later

"""アプリケーションファクトリ。

このモジュールは、Flaskアプリケーションインスタンスの作成と設定を行う、
`create_app()` ファクトリ関数を提供します。アプリケーションの全体的な設定、
Blueprintの登録、拡張機能の初期化など、起動に関する中核的な処理を担当します。
"""

import datetime
import ipaddress
import threading
import logging
import os
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

from flask import Blueprint, Flask, Response, redirect, session, url_for
from flask import request
from markupsafe import escape, Markup
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix
from . import util, extensions
from .routes import web_bp
from .events import init_events

# --- グローバル変数 ---
socketio = SocketIO()


def create_app():
    """Flaskアプリケーションインスタンスを作成し、設定を初期化します。"""
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(_current_dir)
    APP_LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
    SESSION_LOG_DIR = os.path.join(APP_LOG_DIR, 'webapp_sessions')

    app = Flask(__name__, static_folder='../static',
                template_folder='../templates')

    config_path = os.path.join(PROJECT_ROOT, 'setting', 'config.toml')
    util.load_app_config_from_path(config_path)
    uppercase_config = {key.upper(): value for key,
                        value in util.app_config.items()}
    app.config.from_mapping(uppercase_config)
    app.config['PROJECT_ROOT'] = PROJECT_ROOT

    webapp_config = app.config.get('WEBAPP', {})
    origin = webapp_config.get('ORIGIN', 'http://localhost:5000')
    parsed_origin = urlparse(origin)
    app.config['SERVER_NAME'] = parsed_origin.hostname
    if parsed_origin.port:
        app.config['SERVER_NAME'] += f":{parsed_origin.port}"
    app.config['PREFERRED_URL_SCHEME'] = parsed_origin.scheme

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1,
                            x_proto=1, x_host=1, x_prefix=1)

    os.makedirs(APP_LOG_DIR, exist_ok=True)
    os.makedirs(SESSION_LOG_DIR, exist_ok=True)
    app.config['SESSION_LOG_DIR'] = SESSION_LOG_DIR

    access_logger = logging.getLogger('grbbs.access')
    access_logger.setLevel(logging.INFO)
    access_handler = RotatingFileHandler(
        os.path.join(APP_LOG_DIR, 'grbbs.access.log'),
        maxBytes=1024 * 1024 * 5, backupCount=3, encoding='utf-8'
    )
    access_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s'))
    access_logger.addHandler(access_handler)
    access_logger.propagate = False

    app.register_blueprint(web_bp)

    @app.context_processor
    def inject_util():
        return dict(util=util)

    @app.after_request
    def add_security_headers(response):
        csp = (
            "default-src 'self';"
            "script-src 'self' 'unsafe-inline' https://cdn.socket.io https://cdn.jsdelivr.net;"
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com;"
            "font-src 'self' https://fonts.gstatic.com;"
            "img-src 'self' data:;"
            "connect-src 'self' wss: ws:;"
            "frame-ancestors 'none';"
            "form-action 'self';"
            "base-uri 'self';"
        )
        response.headers['Content-Security-Policy'] = csp
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # 開発中はCORSの問題を回避するため、すべてのオリジンを許可します。
    # 本番環境では、実際のドメインに限定することを推奨します。
    allowed_origins = "*"

    engineio_options = {
        "async_mode": "gevent",
        "ws_proxy_fix": True,
        "max_http_buffer_size": 12 * 1024 * 1024
    }
    socketio.init_app(
        app, cors_allowed_origins=allowed_origins, **engineio_options)

    init_events(socketio, app)

    return app, socketio
