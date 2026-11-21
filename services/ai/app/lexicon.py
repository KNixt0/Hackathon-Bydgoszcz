"""Lexicons shared by the rules and plugins.

All patterns are written for *folded* text (lower-case, no diacritics; see
`preprocess.normalize.fold`), so "wiąże się z ryzykiem" is matched as "wiaze sie z ryzykiem"
and posts typed without Polish characters are covered too.
"""

from __future__ import annotations

import re


def rx(*alternatives: str) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{a})" for a in alternatives))


PCT = r"\d{1,4}(?:[.,]\d+)?\s?(?:%|proc\b|procent)"

# ---- profit / benefit claims --------------------------------------------------------
PROFIT_CLAIM = rx(
    r"\bzarob\w*",
    r"\bzarabia\w*",
    r"\bzysk(?:u|i|ow|iem|ami|ach|owi|own\w+)?\b",
    r"\bzysk(?:asz|aj|ujesz|uj|acie|ac|ali)\b",
    r"\bstop\w+ zwrotu",
    r"\bpomn(?:oz|az)\w*",
    r"\bdochod\w* pasywn\w*",
    r"\bpasywn\w+ dochod\w*",
    r"\bpodwoj\w*",
    r"\bprofit\w*",
    r"\bzwrot\w* z inwestycji",
    r"\bwolnosc\w* finansow\w*",
    r"\bokazj\w+ inwestycyjn\w*",
    rf"(?:\+|nawet |do |ponad |okolo |az )?{PCT} (?:rocznie|miesiecznie|tygodniowo|dziennie|w skali roku"
    r"|w miesiac|w rok|zysku|zwrotu|na plus|w \d+ (?:dni|tygodni|miesi\w+))",
    r"\boprocentowani\w+ \d",
    r"\bearn\w*",
    r"\breturns?\b",
    r"\bbogac\w+",
    r"\bfortun\w+",
)
NO_RISK_CLAIM = rx(
    r"\bbez (?:zadnego |najmniejszego )?ryzyka",
    r"\bzero ryzyka",
    r"\bbrak ryzyka",
    r"\bnie ma (?:zadnego )?ryzyka",
    r"\bryzyko (?:jest )?(?:minimalne|zerowe|praktycznie zadne)",
    r"\bnic nie ryzykujesz",
    r"\bnie (?:mozesz|da sie) stracic",
    r"\bnie stracisz",
    r"\brisk[- ]free",
)
GUARANTEE = rx(
    r"\bgwarantowan\w+ (?:zysk|zwrot|stop|dochod|wynik|zarob|\d)\w*",
    r"\bgwaranc\w+ (?:zysku|zwrotu|kapitalu|wyniku|zarobku|dochodu)",
    r"\bgwarantuj\w+ (?:zysk|zwrot|ze |wynik|staly|\d|min)\w*",
    r"\bpewn\w+ (?:zysk|zarobek|zwrot|dochod|pieniadz)\w*",
    r"\b100\s?% (?:pewn|bezpiecz|gwaranc|skutecz)\w*",
    r"\bstal\w+ (?:zysk|dochod)\w* (?:na poziomie )?\d",
    r"\bguaranteed (?:profit|return)s?",
)

# ---- risk warnings ------------------------------------------------------------------
RISK_STANDARD = rx(
    rf"(?:{PCT}|wiekszosc) rachunkow inwestorow detalicznych odnotowuje strat\w*",
    r"kontrakty (?:na roznice )?(?:\(?cfd\)? )?sa zlozonymi instrumentami",
    r"retail investor accounts lose money",
    r"cfds are complex instruments",
)
RISK_GENERIC = rx(
    r"\bryzyk\w+ (?:utraty|straty|strat|inwestycyjn\w+|szybkiej utraty|poniesienia|rynkow\w+|walutow\w+|zwiazan\w+)",
    r"\bwiaz\w+ sie z (?:\w+ )?ryzykiem",
    r"\bobarczon\w+ (?:\w+ )?ryzykiem",
    r"\b(?:wysoki|znaczn|istotn|duz)\w+ ryzyk\w+",
    r"\bryzyk\w+ jest (?:wysokie|znaczne|duze)",
    r"\butrat\w+ (?:czesci|calosci|kapitalu|srodkow|wplaconych|zainwestowan|pieniedzy|wszystkich)",
    r"\b(?:mozesz|mozna|mozecie|moga|moze) (?:\w+ )?(?:stracic|poniesc strat)",
    r"\bstracic (?:czesc|calosc|wszystk|caly|wiecej)",
    r"\bmozliwosc\w* (?:poniesienia )?strat",
    r"\bponiesieni\w+ strat",
    r"\bstrat\w+ (?:calosci|czesci|kapitalu)",
    r"\bnie gwarantuj\w+ (?:zysk|osiagniecia|zwrotu)",
    r"\bnie (?:ma|daje|stanowi) gwarancji (?:zysk|zwrotu|osiagniecia)",
    r"\binwestowanie (?:jest ryzykowne|wiaze|niesie)",
    r"\bryzykown\w+",
    r"\bdzwigni\w+ .{0,40}ryzyk",
    r"\bcapital (?:is )?at risk",
    r"\blose (?:money|some or all|your)",
    r"\brisk of (?:losing|loss)",
    r"\bhigh(?:er)? risk",
    r"\binvest\w+ involves? risk",
    r"\bverlustrisiko",
    r"\bkapital verlieren",
    r"\brisiko\w*",
)
RISK_STEM = rx(r"ryzyk", r"\bstrac", r"\bstrat", r"\brisk", r"\bloss", r"\blose")
RISK_REFERENCE = rx(  # a pointer to the risk information, not the information itself
    r"\b(?:informacj\w+|ostrzezeni\w+|nota|wiecej|szczegol\w+|dokument\w*) (?:o|dotyczac\w+|na temat) ryzyk\w+",
    r"\bryzyk\w+ ?[:\-–>]\s*$",
    r"\brisk (?:warning|disclosure|information)\b",
    r"\bczynniki ryzyka\b",
)
RISK_PROTOTYPES = [
    "Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanego kapitału.",
    "Kontrakty CFD są złożonymi instrumentami i wiążą się z dużym ryzykiem szybkiej utraty "
    "środków pieniężnych z powodu dźwigni finansowej.",
    "Możesz stracić zainwestowane pieniądze, inwestycje są ryzykowne.",
    "Wartość inwestycji może spadać, zysk nie jest gwarantowany.",
]

# ---- historical performance (rules 12a, 12b, 13, 14) ----------------------------------
PAST_MARKER = rx(
    r"\bw (?:roku )?20[012]\d\b",
    r"\bza (?:rok )?20[012]\d\b",
    r"\b20[012]\d\s?[-–/]\s?20[012]\d\b",
    r"\b(?:ubiegl|zeszl|poprzedni|minion)\w+ (?:rok|roku|lat|miesiac\w*|kwartal\w*|tygodni\w*)",
    r"\bw (?:ciagu )?ostatni\w+ (?:\w+ )?(?:rok|roku|lat|lata|miesi\w+|kwartal\w*|tygodni\w*|dni)",
    r"\b(?:za|przez) ostatni\w+ (?:\w+ )?(?:rok|roku|lat|lata|miesi\w+|kwartal\w*|tygodni\w*|dni)",
    r"\bwynik\w* historyczn\w*",
    r"\bhistori\w+ wynikow",
    r"\bhistoryczn\w+ stop\w+ zwrotu",
    r"\bdotychczasow\w+ (?:wynik|zysk|stop)\w*",
    r"\bod poczatku (?:roku|dzialalnosci|istnienia)",
    r"\bod (?:startu|uruchomienia|debiutu)",
    r"\bw (?:\d+|kilka|trzy|dwa|szesc|cztery|piec) (?:miesi\w+|tygodni\w*|dni|lat\w*)",
    r"\b(?:zarobil|zyskal|przyniosl|wypracowal|osiagnel|osiagnal|wzrosl|urosl|dal|wygenerowal|zanotowal|pomnozyl)\w*",
    r"\bytd\b",
    r"\bw (?:i|ii|iii|iv|\d) kwartale",
    r"\bpast performance\b",
    r"\blast year\b",
)
FIGURE = rx(PCT, r"\d[\d  .]*(?:zl|pln|usd|eur|tys\.?|mln)\b", r"[x×]\s?\d", r"\d+[- ]krotn\w+")
SUB_YEAR_PERIOD = rx(
    r"\bw (?:ciagu |przeciagu )?(?:ostatni\w+ )?(?:\d+|kilka|kilku|trzy|trzech|dwa|dwoch|szesc|szesciu|cztery|jeden|jednego|pol) ?(?:miesi\w+|tygodni\w*|dni|kwartal\w*)",
    r"\b(?:za|przez) (?:ostatni\w+ )?(?:\d+ |kilka |trzy |dwa |szesc )?(?:miesiac\w*|miesiecy|tydzien|tygodni\w*|kwartal\w*|dni)\b",
    r"\bw (?:miesiac|tydzien|kwartal|pol roku)\b",
    r"\b(?:ubiegl|zeszl|ostatni|minion)\w+ (?:miesiac\w*|kwartal\w*|tygodni\w*)",
    r"\bod poczatku roku",
    r"\bytd\b",
    r"\bw (?:i|ii|iii|iv|\d) kwartale",
    r"\bod (?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|wrzesnia|pazdziernika|listopada|grudnia)",
)
FIVE_YEARS = rx(
    r"\b(?:5|piec|pieciu|6|7|8|9|10|dziesiec\w*) (?:ostatnich )?(?:lat|pelnych lat)",
    r"\b5[- ]letni\w+",
    r"\bpiecioletni\w+",
    r"\b60 miesiecy",
    r"\bod poczatku (?:dzialalnosci|istnienia)",
    r"\bod (?:uruchomienia|debiutu)",
    r"\bcaly okres (?:dzialalnosci|oferowania)",
)
# A product younger than 5 years may show a shorter history if the whole offering period is covered.
WHOLE_OFFER_PERIOD = rx(
    r"\bcal\w+ okres\w* (?:oferowania|dzialania|istnienia|funkcjonowania|dostepnosci)",
    r"\bod (?:poczatku|momentu|chwili|dnia) (?:oferowania|wprowadzenia|uruchomienia|startu|debiutu|powstania)",
    r"\bod wprowadzenia (?:produktu|funduszu|strategii|oferty|na rynek)",
    r"\bokres oferowania (?:produktu |funduszu |strategii )?(?:jest |wynosi |to )?krotsz\w+ (?:niz|od) (?:5|piec)",
    r"\b(?:krocej|mniej) niz (?:5|piec) lat\b.{0,80}\b(?:cal\w+|pelen|pelny|wszystk\w+) (?:okres|lata)",
)
OFFERED_SINCE = rx(
    r"\b(?:oferowan\w+|dostepn\w+|istni\w+|dziala\w*|notowan\w+|wprowadzon\w+|uruchomion\w+|oferujemy)"
    r"(?: \w+){0,3} od (?:\w+ ){0,2}?(20[012]\d)\b",
)
SOURCE_GIVEN = rx(
    r"\bzrodlo\b",
    r"\bna podstawie danych",
    r"\bwg danych",
    r"\bwedlug (?:danych|raportu|rankingu|badania|zestawienia)",
    r"\bdane:\s",
    r"\bopracowanie wlasne",
    r"\bsource:",
    r"\bna podstawie (?:raportu|rankingu|badania|sprawozdan)",
)
PERIOD_GIVEN = rx(
    r"\b20[012]\d\s?[-–/]\s?20[012]\d\b",
    r"\bw okresie\b",
    r"\bokres\w* (?:referencyjn\w+|od)",
    r"\bstan na\b",
    r"\b\d{1,2}[./]\d{1,2}[./]20\d\d",
    r"\bza lata\b",
    r"\bw latach\b",
    r"\b(?:za|w) (?:rok )?20[012]\d\b",
)
FX_EXPOSURE = rx(
    r"\busd\b",
    r"\beur\b",
    r"\bdolar\w*",
    r"\beuro\b",
    r"\$",
    r"€",
    r"\bfunt\w*",
    r"\bgbp\b",
    r"\bchf\b",
    r"\bs&p ?500",
    r"\bnasdaq",
    r"\bakcj\w+ (?:amerykansk|zagraniczn)\w+",
    r"\bwall street",
    r"\bwalut\w+ obc\w+",
)
FX_WARNING = rx(
    r"\bkurs\w+ walut\w*",
    r"\bryzyk\w+ walutow\w+",
    r"\bwahan\w+ kurs\w+",
    r"\bzmian\w+ kurs\w+",
    r"\bcurrency (?:risk|fluctuation)s?",
    r"\bkurs\w+ wymiany",
)
FEES_EFFECT = rx(
    r"\bprowizj\w+",
    r"\boplat\w*",
    r"\bkoszt\w+",
    r"\bobciazen\w+",
    r"\bnetto\b",
    r"\bbrutto\b",
    r"\bfees?\b",
    r"\bcharges\b",
    r"\bpo uwzglednieniu\b",
    r"\bspread\w*",
)
HIST_WARNING = rx(
    r"wynik\w* (?:historyczn\w+|osiagniet\w+ w przeszlosci|z przeszlosci|przeszl\w+|inwestycyjn\w+ osiagniet\w+ w przeszlosci)"
    r" nie (?:stanowi\w*|sa|daj\w+|gwarantuj\w+|musza|przesadzaj\w+)",
    r"nie (?:stanowi\w*|sa|daj\w+) (?:wiarygodn\w+ wskaznik\w+|gwarancj\w+|pewnosci|zapowiedzi\w*) (?:osiagniecia )?(?:\w+ )?(?:przyszl\w+ )?(?:wynik|zysk|rezultat)",
    r"past performance (?:is|does) not",
)

# ---- forecasts (rule 15) -------------------------------------------------------------
FORECAST = rx(
    r"\bprognoz\w+",
    r"\bprzewidyw\w+|\bprzewiduj\w+",
    r"\b(?:oczekiwan|spodziewan|szacowan|planowan|docelow)\w+ (?:\w+ )?(?:zysk|zwrot|stop|wzrost|wynik|rentown)\w*",
    r"\b(?:zarobisz|zyskasz|otrzymasz|dostaniesz|pomnozysz|podwoisz|wyplacimy|zarobicie|zyskacie)\b",
    r"\b(?:wzrosnie|urosnie|osiagnie|przyniesie|bedzie wart\w*|da zarobic|podwoi sie|eksploduje|wystrzeli|poszybuje)\b",
    r"\bpotencjal\w* (?:wzrostu|zysku|zwyzki)",
    r"\bdo konca (?:roku|20\d\d|kwartalu)",
    r"\bcen\w+ docelow\w+",
    r"\btarget\w*",
    rf"\b(?:nawet|do|ponad|minimum|co najmniej) {PCT} (?:rocznie|miesiecznie|tygodniowo|dziennie|zysku|zwrotu|w skali roku)",
    r"\bw (?:przyszlym|nastepnym|kolejnym) (?:roku|kwartale|miesiacu)",
    r"\bforecast\w*|\bexpected return",
    r"\bmozesz (?:zarobic|zyskac|osiagnac)",
    r"\bmozna (?:zarobic|zyskac)",
)
FORECAST_WARNING = rx(
    r"prognoz\w+ nie (?:stanowi\w*|sa|jest|daj\w+|gwarantuj\w+)",
    r"nie (?:stanowi\w*|sa|jest) (?:wiarygodn\w+ wskaznik\w+|gwarancj\w+) przyszl\w+",
    r"nie gwarantuj\w+ (?:osiagniecia|przyszl\w+|realizacji)",
    r"prognoz\w+ .{0,60}nie (?:\w+ )?(?:gwarancj|wiarygodn|pewn)",
    r"forecasts? (?:is|are) not",
)

# ---- tax (rule 16) -------------------------------------------------------------------
TAX_REF = rx(
    r"\bpodat\w+",
    r"\bbelk\w+",
    r"\bike\b",
    r"\bikze\b",
    r"\bulg\w+ podatkow\w+",
    r"\bpit-?\s?38\b",
    r"\btax\w*",
    r"\bopodatkowan\w+",
    r"\bzwolnien\w+ (?:z|od) podatk\w+",
)
TAX_INDIVIDUAL = rx(
    r"zalez\w+ od indywidualn\w+ sytuacji",
    r"indywidualn\w+ sytuacj\w+ (?:klienta|podatnika|inwestora|kazdego)",
    r"depends on (?:your|the) individual",
)
TAX_MAY_CHANGE = rx(
    r"mo(?:ze|ga) (?:w przyszlosci )?(?:ulec|sie) zmian\w+",
    r"mo(?:ze|ga) sie zmieni\w+",
    r"(?:ulec|podlegac) zmian\w+ w przyszlosci",
    r"may change",
)

# ---- supervisory authority (rules 17, 18) --------------------------------------------
SUPERVISOR_REF = rx(
    r"\bu?knf\b",
    r"\bkomisj\w+ nadzoru finansowego",
    r"\borgan\w* nadzoru",
    r"\bnadzor\w* (?:finansow\w+|panstwow\w+|regulator\w+)",
    r"\bnadzorowan\w+",
    r"\bpod (?:scislym |pelnym |stalym )?nadzorem",
    r"\bregulowan\w+ przez",
    r"\bwymog\w+ nadzorcz\w+",
    r"\bcysec\b",
    r"\bfca\b",
    r"\bbafin\b",
    r"\bregulator\w*",
    r"\bnadzor\w* (?:knf|komisji)",
    r"\blicencj\w+ (?:knf|komisji)",
    r"\bzezwoleni\w+ (?:knf|komisji)",
)
APPROVAL_WORDS = rx(
    r"\bzatwierdz\w+",
    r"\bzaaprobow\w+|\baprobat\w+",
    r"\brekomendowan\w+",
    r"\brekomendacj\w+ (?:knf|komisji|nadzoru)",
    r"\bcertyfik\w+",
    r"\bpolecan\w+",
    r"\bpotwierdz\w+ przez",
    r"\b(?:zweryfikowan|sprawdzon|przetestowan|zaakceptowan|atestowan)\w+ przez",
    r"\batest\w*",
    r"\bznak\w* jakosci",
    r"\bpozytywn\w+ opini\w+",
    r"\bapproved by",
    r"\bendorsed by",
    r"\bpod patronatem",
)
SAFETY_WORDS = rx(
    r"\bbezpiecz\w+",
    r"\bgwaran\w+",
    r"\bbez (?:zadnego )?ryzyka",
    r"\bpewnosc\w*",
    r"\bpewn\w+ inwestycj\w+",
    r"\bchron\w+",
    r"\bnic nie ryzykujesz",
    r"\bnie stracisz",
    r"\bspokojn\w+ (?:o|sen)",
    r"\bnie musisz sie (?:martwic|obawiac)",
    r"\bsafe\w*",
    r"\bzabezpiecz\w+",
    r"\bw 100\s?%",
    r"\bnic (?:ci )?nie grozi",
)
SUPERVISOR_NEGATION = rx(
    r"\bnie (?:oznacza|stanowi|gwarantuje|jest gwarancja|daje gwarancji|chroni|eliminuje|wyklucza)",
    r"\bnie (?:zatwierdz|rekomenduj|aprobuj|certyfik)\w+",
)

# ---- comparisons (rule 11) -----------------------------------------------------------
COMPARISON = rx(
    r"\b(?:lepsz|wyzsz|nizsz|tansz|szybsz|wieksz|mniejsz|korzystniejsz|bezpieczniejsz|drozs)\w+ (?:niz|od|anizeli)\b",
    r"\bw porownaniu (?:z|do)\b",
    r"\bporownani\w+ (?:z|do|ofert|broker|kont|platform)\w*",
    r"\bnaj(?:tansz|lepsz|nizsz|wyzsz|szybsz|bezpieczniejsz|korzystniejsz)\w+",
    r"\bnr\.? ?1\b",
    r"\bnumer jeden\b",
    r"\blider\w* (?:rynku|branzy|w polsce)",
    r"\bpokon\w+ (?:rynek|indeks|lokat|inflacj|konkurenc)\w*",
    r"\bbij\w+ (?:lokaty|rynek|inflacje|konkurencje)",
    r"\bw przeciwienstwie do\b",
    r"\bkonkurenc\w+",
    r"\b(?:niz|od) (?:lokat|obligacj|konkurenc|inn\w+ broker|bank)\w*",
    r"\bvs\.?\b",
    r"\bbetter than\b",
    r"\b\d+ razy (?:wiecej|taniej|szybciej|lepiej)",
)
ASSUMPTIONS_GIVEN = rx(
    r"\bprzy zalozeniu",
    r"\bzalozeni\w+",
    r"\bstan na\b",
    r"\bdane na dzien",
    r"\bna dzien \d",
    r"\bdla (?:kwoty|rachunku|inwestycji|zlecenia)",
    r"\bokres\w* porownania",
    r"\bporownan\w+ (?:obejmuje|dotyczy|uwzglednia)",
    r"\bkryteri\w+",
    r"\bmetodologi\w+",
)

# ---- advertising markers (rule 2, module 1) -------------------------------------------
AD_MARKER = rx(
    r"#?reklam\w+",
    r"\bmaterial\w* (?:reklamow\w+|promocyjn\w+|sponsorowan\w+|marketingow\w+|platn\w+)",
    r"\bwspolprac\w+ (?:reklamow\w+|platn\w+|komercyjn\w+|sponsorowan\w+|marketingow\w+|z mark\w+)",
    r"\b(?:platn\w+|komercyjn\w+|sponsorowan\w+|reklamow\w+) wspolprac\w+",
    r"#wspolpraca\w*",
    r"\b(?:post|film|artykul|wpis|tresc|odcinek|material|live) (?:jest )?sponsorowan\w+",
    r"\bsponsor\w* (?:odcinka|filmu|materialu|kanalu)",
    r"\bpartner\w* (?:odcinka|filmu|materialu)",
    r"#ad\b",
    r"#sponsored\b",
    r"\binformacj\w+ handlow\w+",
    r"\blokowani\w+ produktu",
    r"\badvertisement\b",
    r"\bpaid partnership\b",
    r"\bsponsored\b",
    r"\b(?:powstal|zrealizowan|przygotowan)\w+ we wspolpracy z",
    r"\bna zlecenie\b",
    r"\bpromocj\w+ (?:marki|firmy)\b",
    r"\b\[?(?:ad|promo)\]",
)
AD_NEGATION = rx(
    r"\bnie (?:jest )?(?:to )?(?:zadna |zaden )?(?:reklam|material\w* (?:reklamow|sponsorowan)|wspolprac|post\w* sponsorowan)\w*",
    r"\bto nie (?:jest )?(?:zadna )?(?:reklam|wspolprac)\w*",
    r"\bbez (?:zadnej )?(?:reklam|wspolprac)\w*",
    r"\bniesponsorowan\w+",
    r"\bnikt mi (?:za to |za ten \w+ )?nie (?:placi|zaplacil)",
    r"\bnot (?:an ad|sponsored)\b",
    r"\bzadna reklama",
)
INDEPENDENCE_CLAIM = rx(
    r"\bniezalezn\w+ (?:recenzj\w+|opini\w+|test\w*|ranking\w*|analiz\w+|ocen\w+|przeglad\w*|porownan\w+|ekspert\w*)",
    r"\bszczer\w+ (?:opini\w+|recenzj\w+)",
    r"\bobiektywn\w+ (?:opini\w+|recenzj\w+|test\w*|ocen\w+|analiz\w+)",
    r"\bnikt mi (?:za to |za ten \w+ )?nie (?:placi|zaplacil)",
    r"\bto nie (?:jest )?(?:zadna )?(?:reklam|wspolprac)\w*",
    r"\bbezstronn\w+",
    r"\bniezalezn\w+ (?:kanal|portal|serwis|bloger|tworca)\w*",
)
CALL_TO_ACTION = rx(
    r"\bzaloz\w* (?:\w+ )?(?:konto|rachunek)",
    r"\bzarejestruj\w* sie",
    r"\botworz\w* (?:\w+ )?(?:rachunek|konto)",
    r"\blink\w* w (?:opisie|bio|komentarzu)",
    r"\bkod\w* (?:rabatow\w+|promocyjn\w+|polecajac\w+)",
    r"\bz (?:mojego|tego|naszego) linku",
    r"\blink\w* (?:partnersk\w+|afiliacyjn\w+|polecajac\w+)",
    r"\breflink\w*",
    r"\bafiliac\w+",
    r"\bsprawdz (?:oferte|platforme|szczegoly|sam)",
    r"\bdolacz\w*\b",
    r"\bkliknij\b",
    r"\bzapisz\w* sie",
    r"\bumow\w* (?:sie na )?(?:\w+ )?(?:konsultacj|rozmow|spotkani)\w+",
    r"\bodbierz\b",
    r"\bskontaktuj\w* sie",
    r"\bnapisz (?:do|na|w)\b",
    r"\bwhatsapp|\btelegram",
    r"\bzacznij (?:inwestowac|zarabiac|juz)",
    r"\bwplac (?:juz|teraz|dzis|\d)",
    r"\bbonus\w* (?:powitaln\w+|na start|od depozytu)",
    r"\bzadzwon\b",
    r"\bwypelnij formularz",
    r"\bzostaw (?:numer|kontakt|dane)",
    r"\bsign up\b",
    r"\bjoin now\b",
)

# ---- module 3: investment advice without authorisation ----------------------------------
ADVISORY_SERVICE = rx(
    r"\bwealth management",
    r"\bfamily office",
    r"\basset management",
    r"\bprivate banking",
    r"\binvestment (?:consulting|advisory|advice)",
    r"\bzarzadz\w+ (?:\w+ )?(?:majatkiem|aktywami|portfel\w+|kapitalem|srodkami|pieniedzmi|oszczednosciami|inwestycjami)",
    r"\bdoradztw\w+ inwestycyjn\w+",
    r"\bdoradc\w+ inwestycyjn\w+",
    r"\b(?:c|k)onsulting\w* inwestycyjn\w+",
    r"\bopiek\w+ inwestycyjn\w+",
    r"\bopiekun\w* inwestycyjn\w+",
    r"\bsygnal\w+ (?:inwestycyjn\w+|tradingow\w+|transakcyjn\w+|kupna|sprzedazy|gieldow\w+)",
    r"\bgrup\w+ (?:vip|premium|sygnalow\w+|inwestycyjn\w+)",
    r"\bmentoring\w* inwestycyjn\w+",
    r"\bportfel\w* modelow\w+",
    r"\bstrategi\w+ inwestycyjn\w+ (?:szyt|dopasowan|indywidualn|dla ciebie)\w*",
    r"\bindywidualn\w+ strategi\w+ inwestycyjn\w+",
    r"\bdoradc\w+ majatkow\w+",
    r"\bplanowani\w+ majatk\w+",
    r"\binwestuj\w+ za ciebie",
    r"\bkonsultacj\w+ inwestycyjn\w+",
)
RECOMMEND = rx(
    r"\brekomend\w+",
    r"\bdoradz\w+|\bdoradzimy|\bdoradzam\w*",
    r"\bwskaz\w+ (?:ci |panstwu |dokladnie |konkretn\w+ )*(?:co|kiedy|ktore|jakie|spolk|akcj|instrument|moment)\w*",
    r"\bpowi\w+ (?:ci |wam )?(?:dokladnie )?(?:co|kiedy|ktore|jakie)",
    r"\bpodpowi\w+",
    r"\bmowi\w+ (?:ci |wam )?(?:dokladnie )?(?:co|kiedy)",
    r"\bdobierz\w+|\bdobieram\w*|\bdobor\w* (?:instrumentow|spolek|funduszy|akcji|portfela)",
    r"\bwybierz?emy (?:dla|za)|\bwybieram\w* (?:dla|za)",
    r"\bsygnal\w+ (?:kupna|sprzedazy|inwestycyjn\w+|tradingow\w+|transakcyjn\w+)",
    r"\b(?:co|kiedy|ktore \w+|jakie \w+) (?:kupic|sprzedac|trzymac|kupowac|sprzedawac)",
    r"\bzalec\w+",
    r"\bpolec\w+ (?:kupn|zakup|sprzeda|nabyci)\w*",
    r"\bkonkretn\w+ (?:spolk|typ|wskazan|rekomendacj|instrument|pozycj)\w*",
    r"\bgotow\w+ (?:typy|sygnaly|sklad portfela|portfel)",
    r"\btyp\w+ inwestycyjn\w+",
    r"\bwe recommend|\brecommendations?\b|\badvise\b",
    r"\bprowadz\w+ (?:cie |pana |pania )?(?:za reke|krok po kroku) ",
    r"\botrzymasz (?:\w+ )?(?:liste|typy|sygnaly|wskazania)",
)
TRADE_ACTION = rx(
    r"\bkup\w*",
    r"\bnaby\w+",
    r"\bsprzeda\w+",
    r"\bzby\w+",
    r"\btrzyma\w+",
    r"\bzamkn\w+ pozycj\w+",
    r"\botworz\w+ pozycj\w+",
    r"\bwejsc\w* w\b|\bwejsci\w+",
    r"\bwyjsc\w* z\b|\bwyjsci\w+",
    r"\bbuy\b|\bsell\b|\bhold\b",
    r"\bzainwestowac w\b",
    r"\bpozbyc sie\b",
)
# Instrument vocabulary of art. 2 and 3 of the act on trading in financial instruments.
INSTRUMENT = rx(
    r"\bakcj\w+",
    r"\bobligacj\w+",
    r"\bpapier\w+ wartosciow\w+",
    r"\bcertyfikat\w+ inwestycyjn\w+",
    r"\blist\w+ zastawn\w+",
    r"\bpraw\w+ poboru",
    r"\bpraw\w+ do akcji",
    r"\bwarrant\w+",
    r"\bkwit\w+ depozytow\w+",
    r"\btytul\w+ uczestnictwa",
    r"\bjednost\w+ uczestnictwa",
    r"\bfundusz\w+",
    r"\betf\w*",
    r"\binstrument\w+ (?:finansow\w+|pochodn\w+|rynku pienieznego)",
    r"\bopcj\w+",
    r"\bkontrakt\w+ (?:terminow\w+|na roznic\w+|futures|cfd)",
    r"\bcfd\b",
    r"\bswap\w*",
    r"\bforward\w*",
    r"\bderywat\w+",
    r"\buprawnien\w+ do emisji",
    r"\bforex\w*",
    r"\bpar\w* walutow\w+",
    r"\bspol\w+ (?:gieldow\w+|z gpw|z nasdaq|technologiczn\w+|dywidendow\w+)",
    r"\bindeks\w+",
    r"\bfutures\b",
    r"\bstocks?\b|\bshares\b|\bbonds?\b",
    r"\bwalor\w+",
    r"\bspolk\w+",
)
PERSONALISATION = rx(
    r"\bdopasowan\w+ do (?:twoj|panstwa|pana|pani|twoich|indywidualn|ciebie)\w*",
    r"\bindywidualn\w+",
    r"\bspersonalizowan\w+",
    r"\bna podstawie (?:twoj|twoich|panstwa|pana|pani)\w*",
    r"\btwoj\w+ (?:sytuacj|potrzeb|cel|portfel|profil|kapital|oszczednosc)\w*",
    r"\bszyt\w+ na miare",
    r"\bdla ciebie\b",
    r"\bosobist\w+ (?:dorad|opiekun|analityk)\w*",
    r"\bprofil\w* ryzyka",
    r"\banaliz\w+ (?:twoj\w+|panstwa) (?:sytuacji|portfela|potrzeb)",
    r"\b1 na 1\b|\bjeden na jeden\b",
    r"\btwojego portfela",
    r"\bpanstwa (?:sytuacj|potrzeb|majat|portfel|cel)\w*",
    r"\bpod (?:twoje|panstwa) (?:potrzeby|cele)",
    r"\btailored\b|\bpersonali[sz]ed\b",
)
PORTFOLIO_MANAGEMENT = rx(
    r"\bzarzadz\w+ (?:\w+ ){0,2}(?:portfel\w+|kapitalem|srodkami|pieniedzmi|oszczednosciami|majatkiem|aktywami)",
    r"\binwestuj\w+ za ciebie",
    r"\bprzejmiemy (?:zarzadzanie|inwestowanie)",
    r"\bpowierz\w* nam (?:\w+ )?(?:kapital|srodki|pieniadze|oszczednosci)",
    r"\bpelnomocnictw\w+ do rachunku",
    r"\bhandluj\w+ w twoim imieniu",
    r"\bobracamy (?:twoim|panstwa)",
    r"\bmanaged account",
    r"\bportfolio management",
    r"\bwplac\w+ (?:nam |do nas )?(?:srodki|kapital|depozyt)\w*,? a my",
)
ADVICE_DISCLAIMER = rx(
    r"\bnie stanowi\w* (?:\w+ )?(?:rekomendacji|porady|doradztwa)",
    r"\bnie (?:jest|sa) (?:\w+ )?(?:porad\w+|rekomendacj\w+|doradztwem) inwestycyjn\w+",
    r"\bcharakter (?:wylacznie |jedynie )?(?:edukacyjn|informacyjn)\w+",
    r"\bmaterial\w* edukacyjn\w+",
    r"\bcel\w+ (?:wylacznie )?edukacyjn\w+",
    r"\bnie jestem doradca",
    r"\bnie udzielam\w* (?:porad|rekomendacji)",
    r"\bnot (?:financial|investment) advice",
)
REPORTING_CONTEXT = rx(  # the text talks *about* scams instead of offering one
    r"\b(?:knf|komisj\w+ nadzoru finansowego|policj\w+|uokik|prokuratur\w+) (?:ostrzega|przestrzega|informuje|wpisal\w*)",
    r"\buwaga na (?:oszust|falszyw)\w+",
    r"\bjak (?:rozpoznac|nie dac sie) (?:oszust|oszuka)\w*",
    r"\boszust\w+ (?:podszywaj|obiecuj|kusz|wyludz)\w+",
    r"\bostrzezeni\w+ (?:publiczn\w+|przed)",
    r"\bfalszyw\w+ (?:inwestycj|platform|doradc|broker)\w*",
    r"\bpiramid\w+ finansow\w+",
    r"\bscam\w*",
    r"\bnie daj sie (?:oszukac|nabrac)",
)
LICENCE_NUMBER = re.compile(
    r"(?:licencj\w+|doradc\w+ inwestycyjn\w+|wpis\w*)(?: doradcy inwestycyjnego)?(?: knf)?,? ?(?:nr|numer|no)\.? ?([a-z]{0,3}[-/ ]?\d{1,6})"
)

NEGATION_BEFORE = re.compile(
    r"(?:\bnie\b|\bbrak\b|\bzadn\w+|\bnigdy\b|\bani\b|\bbez\b|\bnikt\b|\bno\b|\bnot\b|\bnever\b)(?: \w+){0,3} ?$"
)

LEGAL_FORM_RE = (
    r"(?:S\.\s?A\.|SA|sp\.\s?z\s?o\.\s?o\.|Sp\.\s?z\s?o\.\s?o\.|SP\.\s?Z\s?O\.\s?O\.|sp\.\s?k\.|Sp\.\s?k\.|S\.K\.A\.|"
    r"Ltd\.?|LTD\.?|Limited|LLC|LLP|L\.L\.C\.|GmbH|AG|Inc\.?|PLC|plc|OÜ|UAB|s\.r\.o\.|a\.s\.|Corp\.?|B\.V\.|N\.V\.|S\.à r\.l\.|SARL|PSC)"
)
