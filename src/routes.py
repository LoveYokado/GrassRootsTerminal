# SPDX-FileCopyrightText: 2025-2026 LoveYokado
# SPDX-License-Identifier: GPL-2.0-or-later

"""Webアプリケーションのルート定義。

このモジュールは、ログイン、ログアウト、メインのターミナルページといった、
アプリケーションの標準的なWebルートを定義します。FlaskのBlueprintを
使用して、これらのルートをコアロジックから分離し、整理しています。
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    send_from_directory, jsonify, Response, current_app, flash
)
from werkzeug.utils import secure_filename
from functools import wraps
import os
import time
import logging
from . import util, extensions

web_bp = Blueprint('web', __name__)


@web_bp.route('/manifest.json')
def manifest():
    """PWA (Progressive Web App) のマニフェストファイルを配信します。"""
    return send_from_directory(current_app.static_folder, 'manifest.json')


@web_bp.route('/sw.js')
def service_worker():
    """PWAのService Workerファイルを配信します。"""
    response = send_from_directory(current_app.static_folder, 'sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response


@web_bp.route('/')
def index():
    """メインのターミナルページを描画します。"""
    # クッキーから表示モードを取得（デフォルトは'1':英語）
    menu_mode = request.cookies.get('menu_mode', '1')
    fkey_definitions = {
        "f1": {"label": "SETTING", "action": "open_popup"},
        "f2": {"label": "LOGGING", "action": "toggle_logging"},
        "f3": {"label": "NoFunction", "action": "none"},
        "f4": {"label": "NoFunction", "action": "none"},
        "f5": {"label": "Line Edit", "action": "open_line_editor"},
        "f6": {"label": "Multi Edit", "action": "open_multiline_editor"},
        "f8": {"label": "ReConnect", "action": "redirect", "value": "/"},
    }

    all_text_data = util.load_master_text_data()
    mobile_button_layouts = all_text_data.get("mobile_button_layouts", {})

    def _process_texts_for_mode(node, mode):
        if isinstance(node, dict):
            mode_key = f"mode_{mode}"
            if mode_key in node:
                return node[mode_key]
            else:
                return {key: _process_texts_for_mode(value, mode) for key, value in node.items()}
        return node

    textData_for_js = {
        "terminal_ui": _process_texts_for_mode(all_text_data.get("terminal_ui", {}), menu_mode),
        "user_pref_menu": _process_texts_for_mode(all_text_data.get("user_pref_menu", {}), menu_mode)
    }

    return render_template('terminal.html', fkey_definitions=fkey_definitions, mobile_button_layouts=mobile_button_layouts, menu_mode=menu_mode, textData=textData_for_js, user_level=0)


@web_bp.route('/download_log/<path:filename>')
def download_log(filename):
    """保存されたセッションログファイルをダウンロードさせます。"""
    session_log_dir = current_app.config.get('SESSION_LOG_DIR')
    return send_from_directory(session_log_dir, filename, as_attachment=True)
