# Database Setup

This directory contains the database structure and sample data for the CRUD
starter kit.

## Files

- `schema.sql` — table definitions
- `seed_data.sql` — sample rows for testing

## Setup Instructions

### 1. Prerequisites
- Your database has been provisioned on the shared MySQL server (Module 4
  Lesson 1) and you have the host / username / password / database name.
- Those credentials are in your local `.env` file (see the repo's `.env.example`).

### 2. Create the table structure
Run the schema file against your database:

```bash
mysql -h <host> -u <username> -p <database_name> < database/schema.sql
```

Or paste its contents into MySQL Workbench and run.

### 3. Load sample data (optional)
```bash
mysql -h <host> -u <username> -p <database_name> < database/seed_data.sql
```

## Database Structure

### `sample_table`
- `sample_table_id` — INT, primary key, auto-increment
- `first_name` — VARCHAR(50), NOT NULL
- `last_name` — VARCHAR(50), NOT NULL
- `date_of_birth` — DATE, NOT NULL
- `created_at` — TIMESTAMP, defaults to current time
- `updated_at` — TIMESTAMP, auto-updated on modification

The schema includes helpful indexes for common query patterns. `seed_data.sql`
loads 10 test rows.

## Database Connection

Local and production both read `JAWSDB_URL` from the environment. The name is
a holdover from the Heroku JawsDB add-on — the value is just a MySQL connection
string in the format `mysql://username:password@host:port/database_name`.

- **Local:** put it in `.env` (copy from `.env.example`).
- **Production (Dokku on iscs2):** set it as a config var:
  ```bash
  ssh dokku@iscs2.gcsu.edu config:set <netid>-demo-04 \
      JAWSDB_URL='mysql://user:pass@host:3306/dbname'
  ```

See Module 4 Lesson 1 (`jawsdb-mysql-setup.md`) for how you get the credentials
in the first place.
