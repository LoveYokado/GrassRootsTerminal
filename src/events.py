# SPDX-FileCopyrightText: 2025-2026 mid.yuki(LoveYokado)
# SPDX-License-Identifier: GPL-2.0-or-later

"""WebSocketイベントハンドラ。

このモジュールは、Webターミナルクライアントとのリアルタイム通信を担う
SocketIOイベントハンドラを定義します。クライアント接続のライフサイクル
(接続、認証、入力処理、切断) を管理します。
"""

from flask import request, session, url_for, current_app
from flask_socketio import emit, disconnect
import logging
import os
import glob
import uuid
import json
import shutil
import ipaddress
from werkzeug.utils import secure_filename

from . import terminal_handler, util


def init_events(socketio, app):
    """全てのSocketIOイベントハンドラを初期化し、登録します。"""

    @socketio.on('connect')
    def handle_connect(auth=None):
        """新しいクライアントのWebSocket接続を処理し、セッションを初期化します。"""

        with terminal_handler.current_webapp_clients_lock:
            max_clients = util.app_config.get('server', {}).get(
                'max_concurrent_webapp_clients', 4)
            if max_clients > 0 and terminal_handler.current_webapp_clients >= max_clients:
                return False
            terminal_handler.current_webapp_clients += 1

        username = 'GUEST'
        ip_addr = util.get_client_ip()
        display_name = util.get_display_name(username, ip_addr)
        logging.getLogger('grbbs.access').info(
            f"CONNECT - User: {username}, DisplayName: {display_name}, IP: {ip_addr}, SID: {request.sid}")

        sid = request.sid
        user_session_data = {
            'user_id': 0, 'display_name': display_name,
            'username': username, 'userlevel': 0,
            'lastlogin': 0, 'menu_mode': '2'
        }
        handler = terminal_handler.WebTerminalHandler(
            app, sid, user_session_data, ip_addr, socketio)
        terminal_handler.client_states[sid] = handler

    @socketio.on('set_speed')
    def handle_set_speed(speed_name):
        """クライアントからBPSレート設定を受け取り、通信速度をシミュレートします。"""
        sid = request.sid
        if sid in terminal_handler.client_states:
            handler = terminal_handler.client_states[sid]
            handler.speed = speed_name
            handler.bps_delay = terminal_handler.BPS_DELAYS.get(speed_name, 0)

    @socketio.on('disconnect')
    def handle_disconnect():
        """クライアントの切断イベントを処理し、関連リソースをクリーンアップします。"""
        with terminal_handler.current_webapp_clients_lock:
            terminal_handler.current_webapp_clients = max(
                0, terminal_handler.current_webapp_clients - 1)

        sid = request.sid
        handler = terminal_handler.client_states.get(sid)

        username = handler.user_session.get(
            'username', 'Unknown') if handler else 'Unknown'
        display_name = "Unknown"
        if handler:
            display_name = handler.user_session.get(
                'display_name', username)
        ip_addr = util.get_client_ip()

        if sid in terminal_handler.client_states:
            terminal_handler.client_states[sid].stop_worker()
            del terminal_handler.client_states[sid]

    @socketio.on('client_input')
    def handle_client_input(data):
        """クライアントからのキーボード入力を受け取り、入力キューに追加します。"""
        sid = request.sid
        if sid in terminal_handler.client_states:
            handler = terminal_handler.client_states[sid]
            handler.input_queue.put(data)

    @socketio.on('multiline_input_submit')
    def handle_multiline_input_submit(data):
        """マルチラインエディタからの入力を受け取り、入力キューに追加します。"""
        sid = request.sid
        if sid in terminal_handler.client_states:
            handler = terminal_handler.client_states[sid]
            content = data.get('content', '')
            handler.input_queue.put(content.replace('\n', '\r'))

    @socketio.on('toggle_logging')
    def handle_toggle_logging():
        """クライアントのセッションログ記録の開始/停止を切り替えます。"""
        sid = request.sid
        if sid in terminal_handler.client_states:
            handler = terminal_handler.client_states[sid]
            if handler.is_logging:
                handler.is_logging = False
                log_content = "".join(handler.log_buffer)
                handler.log_buffer.clear()
                if not log_content.strip():
                    emit('logging_stopped', {'message': 'ログに内容がありません。'})
                    return
                terminal_name = util.app_config.get(
                    'server', {}).get('TERMINAL_NAME', 'GR-Terminal')
                timestamp = util.datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                display_name_for_log = handler.user_session.get(
                    'display_name', handler.user_session.get('username'))
                # ファイル名を無害化
                safe_display_name = secure_filename(display_name_for_log)
                filename = f"{terminal_name}_{safe_display_name}_{timestamp}.log"
                filepath = os.path.join(
                    current_app.config['SESSION_LOG_DIR'], filename)
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(log_content)
                    download_url = url_for(
                        'web.download_log', filename=filename)
                    emit('log_saved', {
                         'url': download_url, 'filename': filename})
                except Exception as e:
                    emit('logging_stopped', {'message': 'ログファイルの保存に失敗しました。'})
            else:
                handler.is_logging = True
                handler.log_buffer.clear()
                emit('logging_started')
