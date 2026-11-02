# Beacon — MaryLab machine

**Difficulty:** Medium · **OS:** Linux (Ubuntu 22.04) · **Format:** Docker, VM-style
single host · **Author:** MaryLab

A marketing site advertises the open-source **Beacon** uptime monitor (by *Lumen
Systems*). The site points developers at a self-hosted **RepoForge** code host.
A credential leaked in old git history opens an internal Ops Console with a
blind command-execution feature; from a reverse shell the player must neutralise
a 60-second self-wiping maintenance job, read the operational database for the
next user's credentials, and finally escalate to root through a `sudo`
misconfiguration.

Two flags: `/home/maya/user.txt` and `/root/root.txt` (each 32 hex characters).

---

## Services / ports

| Port | Service | Notes |
|------|---------|-------|
| 80   | nginx   | `beacon.myl` (marketing + `/ops` console) and `git.beacon.myl` (RepoForge + anonymous HTTP git clone) by `Host` header |
| 22   | OpenSSH | password auth; only `maya` may log in; root login disabled |

Internal only (not published): PostgreSQL 14 on `127.0.0.1:5432`, two gunicorn
apps on `127.0.0.1:8001`/`8002`.

## Lab hostnames

`beacon.myl` and `git.beacon.myl` both resolve to the machine. The hostname of
the box is `beacon`. No public/external domain is required.

## Build & run

```sh
docker compose up -d --build
```

The container gets its address from the Docker network (DHCP-style; no IP is
hard-coded). Map the two lab hostnames to that address from your attacking
host, e.g.:

```sh
echo "<CONTAINER_IP>  beacon.myl git.beacon.myl" | sudo tee -a /etc/hosts
```

With the default `docker-compose.yml` the box is also reachable on the host at
`http://localhost:80` (send `Host: beacon.myl` / `Host: git.beacon.myl`) and SSH
on `localhost:2222`.

Then browse `http://beacon.myl/`.

## Reset

A fresh `docker compose up` (or `docker compose restart`) restores the intended
state: the database is seeded at image build and the maintenance job, services
and flags are all baked into the image.

## Notes for the platform

* No privileged container and no added Linux capabilities — root comes only from
  the machine's own `sudo` misconfiguration.
* Everything is vendored into the image; the machine needs no internet at runtime.
* The private technical handover (full chain, real flag values, all credentials)
  is in `docs/HANDOVER.md`. The spoiler-safe player walkthrough is in
  `walkthrough/`.
