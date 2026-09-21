# ehv-pricewatch

Prijswacht voor vluchten **vanaf Eindhoven (EIN)**. Logt Ryanair-prijzen, bewaart de volledige historie en zegt of je nu moet kopen of nog kunt wachten.

Kijk in [REPORT.md](REPORT.md) voor de actuele stand.

## Hoe het werkt

Elke 2 uur draait GitHub Actions `price_watch.py`. Dat script:

1. leest `config/watches.json`
2. haalt per watch en per bestemming de goedkoopste heen- en terugprijs per dag op bij de Ryanair farfnd-API
3. schrijft elke waarneming weg in `data/prices.csv` (append-only)
4. laat `advice.py` bepalen of het koopmoment daar is
5. schrijft `REPORT.md`
6. stuurt een ntfy-push, maar alleen als er iets is gebeurd

## Vertrekvliegveld

Vertrek staat hard op **EIN**. Dat is een constante in `price_watch.py`, geen instelling. Zet je de omgevingsvariabele `ORIGIN` op iets anders, dan stopt het script met een foutmelding. Dit is opzettelijk: geen prijzen van Schiphol, Weeze, Dusseldorf of Brussel.

## Een reis toevoegen of wijzigen

Alles staat in `config/watches.json`. Code aanpassen is niet nodig.

```json
{
  "id": "kerst2026",
  "dests": ["GRO", "BCN", "PGF", "CCF"],
  "out_from": "2026-12-23", "out_to": "2026-12-28",
  "ret_from": "2027-01-01", "ret_to": "2027-01-05",
  "buy_by_date": "2026-10-31",
  "target_total": 0,
  "active": true
}
```

| Veld | Betekenis |
|---|---|
| `id` | unieke naam, komt terug in prices.csv en in de meldingen |
| `dests` | IATA-codes van de bestemmingen die het script vergelijkt |
| `out_from` / `out_to` | venster waarbinnen de heenvlucht mag vallen |
| `ret_from` / `ret_to` | venster waarbinnen de terugvlucht mag vallen |
| `buy_by_date` | je eigen deadline, hierna adviseert het script altijd kopen |
| `target_total` | retourprijs waaronder je sowieso een melding wilt, 0 is uit |
| `active` | op `false` zetten pauzeert de watch zonder hem weg te gooien |

Heen- en terugvlucht worden altijd per bestemming gecombineerd. Je krijgt dus nooit een heenvlucht naar Girona met een terugvlucht uit Barcelona.

Vanaf Eindhoven vliegt Ryanair naar GRO en BCN. PGF en CCF worden niet direct bediend en verschijnen in het rapport als "geen directe route". Ze staan er bewust in, zodat je het meteen ziet als daar een route bij komt.

## data/prices.csv

Append-only. Nooit een regel wijzigen of verwijderen; dit is het enige wat het adviesmodel voedt.

| Kolom | Betekenis |
|---|---|
| `observed_at_utc` | tijdstip van de meting, gelijk voor alle regels uit één run |
| `watch_id` | naar welke watch deze regel hoort |
| `leg` | `out` of `ret` |
| `origin` / `dest` | werkelijke richting van deze vlucht |
| `flight_date` | vertrekdatum van de vlucht |
| `price_eur` | enkele reis in euro |
| `dep` / `arr` | vertrek- en aankomsttijd |
| `days_to_flight` | dagen tussen meting en vluchtdatum |

## Het advies

Ryanair-prijzen stijgen vrijwel altijd naarmate stoelen vollopen. Dit is dus een dip-jager met een deadline, geen wacht-optimalisator.

**KOPEN** zodra een van deze waar is:

- minstens 7 dagen historie en de prijs zit in het goedkoopste kwintiel van alles wat je gezien hebt
- de prijs sprong meer dan 8% omhoog sinds de vorige meting; dan is een fare bucket volgelopen en komt die prijs niet terug
- `buy_by_date` is bereikt
- nog 21 dagen of minder tot vertrek; daaronder zijn de goedkope fare classes weg
- `target_total` is geraakt

**WACHTEN** in alle andere gevallen.

Het vertrouwen staat op LOW onder 7 dagen historie, MED tot 21 dagen en HIGH daarboven. De eerste week zegt het advies weinig; dat is de prijs van historie opbouwen.

## Instellen

- Repo-secret `NTFY_TOPIC` met de naam van je ntfy-topic, niet de hele URL. Kies een lange willekeurige naam: ntfy-topics zijn niet beveiligd en iedereen die de naam kent leest mee.
- Settings → Actions → General → Workflow permissions op "Read and write permissions", anders kan de bot de historie niet terugcommitten.

Handmatig draaien kan via Actions → Prijswacht EIN → Run workflow, met "Stuur altijd een testmelding" aan om de push te testen.

## Tests

```
python -m unittest discover -s tests
```

Draait ook automatisch bij elke workflow-run, vóór de prijscheck.
