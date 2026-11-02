-- Beacon operational database schema.
-- Two schemas: `app` (user-facing dashboard data) and `ops` (internal
-- operations data used by the control plane and the release pipeline).

CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS ops;

-- Dashboard login accounts (web UI). Passwords are bcrypt hashes.
CREATE TABLE app.users (
    id            SERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    display_name  TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'viewer',
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Configured monitors.
CREATE TABLE app.monitors (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,
    target      TEXT NOT NULL,
    interval_s  INT  NOT NULL DEFAULT 30,
    enabled     BOOLEAN NOT NULL DEFAULT true
);

-- Incident timeline shown on status pages.
CREATE TABLE app.incidents (
    id         SERIAL PRIMARY KEY,
    opened_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    title      TEXT NOT NULL,
    severity   TEXT NOT NULL,
    body       TEXT NOT NULL,
    resolved   BOOLEAN NOT NULL DEFAULT false
);

-- Operator API tokens (hashed) used by CLI / IaC.
CREATE TABLE ops.api_tokens (
    id         SERIAL PRIMARY KEY,
    label      TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    scopes     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Stored credentials for outbound integrations the control plane drives
-- (SMTP relay, the release-deploy SSH account, status-page CDN, ...).
-- These are kept in plaintext because the control plane must present them to
-- the remote services at run time.
CREATE TABLE ops.integration_credentials (
    id        SERIAL PRIMARY KEY,
    service   TEXT NOT NULL,
    username  TEXT NOT NULL,
    secret    TEXT NOT NULL,
    note      TEXT,
    rotated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
