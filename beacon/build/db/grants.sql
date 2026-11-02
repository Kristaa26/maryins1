-- Database role used by the Beacon control plane / Ops Console.
-- Read-mostly: it can read operational data (including the stored integration
-- credentials it must present to remote services).
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'beacon_ops') THEN
      CREATE ROLE beacon_ops LOGIN PASSWORD '0ps-r3ader-9c2f';
   END IF;
END $$;

GRANT CONNECT ON DATABASE beacon TO beacon_ops;
GRANT USAGE ON SCHEMA app, ops TO beacon_ops;
GRANT SELECT ON ALL TABLES IN SCHEMA app, ops TO beacon_ops;
ALTER DEFAULT PRIVILEGES IN SCHEMA app, ops GRANT SELECT ON TABLES TO beacon_ops;
