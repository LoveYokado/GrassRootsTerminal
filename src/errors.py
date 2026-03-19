# SPDX-FileCopyrightText: 2025-2026 mid.yuki(LoveYokado)
# SPDX-License-Identifier: GPL-2.0-or-later

"""カスタムエラーハンドラ。

このモジュールは、404 (Not Found) や 500 (Internal Server Error) といった
一般的なHTTPエラーに対するカスタムエラーページを定義します。これにより、
デフォルトのエラーページよりもユーザーフレンドリーな体験を提供します。
"""

from flask import render_template, request
import logging


def register_error_handlers(app):
    """Flaskアプリケーションにカスタムエラーハンドラを登録します。"""

    @app.errorhandler(429)
    def ratelimit_handler(e):
        logging.warning(
            f"Rate limit exceeded for {request.remote_addr} on {request.path}. Limit: {e.description}")
        return render_template('errors/429.html', error=e), 429

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logging.error(f"500 Internal Server Error: {error}", exc_info=True)
        return render_template('errors/500.html'), 500
