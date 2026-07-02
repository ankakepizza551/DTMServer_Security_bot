# DTMServer Security BOT

新規参加者に「認証待ち」ロールを付与し、管理者が承認すると「DTMメンバー」ロールに入れ替えるDiscord Bot。

## 動作フロー

1. ユーザーがサーバーに参加すると、自動的に「認証待ち」ロールが付与される。
2. 設定した承認申請チャンネル（デフォルト: `認証申請`）に、ユーザー情報と「承認」「拒否」ボタン付きの通知が投稿される。
3. 管理者権限を持つメンバーがボタンを押す。
   - **承認**: 「認証待ち」ロールを外し、「DTMメンバー」ロールを付与する。
   - **拒否**: 設定によりサーバーからKickする（`KICK_ON_REJECT`）。
4. 対応結果がメッセージに反映され、ボタンは無効化される。
5. Bot再起動後も、未対応の申請ボタンは引き続き機能する（`data/pending.json` に保存）。

## セットアップ

### 1. Discord側の準備

- ロールを2つ作成する: `認証待ち` と `DTMメンバー`（名前は `.env` で変更可）
- 通知用テキストチャンネルを作成する: `認証申請`（名前は `.env` で変更可）
- Bot導入時に以下の権限を付与する:
  - ロールの管理 (Manage Roles)
  - メンバーをキック (Kick Members) ※拒否時にKickする場合
  - メッセージの送信 / 埋め込みリンク (Send Messages / Embed Links)
  - サーバーメンバー情報インテント (Server Members Intent) をDeveloper Portalで有効化
- **重要**: Botのロールを「認証待ち」「DTMメンバー」より上位に配置する（ロール階層の制約でBotは自分より下のロールしか操作できない）

### 2. 環境構築

```bash
pip install -r requirements.txt
cp .env.example .env
# .env を編集して DISCORD_TOKEN を設定
```

### 3. 起動

```bash
python main.py
```

## 診断コマンド

管理者権限を持つユーザーが `!verify_diag` を実行すると、ロール・チャンネルの設定状況とBotの権限、ロール階層をチェックできる。

## 設定項目 (.env)

| 変数 | 説明 | デフォルト |
|---|---|---|
| `DISCORD_TOKEN` | Botトークン (必須) | - |
| `PENDING_ROLE_NAME` | 認証待ちロール名 | 認証待ち |
| `MEMBER_ROLE_NAME` | 承認後に付与するロール名 | DTMメンバー |
| `REQUEST_CHANNEL_NAME` | 承認申請を投稿するチャンネル名 | 認証申請 |
| `KICK_ON_REJECT` | 拒否時にKickするか (true/false) | true |
| `APPROVED_DM_MESSAGE` | 承認時にDMするメッセージ (空で無効) | あり |
| `REJECTED_DM_MESSAGE` | 拒否時にDMするメッセージ (空で無効) | あり |
