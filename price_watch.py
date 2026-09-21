#!/usr/bin/env python3
"""Ryanair prijswacht vanaf Eindhoven.

Haalt per watch de goedkoopste retourcombinatie op, logt alles append-only naar
data/prices.csv, schrijft REPORT.md en stuurt alleen een ntfy-push bij een
gebeurtenis die er toe doet.
"""
import csv
import json
import os
import sys
import time
import traceback
import urllib.request
from datetime import date, datetime, timezone

import advice
import report

# HARDE EIS: vertrekvliegveld is altijd Eindhoven. Dit is geen instelling.
ORIGIN = "EIN"

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(ROOT, "config", "watches.json")
PRICES_FILE = os.path.join(ROOT, "data", "prices.csv")
STATE_FILE = os.path.join(ROOT, "state.json")
REPORT_FILE = os.path.join(ROOT, "REPORT.md")

API = ("https://services-api.ryanair.com/farfnd/v4/oneWayFares/{o}/{d}"
       "/cheapestPerDay?outboundMonthOfDate={m}&currency=EUR")
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 Chrome/128 Safari/537.36"),
    "Accept": "application/json",
}
RETRIES = 3
RETRY_WAIT = 5

COLUMNS = ["observed_at_utc", "watch_id", "leg", "origin", "dest",
           "flight_date", "price_eur", "dep", "arr", "days_to_flight"]

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "").strip()
FORCE_NOTIFY = os.getenv("FORCE_NOTIFY", "").strip().lower() in ("1", "true", "yes", "on")


def guard_origin():
    asked = os.getenv("ORIGIN", "").strip().upper()
    if asked and asked != ORIGIN:
        raise SystemExit(
            f"FOUT: vertrek staat vast op {ORIGIN} (Eindhoven), gevraagd werd '{asked}'. "
            "Dit script vertrekt nergens anders vandaan.")


def months_between(start, end):
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    out, y, m = [], s.year, s.month
    while (y, m) <= (e.year, e.month):
        out.append(f"{y}-{m:02d}-01")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _get(url):
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as exc:  # netwerk of HTTP, beide zijn tijdelijk genoeg
            last = exc
            if attempt < RETRIES:
                time.sleep(RETRY_WAIT)
    raise RuntimeError(f"Ryanair-API onbereikbaar na {RETRIES} pogingen: {last}")


def fetch_fares(o, d, start, end):
    """-> {vluchtdatum: {"price": float, "dep": "HH:MM", "arr": "HH:MM"}}"""
    result = {}
    for month in months_between(start, end):
        data = _get(API.format(o=o, d=d, m=month))
        for f in (data.get("outbound") or {}).get("fares", []):
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


def collect(watch):
    """-> (data, niet_bediend). data = {dest: {"out": {...}, "ret": {...}}}"""
    data, unserved = {}, []
    for dest in watch["dests"]:
        out = fetch_fares(ORIGIN, dest, watch["out_from"], watch["out_to"])
        ret = fetch_fares(dest, ORIGIN, watch["ret_from"], watch["ret_to"])
        if not out and not ret:
            unserved.append(dest)
            print(f"[{watch['id']}] {ORIGIN}-{dest}: geen directe route, overgeslagen")
            continue
        data[dest] = {"out": out, "ret": ret}
    return data, unserved


def append_rows(observed_at, watch_id, data):
    today = date.today()
    rows = []
    for dest, legs in data.items():
        for leg, fares in (("out", legs["out"]), ("ret", legs["ret"])):
            o, d = (ORIGIN, dest) if leg == "out" else (dest, ORIGIN)
            for day, f in sorted(fares.items()):
                rows.append({
                    "observed_at_utc": observed_at,
                    "watch_id": watch_id,
                    "leg": leg,
                    "origin": o,
                    "dest": d,
                    "flight_date": day,
                    "price_eur": f"{f['price']:.2f}",
                    "dep": f["dep"],
                    "arr": f["arr"],
                    "days_to_flight": (date.fromisoformat(day) - today).days,
                })
    if not rows:
        return 0
    os.makedirs(os.path.dirname(PRICES_FILE), exist_ok=True)
    new = not os.path.exists(PRICES_FILE)
    with open(PRICES_FILE, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


def notify(title, msg, click):
    print(f"\n[{title}]\n{msg}")
    if not NTFY_TOPIC:
        print("FOUT: NTFY_TOPIC is leeg, er is geen push verstuurd.", file=sys.stderr)
        raise RuntimeError("NTFY_TOPIC ontbreekt")

    def h(v):
        return v.encode("utf-8").decode("latin-1")

    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(),
        headers={"Title": h(title), "Tags": "airplane", "Click": click})
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"[ntfy] verstuurd naar topic '{NTFY_TOPIC}' (HTTP {r.status})")


def main():
    guard_origin()
    with open(CONFIG_FILE, encoding="utf-8") as fh:
        watches = [w for w in json.load(fh) if w.get("active", True)]
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as fh:
            state = json.load(fh)

    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results, new_state = [], {}

    for watch in watches:
        data, unserved = collect(watch)
        n = append_rows(observed_at, watch["id"], data)
        print(f"[{watch['id']}] {n} prijsregels gelogd")
        history = advice.load_history(PRICES_FILE, watch["id"])
        verdict = advice.evaluate(watch, history, data, date.today())
        verdict["unserved"] = unserved
        results.append((watch, verdict))
        new_state[watch["id"]] = {
            "advice": verdict["advice"],
            "total": verdict["current_total"],
            "min_ever": verdict["min_ever"],
        }

    report.write(REPORT_FILE, observed_at, results)

    for watch, v in results:
        prev = state.get(watch["id"], {})
        events = advice.notify_reasons(watch, v, prev, date.today())
        if FORCE_NOTIFY:
            events = events or ["Testmelding, geen bijzonderheden."]
        if not events:
            print(f"[{watch['id']}] {v['advice']}: {v['reason']} (geen melding)")
            continue
        best = v.get("best")
        click = ("https://www.ryanair.com/nl/nl/cheap-flights/"
                 f"{ORIGIN.lower()}-to-{(best['dest'] if best else 'gro').lower()}")
        body = "\n".join(events + ["", v["reason"], "", *v["summary"]])
        notify(f"{watch['id']}: {v['advice']}", body, click)

    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(new_state, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FOUT: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
