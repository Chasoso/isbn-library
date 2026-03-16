# Setup Guide

## 1. 前提

- Node.js 20 以上
- npm
- Python 3.12
- AWS CDK CLI
- AWS 認証情報設定済み

## 2. フロントエンド環境変数

`frontend/.env` を `frontend/.env.example` から作成し、以下を設定します。

- `VITE_API_BASE_URL`
- `VITE_COGNITO_AUTHORITY`
- `VITE_COGNITO_CLIENT_ID`
- `VITE_COGNITO_REDIRECT_URI`
- `VITE_COGNITO_LOGOUT_REDIRECT_URI`
- `VITE_COGNITO_SCOPE`

ローカルでは通常以下の URL を使います。

- Redirect URI: `http://localhost:5173/auth/callback`
- Logout URI: `http://localhost:5173`

## 3. CDK デプロイ用環境変数

PowerShell 例:

```powershell
$env:COGNITO_DOMAIN_PREFIX = "isbn-library-yourname"
$env:COGNITO_CALLBACK_URLS = "http://localhost:5173/auth/callback,https://main.xxxxxx.amplifyapp.com/auth/callback"
$env:COGNITO_LOGOUT_URLS = "http://localhost:5173,https://main.xxxxxx.amplifyapp.com"
$env:CORS_ALLOW_ORIGINS = "http://localhost:5173,https://main.xxxxxx.amplifyapp.com"
```

## 4. インフラデプロイ

```powershell
cd infrastructure
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

CloudFormation Outputs から以下を控えます。

- `UserPoolId`
- `UserPoolClientId`
- `CognitoDomain`
- `ApiUrl`
- `JwtIssuer`
- `BooksTableName`

## 5. Cognito 初期ユーザー作成

1. AWS Console で User Pool を開く
2. `Users` > `Create user`
3. Email と仮パスワードを設定
4. 対象ユーザーで Hosted UI からログイン
5. 初回サインイン時にパスワード変更

自己サインアップは無効です。

## 6. Frontend 起動

```powershell
cd frontend
npm install
npm run dev
```

## 7. Amplify Hosting

1. `frontend/` をビルド対象として Amplify Hosting に接続
2. SPA リライトを `/index.html` に設定
3. ビルド環境変数に `VITE_*` を設定
4. 必要に応じて Amplify Hosting 側で Basic 認証を有効化

Basic 認証自体はこのアプリの実装範囲外です。

## 8. GitHub Actions による自動デプロイ

GitHub Actions で `main` への push 時に `frontend build -> CDK deploy -> Amplify 再デプロイ` を自動化できます。

設定手順:

1. AWS 側で GitHub OIDC 用の IAM Role を作成
2. GitHub Secrets に `AWS_DEPLOY_ROLE_ARN` を登録
3. GitHub Variables に AWS / Cognito / Vite / Amplify の値を登録
4. 事前に `cdk bootstrap` を 1 回実行
5. `main` に push

詳しい項目一覧は [docs/github-actions.md](/d:/Git/isbn-library/docs/github-actions.md) を参照してください。
