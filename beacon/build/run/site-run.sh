#!/bin/bash
# Launch the Beacon marketing site + Ops Console (runs as beacon-ops).
set -a
. /etc/beacon/beacon.env
set +a
cd /opt/beacon/site
exec /opt/beacon/venv/bin/gunicorn --bind 127.0.0.1:8001 --workers 2 --name beacon-site \
     --timeout 30 --access-logfile /var/log/beacon/site.access.log \
     --error-logfile /var/log/beacon/site.error.log wsgi:application
