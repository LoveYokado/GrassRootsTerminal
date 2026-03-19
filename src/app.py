# SPDX-FileCopyrightText: 2025-2026 mid.yuki(LoveYokado)
# SPDX-License-Identifier: GPL-2.0-or-later

"""アプリケーションエントリポイント。

これは、Gunicornや開発サーバーから直接実行される際の、
アプリケーションのメインエントリポイントです。
`factory.create_app()` を呼び出して、設定済みのFlaskアプリケーションインスタンスを生成します。
"""

from .factory import create_app
from gevent import monkey
monkey.patch_all()


app, socketio = create_app()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
