# SPDX-FileCopyrightText: 2025-2026 LoveYokado
# SPDX-License-Identifier: GPL-2.0-or-later

"""Webターミナルセッションハンドラモジュール。

このモジュールは、個々のWebターミナルセッションを管理するための中核ロジックを提供します。
WebTerminalHandlerクラスは各クライアントのセッション状態を管理し、BBSのメインループとI/Oを統括します。
また、接続されている全クライアントのグローバルな状態も管理します。
"""

import logging
import threading  # stop_worker_event で利用
from gevent.queue import Queue
import socket
import codecs
import unicodedata
import time
import re
import datetime

from . import util

# --- Global State for Web Terminal Clients / Webターミナルクライアントの状態管理 ---

# {sid: WebTerminalHandler_instance}
# 接続中の全クライアントのハンドラインスタンスを保持するグローバル辞書。
client_states = {}

# 現在接続しているWebターミナルクライアントの数を追跡します。
current_webapp_clients = 0
current_webapp_clients_lock = threading.Lock()


# --- Constants for Simulated Baud Rates / 擬似BPSレート用定数 ---
BPS_DELAYS = {
    '300': 10.0 / 300,
    '2400': 10.0 / 2400,
    '4800': 10.0 / 4800,
    '9600': 10.0 / 9600,
    'full': 0,
}


class WebTerminalHandler:
    """
    単一のWebターミナルセッションの状態とロジックを管理するクラス。

    接続されたクライアントごとにインスタンスが生成されます。BBSのメインループを
    バックグラウンドタスクとして実行し、クライアントとのI/Oを仲介します。

    Attributes:
        sid (str): SocketIOのセッションID。
        user_session (dict): ユーザーのセッション情報。
    """

    def __init__(self, app, sid, user_session, ip_address, socketio):
        self.sid = sid
        self.user_session = user_session
        self.ip_address = ip_address
        self.socketio = socketio
        self.speed = 'full'
        self.app = app  # Flaskアプリケーションインスタンスを保持
        self.bps_delay = 0
        self.output_queue = Queue()
        self.input_queue = Queue()
        self.stop_worker_event = threading.Event()
        self.is_logging = False
        self.connect_time = time.time()
        self.log_buffer = []
        self.main_thread_active = True
        self.is_mobile = self.user_session.get('menu_mode') == '4'

        # クライアントのUIを制御するためのカスタムエスケープシーケンスのパターン。
        # これらのシーケンスはBPS遅延の影響を受けずに一括で送信する必要があります。
        self.control_sequence_pattern = re.compile(
            r'('
            r'\x1b\]GRBBS;[^\x07]*\x07'  # OSC: LINE_EDITなど
            r'|\x1b_GRBBS_DOWNLOAD;[^\x1b]*\x1b\\'  # APC: ファイルダウンロード
            r'|\x1b\[\?\d+[hl]'  # DEC Private Mode: UIボタンの表示/非表示
            r')'
        )
        self.channel = self.WebChannel(self, self.ip_address)
        self.socketio.start_background_task(self._sender_worker)
        self.socketio.start_background_task(self._bbs_main_loop)

    class WebChannel:
        """
        WebTerminalHandlerとBBSコアロジック間の通信を仲介する内部クラス。

        従来のソケット通信を模倣したインターフェース (`send`, `recv`など) を提供し、
        BBSの既存ロジックをWebSocket上で再利用可能にします。
        """

        def __init__(self, handler_instance, ip_addr):
            self.handler = handler_instance
            self.ip_address = ip_addr
            self.recv_buffer = b''
            self.active = True
            self._timeout = None

        def settimeout(self, timeout):
            self._timeout = timeout

        def send(self, data):
            if isinstance(data, bytes):  # バイト列の場合はUTF-8でデコード
                text_to_send = data.decode('utf-8', 'ignore')
            else:
                text_to_send = str(data)
            if self.handler.is_logging and isinstance(self.handler.log_buffer, list):
                self.handler.log_buffer.append(text_to_send)
            self.handler.output_queue.put(text_to_send)

        def recv(self, n):
            while len(self.recv_buffer) < n and self.active:
                try:
                    # geventのQueueはget()で協調的にブロックする
                    data_str = self.handler.input_queue.get(
                        timeout=self._timeout)
                    self.recv_buffer += data_str.encode('utf-8')
                except Exception:  # gevent.queue.Emptyなど
                    raise socket.timeout("timed out")
            if not self.active and not self.recv_buffer:
                return b''
            ret = self.recv_buffer[:n]
            self.recv_buffer = self.recv_buffer[n:]
            return ret

        def getpeername(self):
            return (self.ip_address, 12345)

        def close(self):
            self.active = False

        def _process_input_internal(self, echo=True):
            line_buffer = []
            decoder = codecs.getincrementaldecoder('utf-8')('ignore')
            try:
                while self.active:
                    char_byte = self.recv(1)
                    if not char_byte:
                        return None
                    if char_byte in (b'\r', b'\n'):
                        if echo:  # エコーバックが有効なら改行を送信
                            self.send(b'\r\n')
                        break
                    elif char_byte in (b'\x08', b'\x7f'):  # バックスペース処理
                        if line_buffer:
                            deleted_char = line_buffer.pop()
                            if echo:  # エコーバックが有効なら文字を削除
                                width = unicodedata.east_asian_width(
                                    deleted_char)
                                char_width = 2 if width in (
                                    'F', 'W', 'A') else 1
                                backspaces = b'\x08' * char_width
                                self.send(
                                    backspaces + (b' ' * char_width) + backspaces)
                    else:
                        try:  # UTF-8としてデコードを試みる
                            decoded_char = decoder.decode(char_byte)
                            if decoded_char:
                                line_buffer.append(decoded_char)
                                if echo:  # エコーバックが有効なら文字を送信
                                    self.send(decoded_char.encode('utf-8'))
                        except UnicodeDecodeError:
                            decoder.reset()
                            continue
            except socket.timeout:
                logging.info(
                    f"Input timeout (normal operation) (SID: {self.handler.sid})")
            except Exception as e:
                logging.error(
                    f"Error in process_input (SID: {self.handler.sid}): {e}")
                return None
            remaining = decoder.decode(b'', final=True)  # バッファに残っている文字をデコード
            if remaining:
                line_buffer.append(remaining)
            return "".join(line_buffer)

        def process_input(self):
            """
            クライアントからの入力を一行受け取ります (エコーバックあり)。

            Returns:
                str: ユーザーが入力した文字列。
            """
            return self._process_input_internal(echo=True)

        def hide_process_input(self):
            return self._process_input_internal(echo=False)

    def stop_worker(self):
        self.main_thread_active = False
        self.channel.close()
        self.stop_worker_event.set()

    def _bbs_main_loop(self):
        """
        Telnetクライアントのメインループ。
        設定ファイルで指定されたTelnetサーバーに接続します。
        """
        telnet_config = util.app_config.get('telnet', {})
        host = telnet_config.get('host', 'sbbs')
        port = telnet_config.get('port', 23)
        timeout = telnet_config.get('timeout', 10)
        encoding = 'utf-8'

        sock = None

        try:
            self.channel.send(
                f"Connecting to Synchronet BBS ({host}:{port})...\r\n".encode(encoding, 'replace'))
            sock = socket.create_connection((host, port), timeout=timeout)
            self.channel.send(
                f"Connected to {host}:{port}.\r\n".encode(encoding, 'replace'))

            # Webクライアントからの入力をソケットに送るスレッド
            def writer_thread():
                try:
                    while self.main_thread_active:
                        # 1文字ずつ読み込んで即座に送信する（キャラクターモード）
                        char_byte = self.channel.recv(1)
                        if not char_byte:
                            break
                        sock.sendall(char_byte)
                except Exception as e:
                    logging.debug(f"Writer thread exception: {e}")
                finally:
                    self.stop_worker()

            # gevent環境でバックグラウンドタスクを開始
            self.socketio.start_background_task(writer_thread)
            # ソケットからの出力をWebクライアントに送る
            while self.main_thread_active:
                data = sock.recv(4096)
                if not data:
                    break
                self.channel.send(data)

        except (ConnectionRefusedError, socket.gaierror, socket.timeout) as e:
            self.channel.send(
                f"\r\n\x1b[31mConnection failed: {e}\x1b[0m\r\n".encode(encoding, 'replace'))
        except Exception as e:
            logging.error(
                f"Echo loop error ({self.user_session.get('username')}): {e}", exc_info=True)
            try:
                self.channel.send(
                    f"\r\n\x1b[31mAn unexpected error occurred: {e}\x1b[0m\r\n".encode(encoding, 'replace'))
            except Exception:
                pass
        finally:
            if sock:
                sock.close()
            self.channel.send(b"\r\nConnection closed.\r\n")
            self.stop_worker()

    def _web_to_telnet(self, tn, encoding):
        """この関数は、echoサーバーへの接続ロジックに置き換えられたため、使用されなくなりました。"""
        pass

    def _sender_worker(self):
        """
        出力キューからテキストを送信するバックグラウンドタスク。

        キューからテキストを取り出し、クライアントに送信します。
        BPSレートをシミュレートするための遅延処理もここで行います。
        """
        while not self.stop_worker_event.is_set():
            try:
                text_to_send = self.output_queue.get(timeout=1)

                # テキストを制御シーケンスと通常のテキストに分割します。
                parts = self.control_sequence_pattern.split(text_to_send)

                for part in parts:
                    if not part:
                        continue

                    # partが制御シーケンスと完全に一致するかチェックします。
                    if self.control_sequence_pattern.fullmatch(part):
                        # 制御シーケンスは遅延なしで即時送信
                        self.socketio.emit('server_output', part, to=self.sid)
                    else:
                        # 通常のテキストはBPS設定に従って送信
                        if self.bps_delay > 0:
                            for char in part:
                                if self.stop_worker_event.is_set():
                                    break
                                self.socketio.emit(
                                    'server_output', char, to=self.sid)
                                self.socketio.sleep(self.bps_delay)
                        else:
                            self.socketio.emit(
                                'server_output', part, to=self.sid)
            except Exception:  # gevent.queue.Empty
                continue  # キューが空の場合はループを継続
