"""
RepoForge — a lightweight, self-hosted, GitHub-style code host.

It renders a browsable UI over a set of *bare* git repositories on disk
(REPO_ROOT/<owner>/<repo>.git). All dynamic data (commits, trees, blobs,
diffs) comes straight from `git` run against those bare repos; per-repo
display metadata (description, language, stars, last push) lives in
REPO_ROOT/registry.json, written by the repo seeding script.

Repositories are also clonable over plain HTTP (dumb protocol) directly
from the .git directories, which nginx serves as static files:

    git clone http://git.beacon.myl/<owner>/<repo>.git
"""
import json
import os
import re
import subprocess
from datetime import datetime, timezone

from flask import Flask, render_template, abort, redirect, url_for

try:
    import markdown as _md
except Exception:  # pragma: no cover
    _md = None

app = Flask(__name__)

REPO_ROOT = os.environ.get("REPOFORGE_ROOT", "/srv/repoforge/repos")
HEX = re.compile(r"^[0-9a-f]{7,40}$")
SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


def _registry():
    path = os.path.join(REPO_ROOT, "registry.json")
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return []


def _bare(owner, repo):
    if not (SAFE.match(owner) and SAFE.match(repo)):
        abort(404)
    p = os.path.join(REPO_ROOT, owner, repo + ".git")
    if not os.path.isdir(p):
        abort(404)
    return p


def _git(bare, *args):
    try:
        out = subprocess.run(["git", "-C", bare, *args],
                             capture_output=True, text=True, timeout=15)
        return out.stdout
    except Exception:
        return ""


def _default_branch(bare):
    b = _git(bare, "symbolic-ref", "--short", "HEAD").strip()
    return b or "main"


def _meta(owner, repo):
    for r in _registry():
        if r["owner"] == owner and r["repo"] == repo:
            return r
    return {"owner": owner, "repo": repo, "description": "",
            "language": "", "stars": 0, "pushed_at": ""}


def _ago(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return iso
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - dt).days
    if days < 1:
        return "today"
    if days < 30:
        return "%d days ago" % days
    if days < 365:
        return "%d months ago" % (days // 30)
    return "%d years ago" % (days // 365)


@app.context_processor
def _ctx():
    return {"ago": _ago, "host": "git.beacon.myl"}


@app.route("/")
def index():
    return redirect(url_for("explore"))


@app.route("/explore")
def explore():
    repos = _registry()
    repos = sorted(repos, key=lambda r: r.get("pushed_at", ""), reverse=True)
    total_stars = sum(r.get("stars", 0) for r in repos)
    return render_template("explore.html", repos=repos, total_stars=total_stars)


@app.route("/<owner>")
def owner_page(owner):
    repos = [r for r in _registry() if r["owner"] == owner]
    if not repos:
        abort(404)
    return render_template("owner.html", owner=owner,
                           repos=sorted(repos, key=lambda r: r.get("pushed_at", ""), reverse=True))


def _commits(bare, limit=60):
    fmt = "%H%x1f%an%x1f%aI%x1f%s"
    raw = _git(bare, "log", "--pretty=format:" + fmt, "-n", str(limit))
    out = []
    for line in raw.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            out.append({"sha": parts[0], "short": parts[0][:7],
                        "author": parts[1], "date": parts[2], "subject": parts[3]})
    return out


def _tree(bare, branch, path):
    ref = branch + ":" + path if path else branch
    raw = _git(bare, "ls-tree", "--long", ref)
    entries = []
    for line in raw.splitlines():
        try:
            meta, name = line.split("\t", 1)
            mode, otype, sha, size = meta.split()
        except ValueError:
            continue
        entries.append({"name": name, "type": otype, "size": size})
    entries.sort(key=lambda e: (e["type"] != "tree", e["name"].lower()))
    return entries


@app.route("/<owner>/<repo>")
def repo_home(owner, repo):
    bare = _bare(owner, repo)
    branch = _default_branch(bare)
    meta = _meta(owner, repo)
    commits = _commits(bare, 1)
    count = _git(bare, "rev-list", "--count", branch).strip() or "0"
    entries = _tree(bare, branch, "")
    readme_html = None
    for cand in ("README.md", "README", "readme.md"):
        content = _git(bare, "show", "%s:%s" % (branch, cand))
        if content:
            if _md:
                readme_html = _md.markdown(content, extensions=["fenced_code", "tables"])
            else:
                readme_html = "<pre>%s</pre>" % (content.replace("<", "&lt;"))
            break
    return render_template("repo.html", owner=owner, repo=repo, meta=meta,
                           branch=branch, entries=entries, readme_html=readme_html,
                           last=commits[0] if commits else None, count=count)


@app.route("/<owner>/<repo>/tree/<branch>/<path:path>")
def repo_tree(owner, repo, branch, path):
    bare = _bare(owner, repo)
    entries = _tree(bare, branch, path)
    if not entries:
        abort(404)
    return render_template("tree.html", owner=owner, repo=repo, branch=branch,
                           path=path, entries=entries, meta=_meta(owner, repo))


@app.route("/<owner>/<repo>/blob/<branch>/<path:path>")
def repo_blob(owner, repo, branch, path):
    bare = _bare(owner, repo)
    content = _git(bare, "show", "%s:%s" % (branch, path))
    if content == "":
        # allow genuinely empty files but 404 on missing
        listing = _git(bare, "ls-tree", branch, path)
        if not listing:
            abort(404)
    lines = content.split("\n")
    return render_template("blob.html", owner=owner, repo=repo, branch=branch,
                           path=path, lines=lines, meta=_meta(owner, repo))


@app.route("/<owner>/<repo>/commits")
@app.route("/<owner>/<repo>/commits/<branch>")
def repo_commits(owner, repo, branch=None):
    bare = _bare(owner, repo)
    branch = branch or _default_branch(bare)
    return render_template("commits.html", owner=owner, repo=repo, branch=branch,
                           commits=_commits(bare), meta=_meta(owner, repo))


@app.route("/<owner>/<repo>/commit/<sha>")
def repo_commit(owner, repo, sha):
    if not HEX.match(sha):
        abort(404)
    bare = _bare(owner, repo)
    meta_raw = _git(bare, "show", "-s",
                    "--pretty=format:%H%x1f%an%x1f%aI%x1f%s%x1f%b", sha)
    parts = meta_raw.split("\x1f")
    if len(parts) < 4:
        abort(404)
    info = {"sha": parts[0], "author": parts[1], "date": parts[2],
            "subject": parts[3], "body": parts[4] if len(parts) > 4 else ""}
    diff = _git(bare, "show", "--no-color", "--format=", sha)
    return render_template("commit.html", owner=owner, repo=repo, info=info,
                           diff=diff, meta=_meta(owner, repo))


@app.route("/healthz")
def healthz():
    return "ok\n", 200, {"Content-Type": "text/plain"}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8002, debug=False)
