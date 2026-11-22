"""Scope: domestic entities and locally supervised branches.

Use the investment firm's country and register checks, never the website's language or TLD.
Missing register data does not in itself establish foreign jurisdiction.
"""

DOMESTIC = {"knf_investment_firms", "knf_brokerage_houses", "knf_banks_brokerage", "knf_foreign_branches"}
POLAND = {"pl", "polska", "poland", "pol", "rp"}


def scope(payload: dict) -> str:
    checks = payload.get("registry_checks") or []
    firm = (payload.get("entities") or {}).get("investment_firm") or {}
    country = str(firm.get("country") or "").strip().lower()
    name = str(firm.get("name") or "").strip().lower()
    firm_checks = [c for c in checks if not name or str(c.get("subject") or "").strip().lower() == name]
    if any(c.get("registry") in DOMESTIC and c.get("status") == "listed" for c in firm_checks):
        return "uknf"
    if country and country not in POLAND:
        return "outside"
    if any(
        c.get("registry") == "knf_foreign_cross_border" and c.get("status") == "listed" for c in firm_checks
    ):
        return "outside"
    return "uknf"
