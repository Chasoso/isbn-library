# Manual Book Registration

When Google Books, Rakuten Books, and NDL Search all return a normal empty result, the scan result page offers a manual registration form. The scanned ISBN is kept in the form and is sent to the existing `POST /books` endpoint without requiring the user to enter it again.

The form accepts a title, author, publisher, book format, category, and reading status. Title is required in the frontend. `publishedDate` and `coverImageUrl` are sent as empty values because the existing backend contract permits those values to be empty.

The existing backend validation and `userId + isbn` conditional write remain authoritative. A duplicate ISBN is shown as a `409 Book already exists` message and is not registered twice.

Temporary lookup failures such as HTTP 502 or 503 remain error states and do not open the manual registration form. Only a normal lookup 404 opens it.

The demo E2E mode uses ISBN `9780000000000` as a deterministic no-result fixture so the scan-to-manual-registration path can be tested without external API traffic.
