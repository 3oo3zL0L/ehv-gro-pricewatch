#!/usr/bin/env python3
"""Beslislogica: koop nu of wacht nog.

Ryanair-prijzen stijgen vrijwel altijd naarmate stoelen vollopen. Dit is dus
een dip-jager met deadline, geen wacht-optimalisator.
"""
import csv
import os
from collections import defaultdict
from datetime import date, datetime

DIP_PERCENTILE = 0.20       # onderste kwintiel van de eigen historie telt als dip
STEP_UP_PCT = 0.08          # sprong omhoog die op een volgelopen fare bucket wijst
MIN_DAYS_FOR_DIP = 7        # minder historie dan dit, dan is een percentiel niets waard
STEP_UP_MIN_DAYS = 3        # onder deze historie is een sprong gewoon ruis
HARD_CUTOFF_DAYS = 21       # hieronder verdwijnen de goedkope fare classes
NEW_LOW_NOTIFY_PCT = 0.05   # nieuwe bodem moet 5% schelen voor een push
DEADLINE_WARN_DAYS = 7


def load_history(path, watch_id):
    """-> [{"at": str, "dest": str, "total": float, "out_day", "ret_day", ...}] oplopend."""
    if not os.path.exists(path):
        return []
    legs = defaultdict(dict)  # (at, dest, leg) -> {day: price}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["watch_id"] != watch_id:
                continue
            dest = row["dest"] if row["leg"] == "out" else row["origin"]
            legs[(row["observed_at_utc"], dest, row["leg"])][row["flight_date"]] = float(row["price_eur"])
    per_run = defaultdict(list)
    for (at, dest, leg), fares in legs.items():
        per_run[(at, dest)].append((leg, fares))
    snapshots = defaultdict(list)
    for (at, dest), items in per_run.items():
        d = dict(items)
        if "out" not in d or "ret" not in d or not d["out"] or not d["ret"]:
            continue
        out_day = min(d["out"], key=d["out"].get)
        ret_day = min(d["ret"], key=d["ret"].get)
        snapshots[at].append({
            "dest": dest,
            "total": round(d["out"][out_day] + d["ret"][ret_day], 2),
            "out_day": out_day, "out_price": d["out"][out_day],
            "ret_day": ret_day, "ret_price": d["ret"][ret_day],
        })
    series = []
    for at in sorted(snapshots):
        best = min(snapshots[at], key=lambda x: x["total"])
        series.append(dict(best, at=at, options=sorted(snapshots[at], key=lambda x: x["total"])))
    return series


def _slope_per_day(series):
    """Kleinste-kwadraten helling in euro per dag over de laatste 7 dagen."""
    if len(series) < 3:
        return None
    last = datetime.strptime(series[-1]["at"], "%Y-%m-%dT%H:%M:%SZ")
    pts = []
    for s in series:
        t = datetime.strptime(s["at"], "%Y-%m-%dT%H:%M:%SZ")
        age = (last - t).total_seconds() / 86400.0
        if age <= 7:
            pts.append((-age, s["total"]))
    if len(pts) < 3:
        return None
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    den = sum((p[0] - mx) ** 2 for p in pts)
    if den == 0:
        return None
    return sum((p[0] - mx) * (p[1] - my) for p in pts) / den


def _span_days(series):
    if len(series) < 2:
        return 0.0
    a = datetime.strptime(series[0]["at"], "%Y-%m-%dT%H:%M:%SZ")
    b = datetime.strptime(series[-1]["at"], "%Y-%m-%dT%H:%M:%SZ")
    return (b - a).total_seconds() / 86400.0


def evaluate(watch, series, live_data, today):
    if not series:
        return {"advice": "WAIT", "reason": "Nog geen prijzen opgehaald.",
                "confidence": "LOW", "current_total": None, "min_ever": None,
                "best": None, "summary": [], "options": [], "new_low": False,
                "days_to_buy_by": None, "percentile": None, "step_up": False}

    now = series[-1]
    totals = [s["total"] for s in series]
    current = now["total"]
    min_ever = min(totals)
    min_at = next(s["at"][:10] for s in series if s["total"] == min_ever)
    percentile = sum(1 for t in totals if t <= current) / len(totals)
    span = _span_days(series)
    prev = series[-2]["total"] if len(series) > 1 else None
    span_ok = _span_days(series) >= STEP_UP_MIN_DAYS
    step_up = bool(prev and span_ok and current > prev * (1 + STEP_UP_PCT))
    slope = _slope_per_day(series)

    buy_by = date.fromisoformat(watch["buy_by_date"])
    days_to_buy_by = (buy_by - today).days
    first_flight = date.fromisoformat(watch["out_from"])
    days_to_flight = (first_flight - today).days
    target = float(watch.get("target_total") or 0)

    reasons, advice_ = [], "WAIT"
    if target and current <= target:
        advice_ = "BUY"
        reasons.append(f"Onder je doelprijs van {target:.0f} euro.")
    if days_to_flight <= HARD_CUTOFF_DAYS:
        advice_ = "BUY"
        reasons.append(f"Nog {days_to_flight} dagen tot vertrek, de goedkope fare classes zijn weg.")
    if days_to_buy_by <= 0:
        advice_ = "BUY"
        reasons.append("Je eigen deadline is verstreken.")
    if step_up:
        advice_ = "BUY"
        reasons.append(f"Prijs sprong {(current / prev - 1) * 100:.0f}% omhoog, een fare bucket is volgelopen.")
    if span >= MIN_DAYS_FOR_DIP and percentile <= DIP_PERCENTILE:
        advice_ = "BUY"
        reasons.append(f"Huidige prijs zit in de goedkoopste {percentile * 100:.0f}% van alles wat je gezien hebt.")

    if advice_ == "WAIT":
        if slope is not None and slope < 0:
            reasons.append(f"Trend is {slope:+.2f} euro per dag, prijs zakt nog.")
        elif span < MIN_DAYS_FOR_DIP:
            reasons.append(f"Pas {span:.1f} dagen historie, te weinig om een dip te herkennen.")
        else:
            reasons.append(f"Prijs staat op {(current / min_ever - 1) * 100:.0f}% boven de laagste stand, geen dip.")

    confidence = "LOW" if span < MIN_DAYS_FOR_DIP else ("MED" if span < HARD_CUTOFF_DAYS else "HIGH")
    reasons.append(f"Nog {days_to_buy_by} dagen tot je deadline van {watch['buy_by_date']}.")

    summary = [f"Nu: {current:.2f} euro via {now['dest']}"
               f" (heen {now['out_day']}, terug {now['ret_day']})",
               f"Laagste ooit: {min_ever:.2f} euro op {min_at}"]
    if slope is not None:
        summary.append(f"Trend 7 dagen: {slope:+.2f} euro/dag")

    return {"advice": advice_, "reason": " ".join(reasons), "confidence": confidence,
            "current_total": current, "min_ever": min_ever, "min_at": min_at,
            "percentile": percentile, "step_up": step_up, "slope": slope,
            "best": now, "options": now["options"], "summary": summary,
            "new_low": current <= min_ever, "days_to_buy_by": days_to_buy_by,
            "days_to_flight": days_to_flight, "span_days": span, "series": series}


def notify_reasons(watch, v, prev_state, today):
    """Welke gebeurtenissen rechtvaardigen een push."""
    events = []
    if v["current_total"] is None:
        return events
    if v["advice"] == "BUY" and prev_state.get("advice") != "BUY":
        events.append(f"Advies slaat om naar KOPEN: {v['current_total']:.2f} euro")
    old_min = prev_state.get("min_ever")
    if v["new_low"] and old_min and v["current_total"] <= old_min * (1 - NEW_LOW_NOTIFY_PCT):
        events.append(f"Nieuwe laagste prijs: {v['current_total']:.2f} euro "
                      f"(was {old_min:.2f})")
    target = float(watch.get("target_total") or 0)
    if target and v["current_total"] <= target and not prev_state.get("target_hit"):
        events.append(f"Onder doelprijs {target:.0f} euro")
    if 0 < v["days_to_buy_by"] <= DEADLINE_WARN_DAYS:
        events.append(f"Deadline over {v['days_to_buy_by']} dagen")
    return events
