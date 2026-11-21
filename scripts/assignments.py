#!/usr/bin/env python3
"""Owner-set assignments: who works on which areas. Stored live in the body of
the GitHub issue labeled swarm:assignments (no commit needed; agents read it each time).

  assignments.py get <login>             -> areas for that login ("" = unassigned)
  assignments.py list                    -> table
  assignments.py set <login> <value>     -> owner only; value: ui,api,ai,devops,docs | all | lead | none
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OWNER = json.loads((ROOT / "coord" / "roles.json").read_text())["owner"]
ALIAS = {"ui": "frontend", "front": "frontend", "api": "backend", "back": "backend", "model": "ai", "ml": "ai", "ops": "devops"}
VALID = {"frontend", "backend", "ai", "devops", "docs"}
BLOCK = re.compile(r"```ya?ml\n(.*?)```", re.S)


def gh(*args, stdin=None):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, input=stdin, cwd=ROOT)
    if r.returncode:
        sys.exit(r.stderr.strip() or "gh failed")
    return r.stdout


def issue():
    out = gh("issue", "list", "--state", "open", "--label", "swarm:assignments", "--limit", "1", "--json", "number,body")
    items = json.loads(out)
    if not items:
        sys.exit("no open issue labeled swarm:assignments (owner: create it)")
    return items[0]["number"], items[0]["body"] or ""


def parse(body):
    m = BLOCK.search(body)
    table = {}
    for line in (m.group(1) if m else "").splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            k, v = line.split(":", 1)
            table[k.strip()] = v.strip()
    return table


def normalise(value):
    v = value.strip().lower()
    if v in ("all", "lead", "none", ""):
        return "" if v == "none" else v
    areas = []
    for a in v.split(","):
        a = ALIAS.get(a.strip(), a.strip())
        if a not in VALID:
            sys.exit(f"unknown area '{a}' (use ui, api, ai, devops, docs, all, lead, none)")
        areas.append(a)
    return ",".join(dict.fromkeys(areas))


def render(table):
    lines = "\n".join(f"{k}: {v or 'none'}" for k, v in sorted(table.items(), key=lambda kv: kv[0].lower()))
    return ("Assignments set by **" + OWNER + "**: who takes which areas. Agents read this before every task "
            "(`./swarm whoami`). **Only " + OWNER + " edits this**, with `./swarm assign <login> <areas>`.\n\n"
            "```yaml\n# login: frontend,backend,ai,devops,docs | all | lead | none\n" + lines + "\n```\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip()); return
    cmd = sys.argv[1]
    n, body = issue()
    table = parse(body)
    if cmd == "get":
        v = table.get(sys.argv[2], "")
        print("" if v in ("none",) else v)
    elif cmd == "list":
        if not table:
            print("  (no assignments yet)")
        for k, v in sorted(table.items(), key=lambda kv: kv[0].lower()):
            print(f"  {k:24} {v or 'none'}")
    elif cmd == "set":
        me = gh("api", "user", "--jq", ".login").strip()
        if me != OWNER:
            sys.exit(f"only {OWNER} can assign (you are {me})")
        login, value = sys.argv[2], normalise(" ".join(sys.argv[3:]))
        table[login] = value
        gh("issue", "edit", str(n), "--body-file", "-", stdin=render(table))
        print(f"{login} → {value or 'none'} (issue #{n})")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
