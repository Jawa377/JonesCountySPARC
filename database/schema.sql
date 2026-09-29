-- SPARC Textbook Studio: database schema (Phase 1)
--
-- Portable SQL for SQLite (local, database/sparc.db) and MySQL (JawsDB).
-- Portability rules this file follows:
--   * Primary keys are written as "INTEGER PRIMARY KEY AUTOINCREMENT" (SQLite).
--     The init script swaps AUTOINCREMENT -> AUTO_INCREMENT for MySQL; that is
--     the only dialect difference in this file.
--   * No ENUM: allowed values use VARCHAR + CHECK (SQLite, MySQL 8.0.16+).
--   * No ON UPDATE CURRENT_TIMESTAMP (MySQL-only): app code sets
--     updated_at = CURRENT_TIMESTAMP in every UPDATE statement.
--   * No DROP TABLE here. Recreating the database is a separate, explicit step.
--   * SQLite enforces foreign keys only with PRAGMA foreign_keys = ON, which the
--     connection helper sets on every connection.

-- Pilot teachers. Phase 1 has no login; the current teacher lives in the
-- Flask session (see get_current_teacher()).
CREATE TABLE teachers (
    teacher_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One teacher's unit, plus its draft settings (studio left rail).
CREATE TABLE units (
    unit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id     INTEGER      NOT NULL,
    subject        VARCHAR(50)  NOT NULL,
    grade          INTEGER      NOT NULL,
    unit_number    INTEGER      NOT NULL,
    title          VARCHAR(200) NOT NULL,
    standards_set  VARCHAR(100) NOT NULL,
    lexile_min     INTEGER      NOT NULL DEFAULT 850,
    lexile_max     INTEGER      NOT NULL DEFAULT 950,
    voice          VARCHAR(30)  NOT NULL DEFAULT 'match_materials',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_units_teacher FOREIGN KEY (teacher_id)
        REFERENCES teachers (teacher_id) ON DELETE RESTRICT,
    CONSTRAINT uq_units_teacher_unit UNIQUE (teacher_id, subject, grade, unit_number)
);

-- Upload records only. Phase 1 stores no file contents and does no parsing.
CREATE TABLE materials (
    material_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id      INTEGER      NOT NULL,
    filename     VARCHAR(255) NOT NULL,
    file_type    VARCHAR(4)   NOT NULL,
    size_label   VARCHAR(50)  NOT NULL,
    uploaded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_materials_unit FOREIGN KEY (unit_id)
        REFERENCES units (unit_id) ON DELETE CASCADE,
    CONSTRAINT ck_materials_file_type CHECK (file_type IN ('PPTX', 'DOCX', 'PDF'))
);

-- Georgia standards. Rows come from retrieval (services/standards_retrieval.py),
-- never from the model. units.standards_set matches standards.standards_set.
CREATE TABLE standards (
    standard_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    code           VARCHAR(20)  NOT NULL,
    description    TEXT         NOT NULL,
    standards_set  VARCHAR(100) NOT NULL,
    source_url     VARCHAR(255) NOT NULL,
    framework      VARCHAR(20)  NOT NULL,
    CONSTRAINT uq_standards_set_code UNIQUE (standards_set, code),
    CONSTRAINT ck_standards_framework CHECK (framework IN ('GSE', 'new ELA'))
);

-- A textbook section. body_text is plain text: paragraphs separated by a
-- blank line, subheadings on their own line starting with "## ".
CREATE TABLE sections (
    section_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id           INTEGER      NOT NULL,
    section_number    INTEGER      NOT NULL,
    title             VARCHAR(200) NOT NULL,
    learning_target   TEXT,
    body_text         TEXT         NOT NULL,
    word_count        INTEGER      NOT NULL DEFAULT 0,
    lexile            INTEGER,
    duration_minutes  INTEGER,
    status            VARCHAR(10)  NOT NULL DEFAULT 'draft',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sections_unit FOREIGN KEY (unit_id)
        REFERENCES units (unit_id) ON DELETE CASCADE,
    CONSTRAINT uq_sections_unit_number UNIQUE (unit_id, section_number),
    CONSTRAINT ck_sections_status CHECK (status IN ('draft', 'edited'))
);

-- Vocabulary callouts shown in the lesson view.
CREATE TABLE vocab_terms (
    vocab_term_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id     INTEGER      NOT NULL,
    term           VARCHAR(100) NOT NULL,
    definition     TEXT         NOT NULL,
    sort_order     INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT fk_vocab_terms_section FOREIGN KEY (section_id)
        REFERENCES sections (section_id) ON DELETE CASCADE
);

-- Practice items: same standard, three entry points.
CREATE TABLE assignments (
    assignment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id     INTEGER     NOT NULL,
    level          VARCHAR(10) NOT NULL,
    prompt_text    TEXT        NOT NULL,
    CONSTRAINT fk_assignments_section FOREIGN KEY (section_id)
        REFERENCES sections (section_id) ON DELETE CASCADE,
    CONSTRAINT ck_assignments_level CHECK (level IN ('support', 'core', 'extension'))
);

CREATE TABLE quiz_items (
    quiz_item_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id    INTEGER NOT NULL,
    dok_level     INTEGER NOT NULL,
    prompt_text   TEXT    NOT NULL,
    CONSTRAINT fk_quiz_items_section FOREIGN KEY (section_id)
        REFERENCES sections (section_id) ON DELETE CASCADE,
    CONSTRAINT ck_quiz_items_dok CHECK (dok_level BETWEEN 1 AND 4)
);

-- The Standards Engine. One row = one standard's coverage by one element.
--   element_type/element_id point at a section, assignment, or quiz_item row
--   (polymorphic, so no FK; app code deletes alignments with their element).
--   evidence_text is the exact passage inside that element that covers the
--   standard; the studio highlights it. NULL means the whole element.
--   A 'gap' row has no element: it records that nothing in the unit covers
--   the standard, and evidence_note says why.
-- The coverage panel rolls rows up per (unit, standard): any covered ->
-- covered, else any partial -> partial, else gap.
CREATE TABLE alignments (
    alignment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id          INTEGER     NOT NULL,
    standard_id      INTEGER     NOT NULL,
    element_type     VARCHAR(10),
    element_id       INTEGER,
    coverage_status  VARCHAR(10) NOT NULL,
    evidence_text    TEXT,
    evidence_note    TEXT,
    CONSTRAINT fk_alignments_unit FOREIGN KEY (unit_id)
        REFERENCES units (unit_id) ON DELETE CASCADE,
    CONSTRAINT fk_alignments_standard FOREIGN KEY (standard_id)
        REFERENCES standards (standard_id) ON DELETE RESTRICT,
    CONSTRAINT ck_alignments_element_type
        CHECK (element_type IN ('section', 'assignment', 'quiz_item')),
    CONSTRAINT ck_alignments_status
        CHECK (coverage_status IN ('covered', 'partial', 'gap')),
    CONSTRAINT ck_alignments_gap_has_no_element CHECK (
        (coverage_status = 'gap' AND element_type IS NULL AND element_id IS NULL)
        OR (coverage_status <> 'gap' AND element_type IS NOT NULL AND element_id IS NOT NULL)
    )
);

-- A teacher saying "this gap is intentional" (e.g. planned for a later section).
CREATE TABLE coverage_dismissals (
    dismissal_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id       INTEGER      NOT NULL,
    standard_id   INTEGER      NOT NULL,
    reason        VARCHAR(255) NOT NULL,
    dismissed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dismissals_unit FOREIGN KEY (unit_id)
        REFERENCES units (unit_id) ON DELETE CASCADE,
    CONSTRAINT fk_dismissals_standard FOREIGN KEY (standard_id)
        REFERENCES standards (standard_id) ON DELETE RESTRICT,
    CONSTRAINT uq_dismissals_unit_standard UNIQUE (unit_id, standard_id)
);
