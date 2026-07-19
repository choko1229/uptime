# Uptime Monitor

Proxmox VM・VPS・Webページ・Discord BOT・マイクラサーバーを対象にした自作の稼働監視システムです。公開ステータスページと管理画面を持ち、障害(インシデント)の手動掲載、Discord Webhook/メール通知、稼働率(30日/90日)表示に対応しています。

## 構成

- FastAPI + SQLAlchemy(async) + MySQL/MariaDB
- Jinja2によるサーバーサイドレンダリング + 最小限のJS
- APSchedulerによるモニターごとの定期チェック
- 監視対象タイプ: `proxmox_vm` / `vps` / `webpage` / `discord_bot` / `minecraft`(`app/checkers/` に実装。新タイプは `CHECKERS` 辞書に追加するだけで拡張可能)

## ローカルでの起動(Docker Compose)

```bash
cp .env.example .env
# .env の SECRET_KEY 等を編集

docker compose up --build
```

初回起動後、別ターミナルで管理者アカウントを作成します。

```bash
docker compose exec app python -m app.cli create-admin
```

- 公開ページ: http://localhost:8000/
- 管理画面: http://localhost:8000/admin/login

## Docker/DBなしでのローカル開発

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env  # MySQL/MariaDBを別途用意し接続情報を設定

alembic upgrade head
python -m app.cli create-admin
uvicorn app.main:app --reload
```

## テスト

MySQLを用意しなくても、pytestはインメモリSQLiteに差し替えて実行されます。

```bash
pip install -r requirements-dev.txt
pytest
```

## 監視対象タイプごとの設定

| タイプ | 必須設定項目 | 備考 |
|---|---|---|
| `proxmox_vm` | host, node, vmid, resource_type(qemu/lxc), token_id, token_secret | Proxmoxで「APIトークン」を発行し、対象VM/LXCへの参照権限(`VM.Audit`等)を付与してください |
| `vps` | host, port | ping と 指定ポートへのTCP接続のどちらかが成功すれば稼働中と判定 |
| `webpage` | url | HTTPステータスコードで判定。加えて `PAGESPEED_API_KEY` を設定すると毎日3:00(サーバー時刻)にPageSpeed Insightsスコアを取得 |
| `discord_bot` | guild_id, bot_username | 対象Discordサーバーの「サーバー設定 > ウィジェット」を有効化する必要があります(Widget JSON APIでオンライン状態を取得する方式のため) |
| `minecraft` | address (host:port), edition (java/bedrock) | Server List Pingプロトコルで人数・MOTD・バージョンを取得 |

## 通知

管理画面の「通知設定」からDiscord WebhookまたはメールをNotification Channelとして登録し、モニターごとにON/OFFを紐付けます。各モニターの「連続失敗しきい値」に達した時点で1回だけ障害通知を送信し、復旧時にも1回だけ通知します(連続失敗中の再通知はしません)。

## 環境変数

`.env.example` を参照してください。`pydantic-settings` により大文字小文字を区別せず読み込まれます(例: `DATABASE_HOST` → `settings.database_host`)。

## Pterodactyl Panelへのデプロイ

1. Pterodactyl管理画面で **Database Host** を登録済みであることを確認(未登録の場合は Admin > Databases から追加)。
2. `pterodactyl/egg-uptime-monitor.json` を Admin > Nests > Import Egg でインポート。
3. 新規サーバー作成時にこのEggを選択し、以下の変数を設定:
   - `GIT_REPOSITORY_URL` / `GIT_BRANCH`: このリポジトリのURLとブランチ
   - `DATABASE_HOST` / `DATABASE_PORT` / `DATABASE_NAME` / `DATABASE_USER` / `DATABASE_PASSWORD`: サーバー作成時にPanelが払い出すDatabase情報
   - `SECRET_KEY`: ランダムな長い文字列
   - 必要に応じて `PAGESPEED_API_KEY` / `SMTP_*` / `SITE_TITLE`
4. サーバーを起動するとインストールスクリプトがリポジトリをcloneし、起動コマンドが `alembic upgrade head` の後にアプリを起動します。
5. 初回のみコンソールから管理者を作成します(Pterodactylのコンソール上で):
   ```
   python -m app.cli create-admin
   ```
6. 公開ステータスページを独自ドメインで公開する場合は、Pterodactylが割り当てたポートへ逆プロキシ(nginx等)を設定し、SSL証明書を発行してください。

> egg定義はテンプレートです。実際のPterodactylバージョン/ノード構成によって `docker_images` や起動スクリプトの調整が必要になる場合があります。

## 既知の制約・今後の拡張候補

- VPSの負荷(CPU/メモリ)取得は今回スコープ外(エージェント未導入のため稼働監視のみ)
- Discord BOT監視はサーバーウィジェット経由のため、ウィジェット非対応/無効なサーバーでは利用不可
- 通知のしきい値は現状「連続失敗N回で1回通知・復旧で1回通知」のシンプルなロジック(将来的にモニターごとの再通知間隔などを追加可能)
