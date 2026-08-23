# Rakuten Books Lookup

`GET /lookup/{isbn}` first queries Google Books. When Google Books returns a normal empty result, the Lambda queries the Rakuten Books Book Search API as a fallback.

## Configuration

Set both values before `cdk deploy`:

- `RAKUTEN_APPLICATION_ID`: Rakuten Web Service application ID
- `RAKUTEN_ACCESS_KEY`: Rakuten Web Service access key

The deployment workflow reads the application ID from a GitHub repository variable and the access key from a GitHub repository secret. Neither value is committed to the repository.

If either value is missing, the Rakuten provider is disabled and Google Books behavior is unchanged.

## Error behavior

- A normal empty Google Books response triggers the Rakuten fallback.
- A normal empty response from both providers returns `404 Book metadata not found`.
- Provider rate limits return `503`.
- Other provider HTTP failures and timeouts return `502`.

Default tests mock both providers and never call the external APIs.
