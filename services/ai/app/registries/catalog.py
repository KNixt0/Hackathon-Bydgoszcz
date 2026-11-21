"""The registers named in the contract enum: Polish labels and official URLs."""

from __future__ import annotations

_KNF = "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego"
_FIRMS = f"{_KNF}/Firmy_inwestycyjne_i_Agenci_firm_inwestycyjnych"

# registry id -> (label, url). Order is the display order.
REGISTRIES: dict[str, tuple[str, str]] = {
    "knf_investment_firms": ("Rejestr firm inwestycyjnych (KNF)", _FIRMS),
    "knf_banks_brokerage": (
        "Banki prowadzące działalność maklerską (KNF)",
        f"{_FIRMS}/Banki_prowadzace_dzialalnosc_maklerska",
    ),
    "knf_brokerage_houses": ("Domy maklerskie (KNF)", f"{_FIRMS}/domy_maklerskie"),
    "knf_foreign_branches": (
        "Oddziały zagranicznych firm inwestycyjnych (KNF)",
        f"{_FIRMS}/notyfikowane_firmy_inwestycyjne_oddzialy",
    ),
    "knf_foreign_cross_border": (
        "Zagraniczne firmy inwestycyjne bez otwierania oddziału (KNF)",
        f"{_FIRMS}/notyfikowane_zagraniczne_firmy_inwestycyjne",
    ),
    "knf_public_warnings": (
        "Lista ostrzeżeń publicznych KNF",
        "https://www.knf.gov.pl/dla_konsumenta/ostrzezenia_publiczne",
    ),
    "knf_investment_advisors": (
        "Lista doradców inwestycyjnych (KNF)",
        f"{_KNF}/lista_doradcow_inwestycyjnych",
    ),
    "kirp_legal_advisers": ("Rejestr radców prawnych (KIRP)", "https://kirp.pl/"),
    "kidp_tax_advisers": ("Rejestr doradców podatkowych (KIDP)", "https://kidp.pl/"),
    # Internal UKNF source: there is no public URL and no bundled snapshot. It is fed only by
    # `context.cooperation_notified` of the analysed document.
    "uknf_cooperation_notice": ("Zgłoszenia współpracy reklamowej (źródło wewnętrzne UKNF)", ""),
}

KNF_FIRM_REGISTERS = [
    "knf_investment_firms", "knf_banks_brokerage", "knf_brokerage_houses",
    "knf_foreign_branches", "knf_foreign_cross_border",
]
# Sub-registers whose union forms the umbrella "Rejestr firm inwestycyjnych".
KNF_SUB_REGISTERS = KNF_FIRM_REGISTERS[1:]
CONTEXT_ONLY = {"uknf_cooperation_notice"}
