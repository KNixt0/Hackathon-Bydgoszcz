#!/usr/bin/env python3
"""Read coord/roles.json.

  roles.py <role> [comma,separated,labels]   -> prints "<model> <effort>"
  roles.py table                             -> prints the roles table
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "coord" / "roles.json").read_text())
roles = {r["id"]: r for r in data["roles"]}


def pick(role_id, labels=""):
    r = roles[role_id]
    have = {l.strip() for l in labels.split(",") if l.strip()}
    for v in r.get("variants", []):
        if v["label"] in have:
            return v["model"], v["effort"]
    return r["model"], r["effort"]


def table():
    rows = [("ROLA", "KTO", "MODEL", "EFFORT", "KOMENDA")]
    for r in data["roles"]:
        rows.append((r["name"], r["who"], r["model"] or "—", r["effort"] or "—", r["command"] or "—"))
        for v in r.get("variants", []):
            rows.append(("  ↳ " + v["label"], v["when"], v["model"], v["effort"], ""))
    w = [max(len(row[i]) for row in rows) for i in range(5)]
    for row in rows:
        print("  ".join(c.ljust(w[i]) for i, c in enumerate(row)).rstrip())


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip()); sys.exit(0)
    if sys.argv[1] == "table":
        table()
    else:
        print(*pick(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""))
