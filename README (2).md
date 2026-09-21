# Prijswacht Eindhoven - Girona (Ryanair)

Deze tool checkt 3x per dag de goedkoopste Ryanair-prijs per dag:

* Heen: Eindhoven (EIN) naar Girona (GRO), 24 t/m 28 december 2026
* Terug: Girona (GRO) naar Eindhoven (EIN), 1 t/m 4 januari 2027

Je krijgt een pushmelding op je telefoon als:

1. een prijs op een van die dagen daalt, of
2. het goedkoopste retourtotaal onder jouw doelprijs komt (optioneel).

Alles draait gratis in GitHub. Je computer hoeft niet aan te staan.

\---

## Deel 1: Installatie

### Stap 1. Pushmeldingen instellen (ntfy)

1. Installeer de app **ntfy** uit de App Store of Google Play.
2. Open de app en tik op **+** (nieuw abonnement).
3. Verzin een topicnaam die niemand kan raden, bijvoorbeeld `thomas-ehv-gro-8k2p`.
Iedereen die de naam kent kan je meldingen lezen, dus kies iets willekeurigs.
4. Laat de server op `ntfy.sh` staan en tik op **Subscribe**.
5. Schrijf de topicnaam op. Die heb je in stap 4 nodig.

### Stap 2. GitHub-account en repository

1. Ga naar https://github.com en maak een gratis account aan (of log in).
2. Klik rechtsboven op **+** en kies **New repository**.
3. Vul in:

   * Repository name: `ehv-gro-prijswacht`
   * Zet hem op **Private**
   * Vink **Add a README file** aan
4. Klik **Create repository**.

### Stap 3. Bestanden toevoegen

De map `.github` is op Windows en Mac vaak onzichtbaar, daarom maak je dat bestand handmatig aan.

**3a. Het script uploaden**

1. Klik in je repository op **Add file** en kies **Upload files**.
2. Sleep `price\_watch.py` in het venster.
3. Sleep ook deze `README.md` erin (die vervangt de lege README).
4. Klik onderaan op **Commit changes**.

**3b. Het workflow-bestand aanmaken**

1. Klik op **Add file** en kies **Create new file**.
2. Typ als bestandsnaam precies: `.github/workflows/price-watch.yml`
(bij elke `/` maakt GitHub automatisch een map aan).
3. Open `price-watch.yml` uit de zip in Kladblok, kopieer alles en plak het in GitHub.
4. Klik **Commit changes** en nog een keer **Commit changes** in het venster dat verschijnt.

Controle: je repository toont nu `price\_watch.py`, `README.md` en een map `.github`.

### Stap 4. Je topic en doelprijs invullen

1. Ga in je repository naar **Settings** (tabblad bovenaan).
2. Klik links op **Secrets and variables** en dan **Actions**.
3. Tabblad **Secrets**: klik **New repository secret**

   * Name: `NTFY\_TOPIC`
   * Secret: je topicnaam uit stap 1 (bijv. `thomas-ehv-gro-8k2p`)
   * Klik **Add secret**
4. Tabblad **Variables** (optioneel): klik **New repository variable**

   * Name: `TARGET\_TOTAL`
   * Value: je doelprijs voor heen + terug in euro, zonder euroteken, bijv. `120`
   * Klik **Add variable**

### Stap 5. Schrijfrechten controleren

De tool slaat na elke run de laatste prijzen op in `state.json`. Daarvoor heeft hij schrijfrechten nodig.

1. **Settings** > links **Actions** > **General**.
2. Scroll naar **Workflow permissions**.
3. Kies **Read and write permissions** en klik **Save**.

De installatie is klaar. Ga door naar Deel 2 om te testen.

\---

## Deel 2: Testen of het werkt

Doe de tests in deze volgorde. Elke test controleert een schakel.

### Test 1. Komen meldingen aan op je telefoon?

Dit test alleen ntfy, los van GitHub.

1. Open op je computer `https://ntfy.sh/JOUW-TOPICNAAM` in de browser.
2. Typ onderaan een bericht, bijvoorbeeld `hallo`, en klik op verzenden.
3. **Geslaagd** als je binnen een paar seconden een melding op je telefoon krijgt.
4. **Niet geslaagd?** Controleer of de topicnaam precies gelijk is (hoofdletters tellen mee) en of meldingen voor de ntfy-app aan staan in je telefooninstellingen.

### Test 2. Draait de workflow en bereikt hij Ryanair?

1. Ga in je repository naar het tabblad **Actions**.
Zie je een melding over workflows inschakelen? Klik op de groene knop om ze te activeren.
2. Klik links op **Prijswacht EHV-GRO**.
3. Klik rechts op **Run workflow**, laat het vinkje uit en klik op de groene **Run workflow**.
4. Ververs na 10 seconden de pagina. Er verschijnt een run met een geel bolletje (bezig).
5. Wacht tot het bolletje groen is (meestal onder 1 minuut).

**Geslaagd als:**

* het bolletje groen is,
* je een melding krijgt met de titel **"Prijswacht EIN-GRO gestart"** en de huidige goedkoopste prijzen,
* er in je repository een nieuw bestand `state.json` staat.

**De prijzen zelf controleren:** klik op de run, dan op **check**, dan op de stap **Prijzen checken**. Je ziet de goedkoopste heen- en terugvlucht. Vergelijk die met ryanair.com voor dezelfde datum. Het bedrag moet gelijk zijn aan het laagste tarief van die dag.

**"Nog geen prijzen beschikbaar"?** Dan staan die data nog niet in de verkoop. Ryanair toont prijzen ongeveer 6 maanden vooruit. De koppeling werkt wel; zodra de vluchten in de verkoop gaan, verschijnen de prijzen vanzelf.

### Test 3. Werkt de testknop?

1. **Actions** > **Prijswacht EHV-GRO** > **Run workflow**.
2. Zet nu het vinkje **Stuur altijd een testmelding** aan en klik **Run workflow**.
3. **Geslaagd** als je een melding krijgt met de titel **"TEST prijswacht EIN-GRO"**.

Deze knop kun je later altijd gebruiken om te checken of alles nog draait.

### Test 4. Wordt een prijsdaling herkend?

Je doet alsof de prijs gisteren hoger was, zodat de tool een daling ziet.

1. Open `state.json` in je repository en klik op het potloodje (bewerken).
2. Zoek bij `"out"` een datum met een prijs, bijvoorbeeld:

```
   "price": 64.99,
   ```

3. Verhoog dat bedrag met bijvoorbeeld 50: `"price": 114.99,`
4. Klik **Commit changes**.
5. Start de workflow opnieuw (zonder testvinkje).
6. **Geslaagd** als je een melding krijgt met de titel **"Prijsdaling EIN-GRO"** en de regel `€114.99 → €64.99`.

Na deze run zet de tool `state.json` automatisch terug naar de echte prijzen. Je hoeft niets op te ruimen.

Werkt test 4 niet omdat `state.json` nog geen prijzen bevat? Dan zijn de vluchten nog niet in de verkoop. Herhaal deze test later.

### Test 5. Draait hij automatisch?

1. Wacht een dag.
2. Kijk in **Actions**. Je ziet runs met het label **schedule** rond 07:00, 13:00 en 19:00 Nederlandse tijd.
3. **Geslaagd** als die runs groen zijn. Zonder prijsdaling krijg je geen melding; dat is correct.

GitHub start geplande runs soms 10 tot 30 minuten later dan gepland. Dat is normaal.

\---

## Problemen oplossen

|Wat zie je|Oorzaak|Oplossing|
|-|-|-|
|Rood kruis, in de log `HTTP Error 403` of `429`|Ryanair blokkeert het verzoek tijdelijk|Nog een keer proberen. Blijft het rood, laat het weten, dan pas ik het script aan|
|Rood kruis bij stap **Laatste prijzen opslaan**, `Permission denied`|Geen schrijfrechten|Deel 1, stap 5|
|Workflow groen, maar geen melding|Topicnaam klopt niet of secret ontbreekt|Controleer `NTFY\_TOPIC` in Settings en doe test 1 opnieuw|
|**Prijswacht EHV-GRO** staat niet links in Actions|Workflow-bestand staat op de verkeerde plek|Het pad moet exact `.github/workflows/price-watch.yml` zijn|
|Geen geplande runs meer|GitHub pauzeert schema's na 60 dagen zonder activiteit|In Actions op **Enable workflow** klikken|

\---

## Aanpassen

Open `price\_watch.py`, klik op het potloodje en wijzig bovenin:

|Instelling|Betekenis|Standaard|
|-|-|-|
|`OUT\_FROM` / `OUT\_TO`|Eerste en laatste dag heenreis|2026-12-24 / 2026-12-28|
|`RET\_FROM` / `RET\_TO`|Eerste en laatste dag terugreis|2027-01-01 / 2027-01-04|
|`ORIGIN` / `DEST`|Luchthavencodes|EIN / GRO|

Andere route, bijvoorbeeld Charleroi-Perpignan: `CRL` en `PGF`.
Na een wijziging van route of data: verwijder `state.json`, anders vergelijkt hij met oude prijzen.

Hoe vaak hij checkt, pas je aan in `.github/workflows/price-watch.yml` bij `cron`. Tijden zijn in UTC (Nederlandse wintertijd = UTC + 1).

## Goed om te weten

* Prijzen zijn per persoon, basistarief zonder bagage of stoelkeuze.
* De tool gebruikt de publieke prijskalender van Ryanair. Die is onofficieel en kan zonder aankondiging veranderen.
* De tool boekt niets. Tik op de melding om direct naar Ryanair te gaan.

