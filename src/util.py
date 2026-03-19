# SPDX-FileCopyrightText: 2025-2026 mid.yuki(LoveYokado)
# SPDX-License-Identifier: GPL-2.0-or-later


"""ユーティリティモジュール。

このモジュールは、GrassRootsBBSアプリケーション全体で共通して使用される
ヘルパー関数を提供します。設定ファイルの読み書き、テキスト処理、
パスワードハッシュ化、データフォーマットなど、多岐にわたる機能を含み、
コードの再利用性を高める役割を担います。
"""

import logging
import toml
import os
import yaml
import datetime
import re
from flask import request, session

# --- Global Variables / グローバル変数 ---
_master_text_data_cache = None


def load_app_config_from_path(config_file_path):
    """指定されたパスのTOMLファイルからアプリケーション設定を読み込みます."""
    global app_config
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            app_config = toml.load(f)
            logging.info(f"設定ファイルを読み込みました: {config_file_path}")
            _validate_config_or_log_warnings()
    except FileNotFoundError:
        logging.error(f"設定ファイル '{config_file_path}' が見つかりません。")
        raise
    except toml.TomlDecodeError as e:
        logging.error(f"設定ファイル '{config_file_path}' の読み込みエラー: {e}")
        raise


def _validate_config_or_log_warnings():
    """読み込まれた設定ファイルの基本的な検証を行い、必須セクションの欠落を警告します。"""
    required_sections = {"security", "webapp"}
    for section in required_sections:
        if section not in app_config:
            logging.warning(f"設定ファイルに必須セクション '{section}' がありません。")


def load_master_text_data():
    """メインのテキストデータファイル(`textdata.yaml`)を読み込み、メモリにキャッシュします。"""
    global _master_text_data_cache
    if _master_text_data_cache is not None:
        return _master_text_data_cache

    # テキストデータを読み込む
    paths_config = app_config.get('paths', {})
    full_path = paths_config.get('text_data_yaml', 'setting/textdata.yaml')
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            _master_text_data_cache = data
            return _master_text_data_cache
    except FileNotFoundError:
        logging.error(f"テキストデータファイル '{full_path}' が見つかりません。")
        _master_text_data_cache = {}
        return _master_text_data_cache
    except Exception as e:
        logging.error(f"テキストデータファイル '{full_path}' の読み込みエラー: {e}")
        _master_text_data_cache = {}
        return _master_text_data_cache


def get_text_by_key(key_string, mode_or_lang, default_value=""):
    """キャッシュされたテキストデータから、指定されたキーとモード/言語に対応する文字列を取得します。"""
    master_data = load_master_text_data()
    keys = key_string.split('.')
    current_level_data = master_data
    try:
        # 要素の取り出し
        for key_part in keys:
            if not isinstance(current_level_data, dict):
                logging.warning(
                    f"キー {key_string} のパス {key_part}が辞書ではありません。")
                return default_value
            current_level_data = current_level_data[key_part]

        if isinstance(current_level_data, dict):
            # まず言語キー (ja, en) を試し、次にモードキー (mode_1, mode_2) を試す
            text_value = None
            try:
                if mode_or_lang in current_level_data:
                    text_value = current_level_data[mode_or_lang]
                else:
                    mode_specific_key = f"mode_{mode_or_lang}"
                    text_value = current_level_data[mode_specific_key]
            except KeyError:
                # mode_4 が見つからない場合に mode_2 にフォールバック
                if mode_or_lang == '4':
                    logging.debug(
                        f"Key '{key_string}' not found for mode_4, falling back to mode_2.")
                    text_value = current_level_data.get('mode_2')

            if text_value is None:
                raise KeyError  # 見つからなかった場合は例外を発生させて、最終的なexceptブロックで処理

            if isinstance(text_value, list):
                return "\r\n".join(text_value)  # 複数行の場合
            return str(text_value)  # 単行の場合

        else:
            # キーの終端が辞書ではなかった場合
            logging.warning(
                f"キー {key_string}の終端が予期した形式ではありません。({mode_or_lang} をキーに持つ辞書にしてください)")
            return default_value
    except (KeyError, TypeError):
        logging.warning(
            f"キー {key_string} (mode/lang: {mode_or_lang}) に対応するテキストデータが見つかりません。")
        return default_value


def generate_guest_hash(ip_address: str) -> str:
    """IPアドレスからゲストユーザー識別用の一貫性のある短いハッシュを生成します。"""
    # app_configがロードされていることを前提とする
    security_config = app_config.get('security', {})
    salt = security_config.get('GUEST_ID_SALT')
    if not salt:
        logging.error("security.GUEST_ID_SALT が設定されていません。ゲストIDを生成できません。")
        return "error"

    import hashlib
    # IPとソルトを結合してハッシュ化
    hash_input = f"{ip_address}-{salt}".encode('utf-8')
    full_hash = hashlib.sha256(hash_input).hexdigest()

    # ハッシュの先頭7文字を使用
    return full_hash[:7]


def get_display_name(login_id: str, ip_address: str) -> str:
    """ユーザーの表示名を取得します。GUESTの場合は動的なIDを生成します。"""
    if login_id.upper() == 'GUEST':
        guest_hash = generate_guest_hash(ip_address)
        return f"GUEST({guest_hash})"
    return login_id


def get_client_ip():
    """リクエストからクライアントのIPアドレスを取得します（リバースプロキシ対応）。"""
    # SocketIOの接続イベントの場合、environから直接取得する
    # このコンテキストでは、request.environ['engineio.socket'] に接続情報が格納されている
    if request and hasattr(request, 'environ') and 'engineio.socket' in request.environ:
        eio_environ = request.environ.get('engineio.socket').environ
        # Nginxなどのリバースプロキシは 'HTTP_X_FORWARDED_FOR' を設定する
        ip_list = eio_environ.get('HTTP_X_FORWARDED_FOR')
        if ip_list:
            # 'client, proxy1, proxy2' のようにカンマ区切りで渡されることがあるため、最初のIPを取得
            return ip_list.split(',')[0].strip()
        # フォールバックとしてREMOTE_ADDRを使用
        return eio_environ.get('REMOTE_ADDR') or 'N/A'

    # 通常のHTTPリクエストの場合
    # ProxyFixが有効なら request.remote_addr が正しいIPを指すが、ヘッダーを直接見る方が確実
    ip_list = request.headers.get('X-Forwarded-For')
    if ip_list:
        return ip_list.split(',')[0].strip()
    return request.remote_addr or 'N/A'
