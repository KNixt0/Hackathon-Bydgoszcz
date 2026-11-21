#!/usr/bin/env python3
"""Mechanical lead: zero LLM tokens. Does what the lead prompt describes wherever no judgment is needed.

Each cycle:
  1. unblock   status:blocked → status:ready once every "Depends on: #n" is closed
  2. merge     squash-merge a PR only when ALL hold:
               - no hold/paused label on the PR or its issue
               - every check passed or was skipped; none pending or failed;
                 owner-approval is green (required for PRs not by the owner)
               - every changed file is inside the issue's "## Owns" paths
               - the author has a check-in with operator_name on the roster
               - GitHub reports it as mergeable
  3. release   status:claimed with no PR and no activity for 120 min → unassign + status:ready
  4. report    one line per action; needs-decision issues and PRs that are stuck are listed for a human (or ./swarm lead)

  lead_auto.py [--once] [--dry-run] [--every SECONDS]   (default: loop every 120 s)
"""
import argparse
import datetime as dt
import fnmatch
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OWNER = json.loads((ROOT / "coord" / "roles.json").read_text())["owner"]
OK_STATES = {"SUCCESS", "SKIPPED", "NEUTRAL"}
BAD_STATES = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
HOLD = {"hold", "status:paused"}
sys.path.insert(0, str(ROOT / "dashboard"))
from server import parse_roster  # noqa: E402  (same parser as the live view)


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, cwd=ROOT)
    if check and r.returncode:
        raise RuntimeError(r.stderr.strip() or f"gh {' '.join(args)} failed")
    return r.stdout


def j(*args):
    return json.loads(gh(*args) or "null")


def now():
    return dt.datetime.now(dt.timezone.utc)


def age_min(iso):
    return (now() - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 60


def owns_of(body):
    m = re.search(r"^##\s*Owns\s*$(.*?)(?=^##\s|\Z)", body or "", re.S | re.M)
    paths = []
    for line in (m.group(1) if m else "").splitlines():
        line = line.split("←", 1)[0].strip().strip("`")
        if line and not line.startswith(("#", "-", "*")) or line.startswith(("demo/", "services/", "docs/", "coord/")):
            paths.append(line.lstrip("-* ").strip("`"))
    return [p for p in paths if p]


def inside(path, globs):
    for g in globs:
        if g.endswith("/**") and path.startswith(g[:-3] + "/"):
            return True
        if fnmatch.fnmatch(path, g) or path == g:
            return True
    return False


def labels(obj):
    return {l["name"] for l in obj.get("labels", [])}


def cycle(dry):
    acts, attention = [], []
    issues = j("issue", "list", "--state", "open", "--limit", "200", "--json", "number,title,labels,assignees,body,updatedAt")
    by_num = {i["number"]: i for i in issues}

    # 1. unblock
    for i in issues:
        if "status:blocked" not in labels(i):
            continue
        deps = [int(d) for d in re.findall(r"#(\d+)", " ".join(re.findall(r"(?im)^\s*depends on:.*$", i["body"] or "")))]
        if deps and all(d not in by_num for d in deps):  # not open → closed
            acts.append(f"unblock #{i['number']} (deps {', '.join('#'+str(d) for d in deps)} closed)")
            if not dry:
                gh("issue", "edit", str(i["number"]), "--remove-label", "status:blocked", "--add-label", "status:ready")

    # roster: who has a named check-in
    roster = j("issue", "list", "--state", "open", "--label", "swarm:roster", "--limit", "1", "--json", "number,comments") or []
    named = {a.get("operator") for a in parse_roster(roster) if (a.get("operator_name") or "").strip()}

    # 2. merge
    prs = j("pr", "list", "--state", "open", "--limit", "50", "--json",
            "number,title,author,labels,files,statusCheckRollup,closingIssuesReferences,mergeable,isDraft")
    with_pr = set()
    for p in prs:
        n, author = p["number"], (p.get("author") or {}).get("login")
        refs = [r["number"] for r in p.get("closingIssuesReferences") or []]
        with_pr.update(refs)
        issue = by_num.get(refs[0]) if refs else None
        why = None
        checks = {}
        for c in p.get("statusCheckRollup") or []:
            name = c.get("name") or c.get("context")
            st = (c.get("conclusion") or c.get("state") or c.get("status") or "PENDING").upper()
            # several runs of one check (e.g. owner-approval re-run after a review): any success wins
            if checks.get(name) != "SUCCESS":
                checks[name] = st
        if p.get("isDraft"):
            why = "draft"
        elif labels(p) & HOLD or (issue and labels(issue) & HOLD):
            why = "on hold"
        elif not issue:
            why = "no linked issue (Closes #n)"
        elif author != OWNER and checks.get("owner-approval") != "SUCCESS":
            why = "waiting for owner approval"
        elif any(s in BAD_STATES for s in checks.values()):
            why = "failing checks: " + ", ".join(k for k, s in checks.items() if s in BAD_STATES)
        elif any(s not in OK_STATES for s in checks.values()) or not checks:
            why = "checks pending"
        elif author not in named and author != OWNER:
            why = f"{author} has no check-in with operator_name"
        else:
            globs = owns_of(issue["body"])
            outside = [f["path"] for f in p.get("files") or [] if not inside(f["path"], globs)]
            if not globs:
                why = "issue has no Owns section"
            elif outside:
                why = "files outside Owns: " + ", ".join(outside[:5])
            elif p.get("mergeable") == "CONFLICTING":
                why = "merge conflict, author must rebase"
            elif p.get("mergeable") != "MERGEABLE":
                why = "GitHub still computing mergeability"
        if why:
            if why not in ("checks pending", "on hold", "GitHub still computing mergeability"):
                attention.append(f"PR #{n} ({author}): {why}")
            continue
        acts.append(f"merge PR #{n} → closes #{refs[0]}")
        if not dry:
            gh("pr", "merge", str(n), "--squash", "--delete-branch")
            gh("issue", "comment", str(refs[0]), "--body",
               f"```yaml\nstatus: merged\nagent: {OWNER}/lead-auto\nmodel: none\nissue: {refs[0]}\nnext: \"dependents unblock on the next cycle\"\n```")

    # 3. release stale claims
    for i in issues:
        if "status:claimed" in labels(i) and i["number"] not in with_pr and age_min(i["updatedAt"]) > 120:
            who = ",".join(a["login"] for a in i["assignees"]) or "?"
            acts.append(f"release #{i['number']} (claimed by {who}, idle >120 min)")
            if not dry:
                args = ["issue", "edit", str(i["number"]), "--remove-label", "status:claimed", "--add-label", "status:ready"]
                for a in i["assignees"]:
                    args += ["--remove-assignee", a["login"]]
                gh(*args)
                gh("issue", "comment", str(i["number"]), "--body", "Released by lead-auto: no PR and no activity for 120 min. Back to status:ready.")

    for i in issues:
        if "status:needs-decision" in labels(i):
            attention.append(f"#{i['number']} needs a human decision: {i['title']}")
    return acts, attention


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--every", type=int, default=120)
    a = ap.parse_args()
    last_attention = None
    while True:
        stamp = time.strftime("%H:%M")
        failed = False
        try:
            acts, attention = cycle(a.dry_run)
        except Exception as exc:  # network hiccup: try again next cycle
            print(f"{stamp} error: {str(exc)[:200]}", flush=True)
            acts, attention, failed = [], last_attention or [], True
        for x in acts:
            print(f"{stamp} {'[dry] ' if a.dry_run else ''}{x}", flush=True)
        if attention != last_attention:
            for x in attention:
                print(f"{stamp} ! {x}", flush=True)
            if not attention and last_attention:
                print(f"{stamp} nothing needs attention", flush=True)
            last_attention = attention
        if a.once:
            if failed:
                sys.exit(1)
            if not acts and not attention:
                print(f"{stamp} idle: nothing to do", flush=True)
            return
        time.sleep(a.every)


if __name__ == "__main__":
    main()
