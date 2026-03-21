# GitHub Actions CI/CD

## 概要

このリポジトリには `main` ブランチへの push をトリガーに、以下を自動実行するワークフローを追加しています。

1. `frontend` の依存関係インストール
2. Lambda テスト + カバレッジ計測
3. `frontend build`
4. `infrastructure` の `cdk deploy`
5. Amplify Hosting の再デプロイ開始

ワークフロー定義は [deploy.yml](/d:/Git/isbn-library/.github/workflows/deploy.yml) です。

Lambda テスト専用のワークフローは [backend-tests.yml](/d:/Git/isbn-library/.github/workflows/backend-tests.yml) です。`push` / `pull_request` / 手動実行でカバレッジ付きテストを実行します。

## 前提

- GitHub リポジトリが存在する

- `AWS_DEPLOY_ROLE_ARN`
- `GOOGLE_BOOKS_API_KEY` (optional)

`GOOGLE_BOOKS_API_KEY` is passed only to the `cdk deploy` step via GitHub Secrets and is not echoed in the workflow logs. If it is not set, the lookup Lambda continues calling Google Books API without an API key.
- Amplify Hosting に対象アプリが作成済み
- CDK の初回 `bootstrap` が済んでいる
- GitHub Actions から AWS にアクセスできる IAM Role を用意する

## 推奨認証方式

GitHub Secrets に長期アクセスキーを置かず、GitHub OIDC で AWS IAM Role を引き受ける構成を推奨します。

## IAM Role テンプレート

`AWS_DEPLOY_ROLE_ARN` に設定する IAM Role には、少なくとも GitHub OIDC からの引き受け設定と、CDK デプロイに必要な権限が必要です。

### 1. 信頼ポリシー例

`YOUR_GITHUB_ORG` と `YOUR_REPOSITORY` は実際の GitHub リポジトリに置き換えてください。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/YOUR_REPOSITORY:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

この形なら `main` ブランチからの実行だけを許可できます。`token.actions.githubusercontent.com:sub` にワイルドカードを使わないので、IAM の警告にも沿っています。

`main` 以外も許可したい場合は、ブランチごとに明示的に列挙してください。例えば `release` ブランチも許可したいなら、`StringLike` に戻して次のように `*` なしで並べます。

```json
{
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
  },
  "StringLike": {
    "token.actions.githubusercontent.com:sub": [
      "repo:YOUR_GITHUB_ORG/YOUR_REPOSITORY:ref:refs/heads/main",
      "repo:YOUR_GITHUB_ORG/YOUR_REPOSITORY:ref:refs/heads/release"
    ]
  }
}
```

タグや Environment まで許可する場合も、同様に個別指定を推奨します。

### 2. 権限ポリシー例

最初は広めですが、CDK でこのアプリをデプロイするための実用的な雛形です。運用時は対象リソース ARN に絞ることを推奨します。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudFormationAccess",
      "Effect": "Allow",
      "Action": [
        "cloudformation:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CdkBootstrapAndArtifactAccess",
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "ecr:*",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IamForCdkManagedResources",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:TagRole",
        "iam:UntagRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassRoleOnlyToLambdaAndCloudFormation",
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": [
            "lambda.amazonaws.com",
            "cloudformation.amazonaws.com"
          ]
        }
      }
    },
    {
      "Sid": "LambdaAccess",
      "Effect": "Allow",
      "Action": [
        "lambda:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ApiGatewayAccess",
      "Effect": "Allow",
      "Action": [
        "apigateway:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DynamoDbAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CognitoAccess",
      "Effect": "Allow",
      "Action": [
        "cognito-idp:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AmplifyStartJob",
      "Effect": "Allow",
      "Action": [
        "amplify:StartJob",
        "amplify:GetJob",
        "amplify:ListJobs"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. 最低限の絞り込みポイント

- `amplify:*` は対象アプリ ARN のみに絞る
- `dynamodb:*` は `books` テーブル ARN のみに絞る
- `cognito-idp:*` は対象 User Pool ARN のみに絞る
- `lambda:*` はこのスタックが作成する関数名 prefix に絞る
- `cloudformation:*` は対象スタック名に絞る
- `iam:PassRole` は対象 Role ARN のみに絞るか、少なくとも `iam:PassedToService` を付ける

### 4. `iam:PassRole` をさらに安全にする例

より安全にするなら、`Resource: "*"` を避けて CDK が作成する実行ロールの ARN prefix に寄せてください。例えば次のような形です。

```json
{
  "Sid": "PassRoleForProjectRolesOnly",
  "Effect": "Allow",
  "Action": [
    "iam:PassRole"
  ],
  "Resource": [
    "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/IsbnLibraryStack-*",
    "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/cdk-*"
  ],
  "Condition": {
    "StringEquals": {
      "iam:PassedToService": [
        "lambda.amazonaws.com",
        "cloudformation.amazonaws.com"
      ]
    }
  }
}
```

CDK が実際に作るロール名を一度デプロイ後に確認し、その prefix に合わせて `Resource` を絞るのが実運用ではおすすめです。

## GitHub OIDC Provider

まだ AWS 側に OIDC Provider がない場合は、`token.actions.githubusercontent.com` を issuer として IAM Identity Provider を作成してください。

代表値:

- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

## GitHub Secrets

- `AWS_DEPLOY_ROLE_ARN`

## GitHub Variables

- `AWS_ACCOUNT_ID`
- `AWS_REGION`
- `COGNITO_DOMAIN_PREFIX`
- `COGNITO_CALLBACK_URLS`
- `COGNITO_LOGOUT_URLS`
- `CORS_ALLOW_ORIGINS`
- `BOOKS_TABLE_NAME`
- `CATEGORIES_TABLE_NAME`
- `VITE_API_BASE_URL`
- `VITE_COGNITO_AUTHORITY`
- `VITE_COGNITO_HOSTED_UI_DOMAIN`
- `VITE_COGNITO_CLIENT_ID`
- `VITE_COGNITO_REDIRECT_URI`
- `VITE_COGNITO_LOGOUT_REDIRECT_URI`
- `VITE_COGNITO_SCOPE`
- `AMPLIFY_APP_ID`
- `AMPLIFY_BRANCH_NAME`
- `GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_BOOKS_SHEET_NAME`
- `GOOGLE_SHEETS_CATEGORIES_SHEET_NAME`
- `BOOKS_EXPORT_SCHEDULE_EXPRESSION`
- `BOOKS_EXPORT_SCHEDULE_TIMEZONE`

## 補足

- `frontend-build` は設定値の妥当性確認も兼ねています
- Amplify へのデプロイは GitHub Actions から `start-job` を呼び、Amplify 側のビルドを開始します
- Amplify アプリ未作成時は `AMPLIFY_APP_ID` と `AMPLIFY_BRANCH_NAME` を未設定にすれば、Amplify ジョブはスキップされます
- `VITE_COGNITO_AUTHORITY` には Hosted UI ドメインではなく `JwtIssuer` を設定します
