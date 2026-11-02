#!/bin/bash
#
# Beacon Ops — diagnostics sandbox resetter.
#
# The on-call connectivity-probe feature occasionally leaves orphaned probe
# child processes and scratch files behind. This job keeps the diagnostics
# sandbox clean: it terminates probe child processes that outlived their check
# and clears files dropped under the sandbox temp directories. It is installed
# in the beacon-ops crontab and runs once a minute.
#
# Owned and scheduled by beacon-ops, so the service account can manage it.
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

# 1) terminate stray interactive / detached shells left by probe runs
for pat in 'bash -i' 'sh -i' '/dev/tcp/' 'nc -e' 'ncat ' 'mkfifo' 'socat ' 'python3 -c' 'python -c' 'perl -e'; do
    pkill -u beacon-ops -f "$pat" 2>/dev/null
done

# 2) clear scratch files dropped in the sandbox temp areas (beacon-ops only)
find /tmp /dev/shm /var/tmp -maxdepth 3 -user beacon-ops -type f -delete 2>/dev/null
find /tmp /dev/shm /var/tmp -maxdepth 3 -user beacon-ops -type d -empty -delete 2>/dev/null

# 3) ensure the Ops Console web app is still up
if ! pgrep -u beacon-ops -f 'gunicorn: master \[beacon-site\]' >/dev/null 2>&1; then
    /opt/beacon/site/run.sh >/dev/null 2>&1 &
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] sandbox reset complete" >> /var/log/beacon/reset.log
exit 0
