# Google Sheets Export

This project can export `books` and `categories` to Google Sheets once per day.

## Architecture

- AWS Lambda reads `books` and `categories` from DynamoDB
- The Lambda loads a Google Workload Identity Federation credential configuration JSON from AWS Systems Manager Parameter Store
- The Lambda uses WIF to obtain a Google access token without a service account key
- The Lambda clears and rewrites two sheets:
  - `books`
  - `categories`
- EventBridge Scheduler triggers the export on a daily schedule

## Required AWS / CDK variables

- `GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_BOOKS_SHEET_NAME`
- `GOOGLE_SHEETS_CATEGORIES_SHEET_NAME`
- `BOOKS_EXPORT_SCHEDULE_EXPRESSION`
- `BOOKS_EXPORT_SCHEDULE_TIMEZONE`

Recommended values:

```text
GOOGLE_SHEETS_BOOKS_SHEET_NAME=books
GOOGLE_SHEETS_CATEGORIES_SHEET_NAME=categories
BOOKS_EXPORT_SCHEDULE_EXPRESSION=cron(0 3 * * ? *)
BOOKS_EXPORT_SCHEDULE_TIMEZONE=Asia/Tokyo
```

If `GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME` or `GOOGLE_SHEETS_SPREADSHEET_ID` is not set, the export Lambda is still deployed, but the EventBridge schedule is not created.

## Parameter Store

Store the full Google external account credential configuration JSON in Parameter Store.

Recommended parameter name example:

```text
/isbn-library/google-wif-credential-config
```

The parameter can be `String` or `SecureString`. The Lambda reads it with decryption enabled.

## GitHub Actions

Set these GitHub Variables so `cdk deploy` can create the schedule and wire the Lambda environment correctly:

- `GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_BOOKS_SHEET_NAME`
- `GOOGLE_SHEETS_CATEGORIES_SHEET_NAME`
- `BOOKS_EXPORT_SCHEDULE_EXPRESSION`
- `BOOKS_EXPORT_SCHEDULE_TIMEZONE`

The WIF config itself stays in Parameter Store and is not passed through GitHub Actions.
