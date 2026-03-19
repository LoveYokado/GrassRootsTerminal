# GrassRootsTerminal

GrassRootsTerminal は、1990 年代のパソコン通信(BBS)の懐かしい体験を現代の技術で再現する、Web ベースのターミナル風掲示板システムであるGrassRootsBBSのターミナル部分だけを切り出したゲートウェイです。

## プロジェクトの背景

あの当時、様々なwwivやBig-Model、RTBBS、mmmなどのホストプログラムが群雄割拠していました。
私はBig-Modelのサイトを中心にいくつかのBBSに接続していましたが、それぞれのBBSにはそれぞれの個性があり、運営するシスオペは幾つかの選択肢から自分に合ったホストプログラムを選択していました。
しかし、現代では生き残っているホストプログラムはほとんどなく、WebUIで動作するBBSも非常に少ない状況です。
そこで、現存するホストプログラムで多用されているTelnetプロトコルを採用することで、当時のBBSの体験をできるだけ再現し、現代のユーザーに提供することを目指してGrassRootsBBSからターミナル部分のみを切り離したものがGrassRootsTerminalです。

## 開発を支援する ☕

GrassRootsTerminalは、GrassRootsBBSをもとにフォークされているようなものです。もしこのソフトウェアを気に入っていただけたら、GrassRootsBBSの開発への応援のためにコーヒーを1杯奢っていただけると嬉しいです!
皆さまからの温かいサポートが活力となり、継続的な開発とメンテナンスの原動力になります。

[![Support me on Ko-fi](https://img.shields.io/badge/Support%20me%20on%20Ko--fi-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/loveyokado)
[Support me on Ko-fi](https://ko-fi.com/loveyokado)

## 主な機能

- **レトロ&モダンな Web ターミナル UI**:
  - ユーザーが自由に選べるテーマ（グリーンモニタ風・アンバーモニタ風など）とフォント。
  - 日本語と英語が選べますが、それ以外の言語への対応も可能な設計。
  - 遊び心のある DIP スイッチ風設定画面。
  - PWA 対応によるスマートフォンへのインストール。
- **シンプルなTelnetゲートウェイ**:
  - Docker Compose で簡単にセットアップ可能。
  - 設定ファイルでポートを指定するだけで動作します。

## Installation & Setup / インストールとセットアップ

**必要なもの:** Docker, Docker Compose

### 1. リポジトリのクローン

```bash
git clone https://github.com/LoveYokado/grassrootsterminal.git
cd GrassRootsTerminal
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` ファイルを作成し、内容を編集します。

```bash
cp .env.example .env
```

大半はデフォルトで問題はないと思います。

### 3. 設定ファイルの編集

config.toml.example をコピーして config.toml を作成します。

```bash
cp setting/config.toml.example setting/config.toml
```

`setting/config.toml`を編集して、あなたの環境に合わせた設定を行います。
[telnet]
host = "sbbs" # Docker Compose環境では、ホスト名をサービス名にしてください (例: "sbbs")。
port = 23 # BBSのTelnetポート
timeout = 300 # ターミナルセッションのタイムアウト時間（秒）
[webapp]
ORIGIN = "http://localhost:5000" # ターミナルにアクセスする際の完全な URL (プロトコル、ホスト、ポートを含む)

### 4. PWA マニフェストの設定

PWA（プログレッシブ・ウェブアプリ）としてスマートフォンなどにインストールする際のアプリ名やアイコンを設定します。
`manifest.json.example`をコピーして manifest.json を作成し、必要に応じて内容を編集してください。

```bash
cp static/manifest.json.example static/manifest.json
```

特に、BBS の名前を変更したい場合は manifest.json 内の name と short_name を変更します。

### 5. サーバの設定と起動

`docker-compose.yml.example` を `docker-compose.yml` としてコピーします。

```bash
cp docker-compose.yml.example docker-compose.yml
```

サンプルとしてSynchronet BBSのホストプログラムである Synchronet がコメントアウトされてますので、必要に応じてコメントアウトを外して、ホストプログラムのサービスを有効にしてください。
他のホストプログラムでも、Telnetで接続できるものであれば、同様のサービス定義を追加することで対応可能です。

設定が完了したら、Docker Compose を使って起動します。

```bash
docker-compose up -d
```

### 6. BBS へのアクセス

Web ブラウザで `http://localhost:5000` にアクセスしてください。

### 7. （推奨）本番環境向け: Nginx によるリバースプロキシ設定

実際にインターネットに公開する際は、セキュリティとパフォーマンス向上のため、Nginx をリバースプロキシとして Terminal アプリケーションの前に配置することを強く推奨します。これにより、HTTPS(SSL/TLS)化も容易になります。

#### a. Nginx 設定ファイルの準備

`nginx.config.example` をコピーして、Nginx 用の設定ファイルを作成します。

```bash
cp nginx.config.example nginx.conf
```

次に、`nginx.conf` を開き、あなたの環境に合わせて編集してください。

- **`server_name`**: `example.com` をあなたのドメイン名に書き換えます。
- **SSL 証明書のパス**: Let's Encrypt などで取得した SSL 証明書と秘密鍵への正しいパスを指定します。Let's Encrypt を使用する場合、証明書は通常 `/etc/letsencrypt/live/your_domain/` 以下に配置されます。

#### b. SSL 証明書の取得 (Let's Encrypt を使用する場合)

無料で SSL 証明書を発行できる Let's Encrypt と、そのクライアントである Certbot を使用するのが一般的です。

Certbot をホストマシンにインストールした後、以下のコマンド例のように実行して証明書を取得します。（Web サーバーを一時的に停止する必要がある場合があります）

```bash
# 'your_domain' とメールアドレスを置き換えてください
sudo certbot certonly --standalone -d your_domain --email your_email@example.com
```

証明書が取得できたら、`nginx.conf` の `ssl_certificate` と `ssl_certificate_key` のパスが正しいか確認してください。

## License

This project is licensed under the **GNU General Public License v2.0 (GPLv2)**.

- **Synchronet BBS Software:** Copyright (c) Rob Swindell. Licensed under GPL/LGPL.
- **Docker Configurations & Setup Scripts:** Copyright (c) 2026 LoveYokado. Licensed under GPLv2.
