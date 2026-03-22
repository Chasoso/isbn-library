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

必要ならテーブル名は環境変数で上書きできます。

- `BOOKS_TABLE_NAME` 例: `books`
- `CATEGORIES_TABLE_NAME` 例: `book-category`

Google Books API キーを使う場合だけ、`cdk deploy` 前に `GOOGLE_BOOKS_API_KEY` を環境変数へ設定してください。未設定ならキーなしで Google Books API を呼び出します。

## 初期ユーザー作成

自己サインアップは無効です。初期ユーザーは Cognito コンソールから手動で作成します。

1. 対象 User Pool を開く
2. `Users` から `Create user`
3. Email と仮パスワードを設定
4. 初回ログイン後にパスワード変更

## CI/CD

GitHub Actions で `main` への push 時に `frontend build -> CDK deploy -> Amplify 再デプロイ` を実行できます。詳細は [docs/github-actions.md](/d:/Git/isbn-library/docs/github-actions.md) を参照してください。

## Lambda テスト

Lambda は `pytest` で自動テストできます。

```bash
cd backend
pip install -r requirements-test.txt
pytest
```

カバレッジは `coverage.xml` とターミナル出力で確認できます。GitHub Actions でも自動実行されます。

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
- `GET /categories`
- `POST /categories`
- `PATCH /categories/{categoryId}`

## Categories

カテゴリは静的配列ではなく `categories` テーブルで管理します。書籍データはカテゴリ名ではなく
`categoryId` を保存し、API 応答では表示用の `categoryName` も返します。

- `POST /books` の登録 payload は `category` ではなく `categoryId`
- `GET /books` の絞り込み query は `category` ではなく `categoryId`
- フロントから `/categories` でカテゴリ追加・名称変更が可能

## 分類

登録時に次の 2 種類の分類を付与できます。

- `bookFormat`: 新書、文庫、単行本、ハードカバー、雑誌、電子書籍、その他
- `category`: 技術書、小説、ビジネス、デザイン、歴史、統計、趣味、漫画、その他

重複判定は引き続き `userId + isbn` のみで行い、分類情報は使用しません。蔵書一覧では分類条件でフィルタできます。

詳しいセットアップは [docs/setup.md](/d:/Git/isbn-library/docs/setup.md) を参照してください。

## Frontend Visual Tests

フロントエンドは Playwright で画面確認できます。E2E 用のデモモードでホーム画面と蔵書一覧を開き、毎回スクリーンショットを保存します。

```bash
cd frontend
npm install
npx playwright install chromium
npm run test:e2e
```

## Google Sheets Daily Export

The stack can export `books` and `categories` to Google Sheets once per day.

- Lambda: `backend/lambda/export_books_to_sheets/`
- WIF config storage: AWS Systems Manager Parameter Store
- Scheduler: EventBridge Scheduler

Required deployment variables:

- `GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_BOOKS_SHEET_NAME` default: `books`
- `GOOGLE_SHEETS_CATEGORIES_SHEET_NAME` default: `categories`
- `GOOGLE_SHEETS_CATEGORY_VORONOI_SHEET_NAME` default: `category_voronoi`
- `BOOKS_EXPORT_SCHEDULE_EXPRESSION` default: `cron(0 3 * * ? *)`
- `BOOKS_EXPORT_SCHEDULE_TIMEZONE` default: `Asia/Tokyo`

The Parameter Store value must be the Google Workload Identity Federation credential configuration JSON. The batch clears and rewrites the `books`, `categories`, and `category_voronoi` sheets on every run.

See also: [docs/google-sheets-export.md](/d:/Git/isbn-library/docs/google-sheets-export.md)

スクリーンショットは `frontend/test-results/`、HTML レポートは `frontend/playwright-report/` に出力されます。GitHub Actions でも同じスクリーンショットを毎回 artifact として保存します。
