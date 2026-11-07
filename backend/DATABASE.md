# PhytoScan SQLite database

The backend uses Python's standard `sqlite3` module. The default database is
`backend/data/phytoscan.db`; override it with `DATABASE_PATH`.

Initialize or update the schema and seed reference data from the backend folder:

```powershell
.\.venv\Scripts\python.exe -m app.db.cli
```

Migrations in `app/db/migrations` are applied once and recorded in
`schema_migrations`. Seeding is idempotent and reads the existing plant,
disease, model-manifest, and frozen-evaluation metadata files.

The schema covers users and sessions, devices, plants and diseases, sourced
guidance, model artifacts/classes/thresholds/deployments, scan sessions and
images, plant predictions, manual confirmations, disease results, immutable
result-detail snapshots, events, errors, and user feedback.

Image bytes and model binaries are deliberately not stored in SQLite. A scan
image record stores metadata and SHA-256 only. Database, WAL, and shared-memory
files are ignored by Git.

The existing analysis response contract is unchanged. Successful completed and
manual-confirmation outcomes are persisted on a best-effort basis. A database
write failure is logged but does not replace a valid inference response.

## Device-owned scan history

Flutter generates one random UUID per installation and sends it as
`X-Device-ID`. The backend attaches completed scans to that device and exposes:

- `GET /api/v1/history`
- `GET /api/v1/history/{scan_id}`
- `DELETE /api/v1/history/{scan_id}`
- `DELETE /api/v1/history`

History deletion is a soft delete. Requests without an owner identifier are
rejected, and one device cannot read or delete another device's rows. Flutter
uses the backend as the authoritative history, keeps a local offline cache, and
queues failed deletes for the next successful synchronization.

`X-Device-ID` is an installation identifier, not a user login. Production
traffic must use HTTPS, and account-based cross-device history should only be
enabled together with authenticated sessions and secure token storage.
