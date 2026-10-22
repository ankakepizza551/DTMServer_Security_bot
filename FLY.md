# Fly.io への移行手順

Railway から Fly.io に移すための手順。設定は `fly.toml`、ビルドは `Dockerfile`、
自動デプロイは `.github/workflows/fly-deploy.yml`。

- アプリ名: `dtmserver-security-bot`（Fly.io 全体で一意。使われていたら `fly.toml` の `app` を変える）
- リージョン: `nrt`（東京）
- 状態ファイル: ボリューム `dtm_security_data` の `/data/pending.json`（デプロイしても消えない）
- Web サービスなしの常駐プロセス。落ちたら自動で再起動する（`[[restart]] policy = 'always'`）

> **同じトークンで Railway と Fly.io を同時に動かさないこと。**
> 2 つの bot が同じイベントに反応して、二重に BAN・キック・メッセージ送信をしてしまう。
> 切り替えの間はサーバーへの参加を止めておく。

## 1. 準備（初回だけ）

```bash
# flyctl を入れてログイン（https://fly.io/docs/flyctl/install/）
fly auth login

# アプリとボリュームを作る
fly apps create dtmserver-security-bot
fly volumes create dtm_security_data --app dtmserver-security-bot --region nrt --size 1 --yes
```

## 2. 環境変数（シークレット）を登録する

Railway のサービスの Variables に入っている値を、そのまま Fly.io に登録する。
`DISCORD_TOKEN` は更新後の新しいトークンを使う。`DB_PATH` は `fly.toml` で設定済みなので登録しない。

```bash
fly secrets set --app dtmserver-security-bot --stage DISCORD_TOKEN='新しいトークン'
# Railway で設定していたものがあれば同じように追加する（例）
# fly secrets set --app dtmserver-security-bot --stage PENDING_ROLE_NAME='認証待ち' MEMBER_ROLE_NAME='DTMメンバー' KICK_ON_REJECT='true'
```

`--stage` を付けると、次のデプロイまで反映を待つ（まだマシンがないので付けておく）。

## 3. Railway を止めてから、Fly.io にデプロイする

1. Railway でこのサービスを停止する（Railway のボリュームにデータを入れていた場合は、先に 5. を読む）
2. Fly.io にデプロイする

```bash
fly deploy --app dtmserver-security-bot
fly status --app dtmserver-security-bot     # マシンが 1 台だけ started になっていること
fly logs --app dtmserver-security-bot       # 「Cog読み込み」とログイン成功のログが出ること
```

マシンが 2 台以上あったら 1 台にする（bot は 1 プロセスだけで動かす）:

```bash
fly scale count 1 --app dtmserver-security-bot
```

Discord で bot がオンラインになったことを確かめてから、サーバーへの参加を再開する。

## 4. GitHub からの自動デプロイを有効にする

```bash
fly tokens create deploy --app dtmserver-security-bot --expiry 8760h
```

表示されたトークンを、GitHub のリポジトリの Settings → Secrets and variables → Actions に
`FLY_API_TOKEN` という名前で登録する。以後は main にマージするたびに、チェックが通れば自動でデプロイされる。
（登録するまでは、ワークフローはチェックだけしてデプロイを飛ばす。）

トークンの期限は 1 年（8760h）。切れたら作り直して登録し直す。

## 5. Railway からデータを移す（Railway でボリュームを使っていた場合だけ）

Railway でボリュームを付けていなかった場合、Railway 側のデータはデプロイのたびに消えていたので、移すものはない。

付けていた場合は、Railway を止める前に `pending.json` を手元に保存しておき、Fly.io にデプロイしたあとで置き換える:

```bash
fly ssh sftp shell --app dtmserver-security-bot
» put ./pending.json /data/pending.json
» exit
fly apps restart dtmserver-security-bot   # 読み込み直す
```

## 6. 片付け

Fly.io で数日問題なく動いたら、Railway のサービスを削除する。`Procfile` は Railway 用なので、そのあと消してよい。

## 困ったとき

```bash
fly logs --app dtmserver-security-bot                  # ログを見る
fly ssh console --app dtmserver-security-bot           # マシンに入る（ls /data で状態ファイルを確認）
fly apps restart dtmserver-security-bot                 # 再起動
```
