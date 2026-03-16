# ISBN Library

ISBN の重複購入防止を目的にした個人用書籍管理アプリです。スマホブラウザで ISBN バーコードを読み取り、登録済みかどうかを即座に判定し、未登録なら Google Books API から取得した書誌情報で登録できます。

## 構成

- `frontend/`: React + Vite + TypeScript の SPA
- `backend/lambda/`: API Gateway から呼ばれる Lambda 群
- `infrastructure/`: AWS CDK (Python) による IaC
- `docs/`: セットアップ手順と運用メモ

## アーキテクチャ

- Hosting: AWS Amplify Hosting
- Auth: Amazon Cognito User Pool + Hosted UI / managed login
- API: API Gateway HTTP API + JWT Authorizer
- Backend: AWS Lambda (Python 3.12)
- DB: DynamoDB on-demand
- Lookup: Google Books API

## ローカル起動

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

### Infrastructure

```bash
cd infrastructure
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cdk synth
cdk deploy
```

## 初期ユーザー作成

自己サインアップは無効です。初期ユーザーは Cognito コンソールから手動で作成します。

1. 対象 User Pool を開く
2. `Users` から `Create user`
3. Email と仮パスワードを設定
4. 初回ログイン後にパスワード変更

## CI/CD

GitHub Actions で `main` への push 時に `frontend build -> CDK deploy -> Amplify 再デプロイ` を実行できます。詳細は [docs/github-actions.md](/d:/Git/isbn-library/docs/github-actions.md) を参照してください。

## Cognito 設定メモ

フロントエンドの `VITE_COGNITO_AUTHORITY` には Hosted UI ドメインではなく、User Pool の issuer URL を設定します。

- 正しい例: `https://cognito-idp.ap-northeast-1.amazonaws.com/ap-northeast-1_xxxxxxxx`
- 誤った例: `https://isbn-library-dev.auth.ap-northeast-1.amazoncognito.com`

一方でログアウト用には Hosted UI ドメインも必要です。

- `VITE_COGNITO_HOSTED_UI_DOMAIN`
- 例: `https://isbn-library-dev.auth.ap-northeast-1.amazoncognito.com`

## Amplify Hosting メモ

Amplify Hosting の Basic 認証はアプリ外設定です。本リポジトリでは実装していません。必要であれば Amplify Hosting 側のアクセス制御設定で保護してください。

## API

- `GET /books`
- `GET /books/{isbn}`
- `POST /books`
- `DELETE /books/{isbn}`
- `GET /lookup/{isbn}`

詳しいセットアップは [docs/setup.md](/d:/Git/isbn-library/docs/setup.md) を参照してください。
