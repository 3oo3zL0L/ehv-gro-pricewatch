# Werkregels voor deze repo

Prijswacht voor vluchten vanaf Eindhoven. Historie opbouwen is het doel; zonder historie kan niets voorspellen.

## Harde regels

- **Vertrek is altijd EIN.** `ORIGIN` is een constante in `price_watch.py`. Maak er nooit een instelling van en voeg nooit een tweede vertrekvliegveld toe.
- **`data/prices.csv` is append-only.** Nooit regels wijzigen, herordenen of verwijderen, ook niet om op te schonen. Kolommen mogen alleen achteraan worden toegevoegd, nooit hernoemd.
- **Geen externe dependencies.** Alleen de Python standard library. De workflow doet geen `pip install` en dat moet zo blijven.
- **Reizen horen in `config/watches.json`,** drempels in `advice.py` als constante bovenin. Nooit datums of prijzen hardcoderen in de logica.
- **Bestanden onder de 250 regels.** Deze repo wordt via de GitHub-webinterface bewerkt; grote bestanden werken daar slecht.
- **Elke wijziging in `advice.py` krijgt een testcase** in `tests/test_advice.py`. Tests draaien met `unittest`, niet met pytest.
- **Falen per bestemming is geen reden om de run te laten falen.** Een bestemming zonder route wordt gelogd en overgeslagen.

## Indeling

| Bestand | Verantwoordelijkheid |
|---|---|
| `price_watch.py` | ophalen, loggen, melden |
| `advice.py` | features en de koop-of-wacht beslissing |
| `report.py` | REPORT.md opmaken |
| `config/watches.json` | welke reizen gevolgd worden |
| `tests/test_advice.py` | beslislogica |

## Bij het aanpassen van het advies

Zeg in de commit message welke regel is veranderd en waarom. Het advies moet altijd een reden in gewoon Nederlands meegeven; een advies zonder uitleg is niet af.
