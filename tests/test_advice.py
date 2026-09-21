import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import advice  # noqa: E402

TODAY = date(2026, 9, 21)
WATCH = {"id": "t", "dests": ["GRO"], "out_from": "2026-12-23", "out_to": "2026-12-28",
         "ret_from": "2027-01-01", "ret_to": "2027-01-05",
         "buy_by_date": "2026-10-31", "target_total": 0, "active": True}


def series(totals, start_days_ago=None):
    """Bouwt een reeks van één observatie per dag, oudste eerst."""
    n = len(totals)
    start = start_days_ago if start_days_ago is not None else n - 1
    out = []
    for i, t in enumerate(totals):
        d = TODAY - timedelta(days=start - i)
        out.append({"at": f"{d.isoformat()}T09:00:00Z", "dest": "GRO", "total": t,
                    "out_day": "2026-12-24", "out_price": t / 2,
                    "ret_day": "2027-01-02", "ret_price": t / 2,
                    "options": [{"dest": "GRO", "total": t, "out_day": "2026-12-24",
                                 "out_price": t / 2, "ret_day": "2027-01-02",
                                 "ret_price": t / 2}]})
    return out


class TestAdvice(unittest.TestCase):

    def test_te_weinig_historie_geeft_wait_en_low(self):
        v = advice.evaluate(WATCH, series([300, 295, 290]), {}, TODAY)
        self.assertEqual(v["advice"], "WAIT")
        self.assertEqual(v["confidence"], "LOW")

    def test_dalende_reeks_met_historie_geeft_buy_want_dip(self):
        # 14 dagen dalend: de huidige prijs is de laagste ooit, dus een dip
        v = advice.evaluate(WATCH, series(list(range(400, 260, -10))), {}, TODAY)
        self.assertEqual(v["advice"], "BUY")
        self.assertTrue(v["new_low"])

    def test_hoge_prijs_na_lange_historie_geeft_wait(self):
        totals = [200, 205, 210, 215, 220, 225, 230, 235, 240, 245, 250, 255]
        v = advice.evaluate(WATCH, series(totals), {}, TODAY)
        self.assertEqual(v["advice"], "WAIT")
        self.assertGreater(v["percentile"], advice.DIP_PERCENTILE)

    def test_sprong_omhoog_geeft_buy(self):
        totals = [200, 202, 201, 203, 200, 202, 201, 203, 202, 240]
        v = advice.evaluate(WATCH, series(totals), {}, TODAY)
        self.assertEqual(v["advice"], "BUY")
        self.assertTrue(v["step_up"])

    def test_voorbij_deadline_geeft_altijd_buy(self):
        w = dict(WATCH, buy_by_date="2026-09-20")
        totals = [200, 210, 220, 230, 240, 250, 260, 270, 280, 300]
        v = advice.evaluate(w, series(totals), {}, TODAY)
        self.assertEqual(v["advice"], "BUY")

    def test_binnen_21_dagen_voor_vertrek_geeft_buy(self):
        w = dict(WATCH, out_from="2026-10-05", out_to="2026-10-08",
                 buy_by_date="2026-10-01")
        totals = [200, 210, 220, 230, 240, 250, 260, 270, 280, 300]
        v = advice.evaluate(w, series(totals), {}, TODAY)
        self.assertEqual(v["advice"], "BUY")

    def test_doelprijs_geeft_buy(self):
        w = dict(WATCH, target_total=260)
        v = advice.evaluate(w, series([300, 299, 298, 255]), {}, TODAY)
        self.assertEqual(v["advice"], "BUY")

    def test_lege_historie_crasht_niet(self):
        v = advice.evaluate(WATCH, [], {}, TODAY)
        self.assertEqual(v["advice"], "WAIT")
        self.assertIsNone(v["current_total"])

    def test_melding_alleen_bij_omslag(self):
        v = advice.evaluate(WATCH, series(list(range(400, 260, -10))), {}, TODAY)
        self.assertTrue(advice.notify_reasons(WATCH, v, {}, TODAY))
        self.assertFalse(advice.notify_reasons(
            WATCH, v, {"advice": "BUY", "min_ever": v["min_ever"]}, TODAY))


if __name__ == "__main__":
    unittest.main()
