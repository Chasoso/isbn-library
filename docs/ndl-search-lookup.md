# NDL Search Lookup

`GET /lookup/{isbn}` queries NDL Search after Google Books and Rakuten Books return normal empty results.

NDL Search is accessed through its OpenSearch API using an ISBN query. The RSS/XML response is normalized to the existing lookup contract:

- `isbn`
- `title`
- `author`
- `publisher`
- `publishedDate`
- `coverImageUrl`

NDL Search does not require an application credential for this integration, so no new Lambda environment variable or secret is added. A missing thumbnail is represented by an empty `coverImageUrl`.

Provider order is strict: Google Books, Rakuten Books, then NDL Search. Only a normal empty response advances to the next provider. HTTP errors, timeouts, and malformed XML return an upstream error instead of being reported as a missing book.

Default tests use mocked responses and do not contact NDL Search.

The application should credit NDL Search when displaying metadata obtained through this API, according to the [NDL Search API usage guidance](https://ndlsearch.ndl.go.jp/help/api).
