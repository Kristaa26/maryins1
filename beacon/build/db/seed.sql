-- Seed data for the Beacon operational database.

INSERT INTO app.users (email, display_name, role, password_hash) VALUES
 ('priya@lumen-systems.dev','Priya Raman','admin',  '$2b$12$9Q3bV3cE0wq7h8m0Zr2b1uK2m1sT5oVq3cQe2b7Yy9pM4kR6dL8aC'),
 ('tomas@lumen-systems.dev','Tomas Weber','editor', '$2b$12$k2J8sV1pQ0xZ4mN6rT2b9uO1wE3yU5iP7aS9dF0gH2jK4lZ6xC8bD'),
 ('oncall@lumen-systems.dev','On-call Bot','viewer','$2b$12$7fL2mN8qR1sT3uV5wX7yZ9aB0cD2eF4gH6iJ8kL0mN2oP4qR6sT8uV');

INSERT INTO app.monitors (name, kind, target, interval_s) VALUES
 ('beacon.myl','http','https://beacon.myl',15),
 ('git.beacon.myl','http','http://git.beacon.myl',30),
 ('primary-db','tcp','127.0.0.1:5432',10),
 ('notifications','grpc','127.0.0.1:9100',10),
 ('status-cdn','http','https://cdn.example.net/health',60);

INSERT INTO app.incidents (title, severity, body, resolved) VALUES
 ('Delayed Slack notifications','minor','Notification worker backlog delayed Slack alerts by up to 4 minutes.',true),
 ('Status page CDN cache','minor','Stale status snapshot served for ~10 minutes after an edge cache misconfig.',true);

INSERT INTO ops.api_tokens (label, token_hash, scopes) VALUES
 ('ci-pipeline','sha256:4f9a2c7e1b8d6a3f0c5e9d2b7a1f8c4e6d3b0a9f2c8e1d7b5a4f6c3e9d0b2a7f','checks:write incidents:write'),
 ('readonly-grafana','sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b','checks:read');

-- The release pipeline deploys tagged builds by SSHing to the Beacon host as
-- the `maya` automation account. The control plane stores that credential so
-- the "Deploy" button in the Ops Console can drive it unattended.
INSERT INTO ops.integration_credentials (service, username, secret, note) VALUES
 ('smtp-relay','beacon-mailer','Rel4y-smtp-prod','Transactional e-mail relay (notifications).'),
 ('status-cdn','cdn-purge','cdnP#rge-2023','API user for purging the status-page CDN zone.'),
 ('ssh-deploy','maya','Beacon-Deploy-7F2a!','Release-deploy automation account on the Beacon host. Used by the pipeline to install tagged builds.'),
 ('pagerduty','pd-integration','pd-ro-8812fa','Read-only PagerDuty integration key.');
