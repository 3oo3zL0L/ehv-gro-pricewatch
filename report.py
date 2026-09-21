#!/usr/bin/env python3
"""Schrijft REPORT.md: wat kost het nu, wat is het advies, en hoe liep het."""
from collections import OrderedDict
from datetime import datetime

BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(values):
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return BLOCKS[0] * len(values)
    return "".join(BLOCKS[int((v - lo) / (hi - lo) * (len(BLOCKS) - 1))] for v in values)


def _daily_last(series):
    """Eén punt per kalenderdag, de laatste observatie van die dag."""
    per_day = OrderedDict()
    for s in series:
        per_day[s["at"][:10]] = s["total"]
    return list(per_day.items())


def write(path, observed_at, results):
    out = ["# Prijswacht Eindhoven", "",
           f"Laatste update: {observed_at}", ""]
    for watch, v in results:
        out.append(f"## {watch['id']}")
        out.append("")
        if v["current_total"] is None:
            out += ["Nog geen prijzen opgehaald.", ""]
            continue
        out.append(f"**{v['advice']}** ({v['confidence']} vertrouwen)")
        out.append("")
        out.append(v["reason"])
        out.append("")
        out.append(f"Heen {watch['out_from']} t/m {watch['out_to']}, "
                   f"terug {watch['ret_from']} t/m {watch['ret_to']}.")
        out.append("")
        out.append("| Bestemming | Heen | Terug | Totaal retour |")
        out.append("|---|---|---|---|")
        for o in v["options"]:
            out.append(f"| EIN-{o['dest']} | {o['out_day']} ({o['out_price']:.2f}) "
                       f"| {o['ret_day']} ({o['ret_price']:.2f}) | **{o['total']:.2f}** |")
        out.append("")
        if v.get("unserved"):
            out.append(f"Geen directe route vanaf Eindhoven: {', '.join(v['unserved'])}.")
            out.append("")
        out.append(f"Laagste ooit gezien: **{v['min_ever']:.2f}** op {v['min_at']}. "
                   f"Historie: {v['span_days']:.1f} dagen, "
                   f"{len(v['series'])} observaties.")
        out.append("")
        daily = _daily_last(v["series"])[-30:]
        if len(daily) >= 2:
            vals = [d[1] for d in daily]
            out.append(f"`{sparkline(vals)}`  {daily[0][0]} tot {daily[-1][0]}, "
                       f"{min(vals):.0f} tot {max(vals):.0f} euro")
            out.append("")
    out.append("---")
    out.append("")
    out.append("Vertrek staat vast op Eindhoven (EIN). "
               "Prijzen komen van de Ryanair farfnd-API, alleen Ryanair-vluchten.")
    out.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
