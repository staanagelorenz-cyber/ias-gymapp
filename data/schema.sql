-- SQLite schema for the IAS Gym App.
-- Apply with: sqlite3 gymapp.db < data/schema.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY,
    username     TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    active       INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    failed       INTEGER NOT NULL DEFAULT 0 CHECK (failed >= 0),
    locked_until TEXT,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS permissions (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

INSERT OR IGNORE INTO roles (name) VALUES
    ('Administrator'), ('Front Desk'), ('Coach'), ('Member'), ('Auditor');

INSERT OR IGNORE INTO permissions (name) VALUES
    ('user:manage'), ('role:assign'),
    ('member:create'), ('member:read'), ('member:update'), ('member:delete'),
    ('member:read_sensitive'),
    ('payment:create'), ('payment:read'), ('payment:approve_refund'),
    ('plan:create'), ('plan:read'), ('plan:update'), ('plan:update_any'), ('plan:delete'),
    ('audit:read');

INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles AS r CROSS JOIN permissions AS p
WHERE (r.name = 'Administrator' AND p.name IN
       ('user:manage', 'role:assign', 'member:read', 'payment:approve_refund'))
   OR (r.name = 'Front Desk' AND p.name IN
       ('member:create', 'member:read', 'member:update', 'payment:create', 'payment:read'))
   OR (r.name = 'Coach' AND p.name IN
       ('member:read', 'member:read_sensitive', 'plan:create', 'plan:read', 'plan:update', 'plan:delete'))
   OR (r.name = 'Member' AND p.name IN ('plan:read', 'payment:read'))
   OR (r.name = 'Auditor' AND p.name IN
       ('member:read', 'payment:read', 'plan:read', 'audit:read'));

CREATE TABLE IF NOT EXISTS members (
    id               INTEGER PRIMARY KEY,
    user_id          INTEGER UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    full_name        TEXT NOT NULL,
    contact_number   TEXT,
    health_notes     TEXT,
    membership_type  TEXT NOT NULL,
    active           INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    id          INTEGER PRIMARY KEY,
    member_id   INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    amount      NUMERIC NOT NULL CHECK (amount > 0),
    kind        TEXT NOT NULL CHECK (kind IN ('payment', 'refund')),
    recorded_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status      TEXT NOT NULL DEFAULT 'recorded'
                CHECK (status IN ('recorded', 'pending', 'approved', 'rejected')),
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plans (
    id         INTEGER PRIMARY KEY,
    member_id  INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    owner_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title      TEXT NOT NULL,
    details    TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY,
    stamp      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT NOT NULL,
    target     TEXT NOT NULL,
    outcome    TEXT NOT NULL CHECK (outcome IN ('OK', 'FAIL')),
    details    TEXT,
    prev_hash  TEXT NOT NULL,
    entry_hash TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_payments_member_id ON payments(member_id);
CREATE INDEX IF NOT EXISTS idx_plans_member_id ON plans(member_id);
CREATE INDEX IF NOT EXISTS idx_plans_owner_id ON plans(owner_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_stamp ON audit_log(stamp);
