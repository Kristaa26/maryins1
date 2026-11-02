#!/bin/bash
# Launch the RepoForge UI (runs as www-data).
export REPOFORGE_ROOT=/srv/repoforge/repos
cd /opt/beacon/repoforge
exec /opt/beacon/venv/bin/gunicorn --bind 127.0.0.1:8002 --workers 2 --name repoforge \
     --timeout 30 --access-logfile /var/log/beacon/forge.access.log \
     --error-logfile /var/log/beacon/forge.error.log wsgi:application
