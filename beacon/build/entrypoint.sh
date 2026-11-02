#!/bin/bash
# Beacon machine entrypoint: bring up all services VM-style, then idle.
set -e
PGBIN="$(ls -d /usr/lib/postgresql/*/bin | head -1)"
PGVER="$(basename "$(dirname "$PGBIN")")"

echo "[*] starting postgresql ($PGVER)"
pg_ctlcluster "$PGVER" main start

echo "[*] starting ssh"
mkdir -p /run/sshd
/usr/sbin/sshd

echo "[*] starting cron"
cron

echo "[*] starting nginx"
nginx

echo "[*] starting RepoForge (www-data)"
runuser -u www-data -- /opt/beacon/repoforge/run.sh &

echo "[*] starting Beacon site + Ops Console (beacon-ops)"
runuser -u beacon-ops -- /opt/beacon/site/run.sh &

echo "[*] beacon is up:  http://beacon.myl/   http://git.beacon.myl/"
# Keep the container in the foreground.
sleep 2
tail -F /var/log/beacon/*.log /var/log/nginx/*.log 2>/dev/null
