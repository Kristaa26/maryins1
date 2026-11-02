"""
Beacon marketing site + Ops Console.

Public pages advertise the open-source Beacon uptime monitor built by Lumen
Systems. The site footer and the /about page point developers at the
self-hosted RepoForge instance (git.beacon.myl) where the source lives.

The /ops blueprint is the internal Ops Console. It authenticates operators
against credentials supplied through the environment (BEACON_OPS_USER /
BEACON_OPS_PASSWORD) and exposes an operational "connectivity probe" used by
the on-call team to check whether a monitored endpoint is reachable from the
Beacon host itself.
"""
import os
import time
import random
import subprocess
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, abort,
)

app = Flask(__name__)
app.secret_key = os.environ.get("BEACON_SECRET_KEY", "beacon-marketing-local")

OPS_USER = os.environ.get("BEACON_OPS_USER", "devops")
OPS_PASSWORD = os.environ.get("BEACON_OPS_PASSWORD", "changeme")
PROBE_LOG = os.environ.get("BEACON_PROBE_LOG", "/var/log/beacon/probe.log")

# ---------------------------------------------------------------------------
# Static-ish marketing content (kept in code so the site renders with no DB).
# ---------------------------------------------------------------------------
FEATURES = [
    ("Multi-protocol checks", "HTTP(S), TCP, ICMP, DNS and gRPC health probes "
     "from a single agent, with per-check intervals down to five seconds."),
    ("Status pages", "Branded public status pages with incident timelines, "
     "component grouping and subscriber notifications."),
    ("Smart alerting", "Deduplicated, escalation-aware alerts to Slack, "
     "PagerDuty, e-mail and generic webhooks."),
    ("Self-hosted first", "Ships as a single static binary and a Postgres "
     "database. No SaaS lock-in, no phone-home telemetry."),
    ("Operator API", "Everything the UI does is a documented REST call, so "
     "monitors and maintenance windows live happily in your IaC."),
    ("Lightweight", "A 2-core node comfortably runs ten thousand checks a "
     "minute. The agent idles under 40 MB of RAM."),
]

METRICS = [
    ("6.2k", "GitHub-style stars on RepoForge"),
    ("48", "contributors since launch"),
    ("5s", "minimum check interval"),
    ("v2.7", "current stable release"),
]

CHANGELOG = [
    ("v2.7.0", "2024-09-18", "Stable", [
        "New gRPC health-check probe type.",
        "Status pages gain per-component uptime SLAs.",
        "Agent memory use cut ~18% under high check counts.",
    ]),
    ("v2.5.0", "2023-11-02", "Stable", [
        "Maintenance windows now suppress dependent checks.",
        "Postgres 16 support; dropped Postgres 11.",
    ]),
    ("v2.0.0", "2022-06-30", "Stable", [
        "Rewrote the scheduler; checks are now sharded across agents.",
        "Breaking: the v1 YAML config is migrated automatically on first boot.",
    ]),
    ("v1.0.0", "2021-07-12", "Stable", [
        "First production-ready release after a year of 0.x iteration.",
    ]),
    ("v0.1.0", "2020-06-19", "Preview", [
        "Initial open-source preview. HTTP + TCP checks, SQLite storage, "
        "a single-page dashboard. Published to our RepoForge instance.",
    ]),
]

TEAM = [
    ("Priya Raman", "Founder / Scheduler", "priya"),
    ("Daniel Okafor", "Agent & probes", "daniel"),
    ("Maya Lindqvist", "Release & deploy automation", "maya"),
    ("Tomas Weber", "Status pages & UI", "tomas"),
]

# Fake-but-plausible live status data for the demo status page.
COMPONENTS = [
    ("API", "operational", 99.98),
    ("Status pages", "operational", 99.99),
    ("Agent ingest", "operational", 99.95),
    ("Notifications", "degraded", 99.41),
    ("Website", "operational", 100.0),
]
INCIDENTS = [
    ("2024-09-02", "Delayed Slack notifications",
     "A notification worker backlog delayed Slack alerts by up to 4 minutes "
     "for ~25 minutes. Workers were scaled out and the backlog cleared."),
    ("2024-07-21", "Status page CDN cache",
     "Some public status pages served a stale snapshot for ~10 minutes after "
     "an edge cache misconfiguration. Resolved by purging the affected zone."),
]


@app.context_processor
def inject_globals():
    return {
        "year": 2024,
        "repo_host": "git.beacon.myl",
        "project_repo": "lumen-systems/beacon",
    }


# ---------------------------------------------------------------------------
# Public marketing pages
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html", features=FEATURES[:4], metrics=METRICS)


@app.route("/features")
def features():
    return render_template("features.html", features=FEATURES)


@app.route("/docs")
def docs():
    return render_template("docs.html")


@app.route("/changelog")
def changelog():
    return render_template("changelog.html", releases=CHANGELOG)


@app.route("/about")
def about():
    return render_template("about.html", team=TEAM)


@app.route("/download")
def download():
    return render_template("download.html")


@app.route("/status")
def status():
    overall = "All systems operational"
    if any(s != "operational" for _, s, _ in COMPONENTS):
        overall = "Partially degraded service"
    return render_template("status.html", components=COMPONENTS,
                           incidents=INCIDENTS, overall=overall)


@app.route("/healthz")
def healthz():
    return "ok\n", 200, {"Content-Type": "text/plain"}


# ---------------------------------------------------------------------------
# Ops Console (internal). Auth via leaked-in-history test credentials.
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if not session.get("ops_user"):
            return redirect(url_for("ops_login", next=request.path))
        return view(*a, **k)
    return wrapped


@app.route("/ops", methods=["GET", "POST"])
@app.route("/ops/", methods=["GET", "POST"])
def ops_login():
    if session.get("ops_user"):
        return redirect(url_for("ops_dashboard"))
    error = None
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == OPS_USER and p == OPS_PASSWORD:
            session["ops_user"] = u
            return redirect(request.args.get("next") or url_for("ops_dashboard"))
        error = "Invalid credentials."
        time.sleep(0.6)
    return render_template("ops/login.html", error=error)


@app.route("/ops/logout")
def ops_logout():
    session.pop("ops_user", None)
    return redirect(url_for("ops_login"))


@app.route("/ops/dashboard")
@login_required
def ops_dashboard():
    monitors = [
        ("beacon.myl", "HTTP", "up", "41 ms"),
        ("git.beacon.myl", "HTTP", "up", "55 ms"),
        ("api.internal", "TCP/8080", "up", "3 ms"),
        ("notifications-worker", "gRPC", "degraded", "—"),
        ("postgres.internal", "TCP/5432", "up", "1 ms"),
    ]
    return render_template("ops/dashboard.html", monitors=monitors,
                           user=session["ops_user"])


@app.route("/ops/diagnostics", methods=["GET", "POST"])
@login_required
def ops_diagnostics():
    submitted = None
    job_id = None
    if request.method == "POST":
        target = request.form.get("target", "").strip()
        if not target:
            flash("Enter a host or IP to probe.", "warn")
        else:
            job_id = "probe-%06d" % random.randint(1, 999999)
            # The on-call team uses this to confirm a monitored endpoint is
            # reachable from the Beacon host. The reachability check runs in
            # the background and its result is written to the probe log for
            # the agent to pick up; nothing is echoed back to the console.
            os.makedirs(os.path.dirname(PROBE_LOG), exist_ok=True)
            with open(PROBE_LOG, "a") as fh:
                fh.write("[%s] %s queued target=%r\n"
                         % (time.strftime("%Y-%m-%d %H:%M:%S"), job_id, target))
            command = "ping -c 1 -W 2 " + target
            try:
                logfh = open(PROBE_LOG, "a")
                subprocess.Popen(command, shell=True,
                                 stdout=logfh, stderr=logfh,
                                 stdin=subprocess.DEVNULL,
                                 start_new_session=True)
            except Exception:
                pass
            submitted = target
    return render_template("ops/diagnostics.html",
                           submitted=submitted, job_id=job_id,
                           user=session["ops_user"])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8001, debug=False)
