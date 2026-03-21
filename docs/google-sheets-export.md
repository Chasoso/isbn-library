# Google Sheets Export

This project can export `books` and `categories` to Google Sheets once per day.

## Architecture

- AWS Lambda reads `books` and `categories` from DynamoDB
- The Lambda loads a Google service account JSON key from AWS Secrets Manager
- The Lambda clears and rewrites two sheets:
  - `books`
  - `categories`
- EventBridge Scheduler triggers the export on a daily schedule

## Required AWS / CDK variables

- `GOOGLE_SERVICE_ACCOUNT_SECRET_NAME`
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

If `GOOGLE_SERVICE_ACCOUNT_SECRET_NAME` or `GOOGLE_SHEETS_SPREADSHEET_ID` is not set, the export Lambda is still deployed, but the EventBridge schedule is not created.

## Secrets Manager

Store the full Google service account JSON as the secret value.

Example secret name:

```text
isbn-library/google-sheets-service-account
```

## GitHub Actions

Set these GitHub Variables so `cdk deploy` can create the schedule and wire the Lambda environment correctly:

- `GOOGLE_SERVICE_ACCOUNT_SECRET_NAME`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_BOOKS_SHEET_NAME`
- `GOOGLE_SHEETS_CATEGORIES_SHEET_NAME`
- `BOOKS_EXPORT_SCHEDULE_EXPRESSION`
- `BOOKS_EXPORT_SCHEDULE_TIMEZONE`

The service account key itself should stay only in AWS Secrets Manager. It is not passed through GitHub Actions.
