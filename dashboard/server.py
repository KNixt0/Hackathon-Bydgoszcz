#!/usr/bin/env python3
"""Live swarm view: serves dashboard/index.html and /api/state.

/api/state is read from GitHub through YOUR `gh` login, so no token ever
reaches the browser. It binds to 127.0.0.1 only.

    python3 dashboard/server.py            # http://127.0.0.1:8787
    python3 dashboard/server.py --port 9000 --repo owner/name
"""
import argparse
import http.server
import json
import pathlib
import subprocess
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
ROLES = HERE.parent / "coord" / "roles.json"
CACHE_SECONDS = 8

PR_FIELDS = ",".join([
    "number", "title", "author", "headRefName", "labels", "isDraft", "url",
    "reviewDecision", "statusCheckRollup", "closingIssuesReferences", "updatedAt",
])


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=40, cwd=HERE.parent)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"gh {' '.join(args)} failed")
    return json.loads(r.stdout or "null")


def checks(rollup):
    out = []
    for c in rollup or []:
        name = c.get("name") or c.get("context") or "?"
        state = c.get("conclusion") or c.get("state") or c.get("status") or "PENDING"
        out.append({"name": name, "state": state.upper()})
    return out


class State:
    def __init__(self, repo):
        self.repo = repo
        self.owner = repo.split("/")[0]
        self.lock = threading.Lock()
        self.cached = None
        self.cached_at = 0.0

    def fetch(self):
        R = self.repo
        jobs = {
            "issues": ("issue", "list", "-R", R, "--state", "open", "--limit", "100",
                       "--json", "number,title,labels,assignees,updatedAt,url"),
            "closed": ("issue", "list", "-R", R, "--state", "closed", "--limit", "30",
                       "--json", "number,title,closedAt,assignees"),
            "prs": ("pr", "list", "-R", R, "--state", "open", "--limit", "50", "--json", PR_FIELDS),
            "merged": ("pr", "list", "-R", R, "--state", "merged", "--limit", "16",
                       "--json", "number,title,author,mergedAt,closingIssuesReferences,url"),
            "events": ("api", f"repos/{R}/events?per_page=40"),
            "collaborators": ("api", f"repos/{R}/collaborators", "--jq", "[.[].login]"),
        }
        with ThreadPoolExecutor(len(jobs)) as pool:
            futures = {k: pool.submit(gh, *a) for k, a in jobs.items()}
            data = {k: f.result() for k, f in futures.items()}

        for p in data["prs"]:
            p["checks"] = checks(p.pop("statusCheckRollup", None))
        data["events"] = [
            {
                "type": e.get("type"),
                "actor": (e.get("actor") or {}).get("login"),
                "at": e.get("created_at"),
                "payload": slim_payload(e.get("type"), e.get("payload") or {}),
            }
            for e in data["events"]
        ]
        data.update(repo=R, owner=self.owner, fetchedAt=time.time())
        return data

    def get(self):
        with self.lock:
            if self.cached is None or time.time() - self.cached_at > CACHE_SECONDS:
                self.cached = self.fetch()
                self.cached_at = time.time()
            return self.cached


def slim_payload(kind, p):
    """Keep only what the ticker shows (titles, numbers, refs)."""
    if kind == "PushEvent":
        return {"ref": p.get("ref"), "size": p.get("size") or len(p.get("commits") or [])}
    if kind in ("PullRequestEvent", "PullRequestReviewEvent", "PullRequestReviewCommentEvent"):
        pr = p.get("pull_request") or {}
        return {"action": p.get("action"), "number": pr.get("number"), "title": pr.get("title"),
                "merged": pr.get("merged"), "review": (p.get("review") or {}).get("state")}
    if kind in ("IssuesEvent", "IssueCommentEvent"):
        i = p.get("issue") or {}
        return {"action": p.get("action"), "number": i.get("number"), "title": i.get("title"),
                "isPR": "pull_request" in i, "label": (p.get("label") or {}).get("name"),
                "assignee": (p.get("assignee") or {}).get("login")}
    if kind in ("CreateEvent", "DeleteEvent"):
        return {"refType": p.get("ref_type"), "ref": p.get("ref")}
    return {}


def make_handler(state):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(HERE), **kw)

        def do_GET(self):
            route = self.path.split("?")[0]
            if route in ("/api/state", "/api/roles"):
                try:
                    payload = state.get() if route == "/api/state" else json.loads(ROLES.read_text())
                    body, code = json.dumps(payload).encode(), 200
                except Exception as exc:  # gh offline, auth expired, rate limit…
                    body, code = json.dumps({"error": str(exc)[:500]}).encode(), 502
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            if route not in ("/", "", "/index.html"):
                self.send_error(404)
                return
            self.path = "/index.html"
            super().do_GET()

        def log_message(self, fmt, *args):
            if "/api/state" not in str(args[0] if args else ""):
                super().log_message(fmt, *args)

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--repo", help="owner/name (default: this checkout's GitHub repo)")
    ap.add_argument("--open", action="store_true", help="open the browser")
    args = ap.parse_args()
    try:
        repo = args.repo or gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    except Exception as exc:
        raise SystemExit(f"Nie mogę odczytać repo przez gh ({exc}).\nZaloguj się: gh auth login")
    handler = make_handler(State(repo))
    server = None
    for port in range(args.port, args.port + 20):  # first free port
        try:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit(f"Brak wolnego portu od {args.port}")
    url = f"http://127.0.0.1:{port}"
    print(f"Swarm na żywo: {url}  (repo {repo}, demo: {url}/?demo=1)  · Ctrl+C kończy", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
