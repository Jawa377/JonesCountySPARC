# Database Setup

SPARC Textbook Studio stores everything in 10 tables (see `schema.sql`).
Locally it runs on SQLite; in production it runs on MySQL (JawsDB). The same
SQL files serve both.

## Files

- `schema.sql`: table definitions (portable SQLite/MySQL)
- `seed_data.sql`: pilot data for Ms. Ruffin's 6th Grade Science Unit 3,
  "Water in Earth's Systems," taken verbatim from the SPARC handout
- `init_db.py`: creates the tables and loads the seed data

## Choosing the engine

`DATABASE_ENGINE` in `.env` (see `.env.example`):

- `sqlite` (default): creates `database/sparc.db`. The file is gitignored.
- `mysql`: uses the database in `JAWSDB_URL`.

## Create the database

From the project root, with `.venv` active:

```bash
python database/init_db.py                 # tables + seed data
python database/init_db.py --schema-only   # tables only
```

The script **never drops or overwrites anything**:

- **SQLite:** it stops if `database/sparc.db` already exists. It builds into a
  temp file and only renames it into place when every statement succeeds.
- **MySQL:** it stops if any SPARC table already exists.

To start over, delete `database/sparc.db` (or drop the tables in MySQL)
yourself, then rerun it.

### Portability notes

- Primary keys are written `INTEGER PRIMARY KEY AUTOINCREMENT`. The init
  script swaps that to `AUTO_INCREMENT` for MySQL. That's the only dialect
  difference.
- Allowed values use `VARCHAR` + `CHECK` instead of `ENUM`. This needs
  MySQL 8.0.16+ for the checks to be enforced.
- `updated_at` is set by the app in each `UPDATE`, not by
  `ON UPDATE CURRENT_TIMESTAMP`, which is MySQL-only.
- SQLite enforces foreign keys only with `PRAGMA foreign_keys = ON` on each
  connection.

## Tables

| Table | Holds |
|---|---|
| `teachers` | Pilot teachers (no login in Phase 1) |
| `units` | A teacher's unit plus its draft settings (standards set, Lexile range, voice) |
| `materials` | Upload records: filename, type, size label. No file contents. |
| `standards` | Georgia standards, from retrieval only, never model-generated |
| `sections` | Textbook sections: body text, learning target, word count, Lexile, status |
| `vocab_terms` | Vocabulary callouts for a section |
| `assignments` | Support / core / extension practice items for a section |
| `quiz_items` | Quiz questions with a DOK level |
| `alignments` | Which element covers which standard, and the exact evidence passage |
| `coverage_dismissals` | Gaps a teacher marked as intentional |

## Heroku demo (`jones-countysparc`)

The Procfile runs `python database/init_db.py --if-missing` before gunicorn,
so each fresh dyno builds and seeds its own `sparc.db`. Heroku's filesystem
is wiped on every restart and deploy (at least daily), so **teacher edits
don't persist**. That's fine for a demo. For real use, switch to MySQL
(below). Config vars: `FLASK_SECRET_KEY`, `DATABASE_ENGINE=sqlite`.

## Production (Dokku on iscs2)

```bash
ssh dokku@iscs2.gcsu.edu config:set <app> DATABASE_ENGINE=mysql \
    JAWSDB_URL='mysql://user:pass@host:3306/dbname'
```

Then run `init_db.py` once from your machine with the same two values in
`.env`. SQLite isn't used on Dokku because the container filesystem is wiped
on every deploy.
