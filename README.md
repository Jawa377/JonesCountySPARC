# Flask CRUD Starter (CBIS 4210 / 5210)

A Flask starter kit with a working `examples` blueprint (Create/Read/Update/Delete
against a MySQL table), used as the base for Module 4's Demo 4.

## Quick Start (Local Development)

1. **Clone and set up a virtual environment:**
   ```bash
   git clone <your-repo-url>
   cd <your-repo>
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   Then open `.env` and fill in `JAWSDB_URL` (the shared MySQL connection string
   your instructor provisioned for you) and `FLASK_SECRET_KEY` (any long random
   string — the app will not start without it).

3. **Set up the database (first time only):**
   Load `database/schema.sql` into your database, either through MySQL Workbench
   or with:
   ```bash
   mysql -h <host> -u <username> -p <database_name> < database/schema.sql
   ```
   See `database/README.md` for details.

4. **Run the app:**
   ```bash
   flask run
   ```

5. **Visit:** http://localhost:5000

## Deploying to Dokku (iscs2)

Full walkthrough is in **Module 4 Lesson 1** (`jawsdb-mysql-setup.md`); this is
the short version.

1. **Create your app on iscs2** (once per app):
   ```bash
   ssh dokku@iscs2.gcsu.edu apps:create <netid>-demo-04
   ```
   The server prints your app's URL (`https://iscs2.gcsu.edu:<port>`) and remote.

2. **Set the config vars** — same names as your local `.env`:
   ```bash
   ssh dokku@iscs2.gcsu.edu config:set <netid>-demo-04 \
       JAWSDB_URL='mysql://user:pass@host:3306/dbname' \
       FLASK_SECRET_KEY='<long-random-string>'
   ```

3. **Load the schema into your provisioned database** (once), the same way you
   did locally.

4. **Add the Dokku remote and push:**
   ```bash
   git remote add dokku dokku@iscs2.gcsu.edu:<netid>-demo-04
   git push dokku main
   ```

Every subsequent update is just `git push dokku main`. If the app fails to boot,
tail the logs:
```bash
ssh dokku@iscs2.gcsu.edu logs <netid>-demo-04 -t
```

## Project Structure

As your project grows, consider adding:

- `docs/features/` — feature specifications
- `tests/` — pytest tests (see `CLAUDE_RULES.md` §9 for the pattern)
- `migrations/` — schema-change files
- `.github/workflows/` — CI

**Note:** create folders only when you actually need them.

## AI Workflow Integration

This folder includes prompts you can copy into `docs/commands/` and reference in
Cursor / Claude Code by tagging them (e.g. `@plan_feature.md`) alongside your
feature description. Customize them for your workflow.

[![The Perfect Cursor AI Workflow (3 Simple Steps)](https://img.youtube.com/vi/Jem2yqhXFaU/0.jpg)](https://youtu.be/Jem2yqhXFaU)
> 🎥 The Perfect Cursor AI Workflow (3 Simple Steps)

### Create Brief
Establish the bigger-picture context for planning features.
```
@create_brief.md

We are building an application to help dungeon masters plan their D&D campaigns
called Dragonroll. It includes a random map generator, NPC generator, loot
generator, etc.
```

### Plan Feature
Create a technical plan for a new feature.
```
@plan_feature.md

Add an NPC generator page using the OpenAI API to generate the description and
name, plus gpt-image-1 for the portrait.
```

### Code Review
```
@code_review.md
@0001_PLAN.md
```

### Documentation
```
@write_docs.md
@0001_PLAN.md
@0001_REVIEW.md
```
