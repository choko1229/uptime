# Uptime Monitor

Proxmox VM・VPS・Webページ・Discord BOT・マイクラサーバーを対象にした自作の稼働監視システムです。公開ステータスページと管理画面を持ち、障害(インシデント)の手動掲載、Discord Webhook/メール通知、稼働率(30日/90日)表示に対応しています。

## 構成

- FastAPI + SQLAlchemy(async) + MySQL/MariaDB
- Jinja2によるサーバーサイドレンダリング + 最小限のJS
- APSchedulerによるモニターごとの定期チェック
- 監視対象タイプ: `proxmox_vm` / `vps` / `webpage` / `discord_bot` / `minecraft`(`app/checkers/` に実装。新タイプは `CHECKERS` 辞書に追加するだけで拡張可能)

## 初回セットアップの考え方

`.env` に書くのは `PORT` だけです。それ以外はすべてアプリ自身の中で設定します。

1. 初回起動時、DBが未設定の場合はどのページにアクセスしても `/setup` にリダイレクトされます。
2. `/setup` でMySQL/MariaDBの接続情報(ホスト/ポート/DB名/ユーザー/パスワード)を入力すると、接続確認→テーブル作成(Alembicマイグレーション)まで自動で行われます。
3. ユーザーがまだ1人もいなければ、管理者アカウント `admin` とランダムなパスワードが自動生成され、**起動ログ(コンソール)にのみ**表示されます。ログイン後は「アプリ設定」ページからパスワードを変更してください。
4. DB接続情報とセッション署名用のSECRET_KEYは `data/` ディレクトリ(gitignore済み)にファイルとして保存され、次回起動時から自動的に読み込まれます。Docker/Pterodactylではこのディレクトリがコンテナ再作成後も残るようにしてください(後述)。
5. SMTP・PageSpeed APIキー・サイトタイトルはログイン後「アプリ設定」(`/admin/settings`)からいつでも変更できます。

## ローカルでの起動(Docker Compose)

```bash
cp .env.example .env  # 通常はPORTのみでOK

docker compose up --build
```

- ブラウザで http://localhost:8000/setup を開き、DB接続情報を入力してください。
  - Docker Compose内では `db` サービス(MariaDB)が使えます。ホストは `db`、DB名/ユーザー/パスワードはいずれも `uptime`(`docker-compose.yml` 参照)。
- セットアップ完了後、`docker compose logs app` で管理者パスワードを確認できます。
- 公開ページ: http://localhost:8000/
- 管理画面: http://localhost:8000/admin/login

## Docker/DBなしでのローカル開発

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env
python -m app.main  # または: uvicorn app.main:app --reload
```

起動後 http://localhost:8000/setup で用意済みのMySQL/MariaDBの接続情報を入力してください。

管理者パスワードを忘れた・作り直したい場合は以下でも変更できます。

```bash
python -m app.cli create-admin
```

## テスト

MySQLを用意しなくても、pytestはインメモリSQLiteに差し替えて実行されます(`/setup`のDB接続確認〜マイグレーション〜管理者自動作成までのエンドツーエンドテストも含む)。

```bash
pip install -r requirements-dev.txt
pytest
```

## 監視対象タイプごとの設定

| タイプ | 必須設定項目 | 備考 |
|---|---|---|
| `proxmox_vm` | host, node, vmid, resource_type(qemu/lxc), token_id, token_secret | Proxmoxで「APIトークン」を発行し、対象VM/LXCへの参照権限(`VM.Audit`等)を付与してください |
| `vps` | host, port | ping と 指定ポートへのTCP接続のどちらかが成功すれば稼働中と判定 |
| `webpage` | url | HTTPステータスコードで判定。加えて「アプリ設定」でPageSpeed APIキーを設定すると毎日3:00(サーバー時刻)にPageSpeed Insightsスコアを取得 |
| `discord_bot` | guild_id, bot_username | 対象Discordサーバーの「サーバー設定 > ウィジェット」を有効化する必要があります(Widget JSON APIでオンライン状態を取得する方式のため) |
| `minecraft` | address (host:port), edition (java/bedrock) | Server List Pingプロトコルで人数・MOTD・バージョンを取得 |

## 通知

管理画面の「通知設定」からDiscord WebhookまたはメールをNotification Channelとして登録し、モニターごとにON/OFFを紐付けます。メール送信にはあらかじめ「アプリ設定」でSMTP情報を登録しておく必要があります。各モニターの「連続失敗しきい値」に達した時点で1回だけ障害通知を送信し、復旧時にも1回だけ通知します(連続失敗中の再通知はしません)。

## 環境変数

`.env.example` を参照してください。`PORT` 以外の設定項目は環境変数ではなく、`/setup`(DB接続)と `/admin/settings`(SMTP・PageSpeed・サイトタイトル)というアプリ内の画面から行います。

## Pterodactyl Panelへのデプロイ

1. `pterodactyl/egg-uptime-monitor.json` を Admin > Nests > Import Egg でインポート。
2. 新規サーバー作成時にこのEggを選択し、`GIT_REPOSITORY_URL` / `GIT_BRANCH` のみ設定(DB接続情報やSECRET_KEYなどのEgg変数は不要です)。
3. サーバーを起動するとインストールスクリプトがリポジトリをcloneし、起動コマンドがアプリを起動します。
4. Panelの「Console」からアクセスできるアドレス(または割り当て済みのallocation)で `/setup` を開き、Pterodactylで用意したMySQL/MariaDB(Database Hostから作成したデータベース)の接続情報を入力してください。
5. セットアップが完了すると管理者アカウントが自動生成され、ユーザー名・パスワードがコンソールのログに表示されます。
6. サーバーのファイル(`data/` ディレクトリを含む)はPterodactylのサーバーストレージ上で永続化されるため、コンテナの再起動・再作成後もDB接続情報やSECRET_KEYは失われません。
7. 公開ステータスページを独自ドメインで公開する場合は、Pterodactylが割り当てたポートへ逆プロキシ(nginx等)を設定し、SSL証明書を発行してください。

> egg定義はテンプレートです。実際のPterodactylバージョン/ノード構成によって `docker_images` や起動スクリプトの調整が必要になる場合があります。

## 既知の制約・今後の拡張候補

- VPSの負荷(CPU/メモリ)取得は今回スコープ外(エージェント未導入のため稼働監視のみ)
- Discord BOT監視はサーバーウィジェット経由のため、ウィジェット非対応/無効なサーバーでは利用不可
- 通知のしきい値は現状「連続失敗N回で1回通知・復旧で1回通知」のシンプルなロジック(将来的にモニターごとの再通知間隔などを追加可能)
- `/setup` は「DBに管理者ユーザーが1人もいない場合のみ」管理者を自動生成します。DB接続情報を変更したい場合は `data/database.json` を編集・削除してから再度 `/setup` にアクセスしてください
