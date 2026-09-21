#!/usr/bin/env python3
"""Ryanair price watch: Eindhoven <-> Girona. Sends a push (ntfy) on price drops."""
import json, os, sys, traceback, urllib.request
from datetime import date

# ---- Config (override via env vars) ----
ORIGIN = os.getenv("ORIGIN", "EIN")
DEST = os.getenv("DEST", "GRO")
OUT_FROM = os.getenv("OUT_FROM", "2026-12-24")  # heenreis venster
OUT_TO = os.getenv("OUT_TO", "2026-12-28")
RET_FROM = os.getenv("RET_FROM", "2027-01-01")  # terugreis venster
RET_TO = os.getenv("RET_TO", "2027-01-04")
TARGET = float(os.getenv("TARGET_TOTAL", "0"))  # optioneel: melding als retour onder dit bedrag komt
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "").strip()
FORCE_NOTIFY = os.getenv("FORCE_NOTIFY", "").strip().lower() in ("1", "true", "yes", "on")
STATE_FILE = os.getenv("STATE_FILE", "state.json")

API = "https://services-api.ryanair.com/farfnd/v4/oneWayFares/{o}/{d}/cheapestPerDay?outboundMonthOfDate={m}&currency=EUR"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
           "Accept": "application/json"}


def months_between(start, end):
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    out, y, m = [], s.year, s.month
    while (y, m) <= (e.year, e.month):
        out.append(f"{y}-{m:02d}-01")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def fetch_fares(o, d, start, end):
    """Return {day: {"price": float, "dep": "HH:MM", "arr": "HH:MM"}} for days in window."""
    result = {}
    for month in months_between(start, end):
        req = urllib.request.Request(API.format(o=o, d=d, m=month), headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        for f in data.get("outbound", {}).get("fares", []):
            day = f.get("day")
            if not day or not (start <= day <= end):
                continue
            if f.get("unavailable") or f.get("soldOut") or not f.get("price"):
                continue
            result[day] = {
                "price": float(f["price"]["value"]),
                "dep": (f.get("departureDate") or "")[11:16],
                "arr": (f.get("arrivalDate") or "")[11:16],
            }
    return result


def cheapest(fares):
    if not fares:
        return None, None
    day = min(fares, key=lambda k: fares[k]["price"])
    return day, fares[day]


def notify(title, msg):
    print(f"\n[{title}]\n{msg}")
    if not NTFY_TOPIC:
        print("FOUT: NTFY_TOPIC is leeg, er is geen push verstuurd. Zet het repo-secret "
              "NTFY_TOPIC op de ntfy-topicnaam (alleen de naam, geen URL).", file=sys.stderr)
        raise RuntimeError("NTFY_TOPIC ontbreekt")
    # HTTP-headers gaan in latin-1 de lijn op; zo komen UTF-8 tekens zoals de euro heel aan.
    def h(v):
        return v.encode("utf-8").decode("latin-1")
    req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(),
                                 headers={"Title": h(title), "Tags": "airplane",
                                          "Click": f"https://www.ryanair.com/nl/nl/cheap-flights/{ORIGIN.lower()}-to-{DEST.lower()}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"[ntfy] verstuurd naar topic '{NTFY_TOPIC}' (HTTP {r.status})")
    except Exception as e:
        print(f"FOUT: ntfy-call naar topic '{NTFY_TOPIC}' mislukt: {e}", file=sys.stderr)
        raise


def compare(label, new, old):
    lines = []
    for day, f in sorted(new.items()):
        prev = old.get(day, {}).get("price")
        if prev is not None and f["price"] < prev:
            lines.append(f"{label} {day} {f['dep']}-{f['arr']}: €{prev:.2f} → €{f['price']:.2f}")
    return lines


def main():
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as fh:
            state = json.load(fh)

    out = fetch_fares(ORIGIN, DEST, OUT_FROM, OUT_TO)
    ret = fetch_fares(DEST, ORIGIN, RET_FROM, RET_TO)

    od, of = cheapest(out)
    rd, rf = cheapest(ret)
    summary = []
    if of:
        summary.append(f"Goedkoopste heen: {od} {of['dep']}-{of['arr']} €{of['price']:.2f}")
    if rf:
        summary.append(f"Goedkoopste terug: {rd} {rf['dep']}-{rf['arr']} €{rf['price']:.2f}")
    total = (of["price"] + rf["price"]) if of and rf else None
    if total is not None:
        summary.append(f"Retour totaal: €{total:.2f}")

    drops = compare("Heen", out, state.get("out", {})) + compare("Terug", ret, state.get("ret", {}))
    first_run = not state

    if FORCE_NOTIFY:
        body = "\n".join(drops + [""] + summary) if drops else "\n".join(summary)
        notify(f"Testmelding prijswacht {ORIGIN}-{DEST}", body or "Nog geen prijzen beschikbaar.")
    elif first_run:
        notify(f"Prijswacht {ORIGIN}-{DEST} gestart", "\n".join(summary) or "Nog geen prijzen beschikbaar.")
    elif drops:
        notify(f"Prijsdaling {ORIGIN}-{DEST}", "\n".join(drops + [""] + summary))
    elif TARGET and total is not None and total <= TARGET and not state.get("target_hit"):
        notify(f"Onder doelprijs €{TARGET:.0f}", "\n".join(summary))
    else:
        print("Geen daling.\n" + "\n".join(summary))

    state = {"out": out, "ret": ret, "target_hit": bool(TARGET and total is not None and total <= TARGET)}
    with open(STATE_FILE, "w") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FOUT: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
