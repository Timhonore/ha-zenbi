# Zenbi til Home Assistant

<img src="custom_components/zenbi/brand/icon.png" alt="Zenbi" width="96">

[![Validate](https://github.com/Timhonore/ha-zenbi/actions/workflows/validate.yml/badge.svg)](https://github.com/Timhonore/ha-zenbi/actions/workflows/validate.yml)

**Version 0.1.0-beta.2 — uofficiel integration og første testversion.**

Henter lektier, opgaver, ugeplaner, kalender, beskeder og opslag fra den konto,
du selv har adgang til på `app.zenbi.dk`. Installeres gennem HACS som et custom
repository: **https://github.com/Timhonore/ha-zenbi**.

## Installer gennem HACS

1. Åbn **HACS → menuen med tre prikker → Custom repositories**.
2. Indsæt `https://github.com/Timhonore/ha-zenbi`, og vælg **Integration**.
3. Find **Zenbi**, download integrationen og genstart Home Assistant.
4. Tilføj **Zenbi** under **Indstillinger → Enheder og tjenester**.
5. Log ind og vælg børnene.

Zenbis officielle appikon er inkluderet. Lokale brandikoner vises i Home
Assistant fra version 2026.3; tidligere versioner kan vise standardikon.

## Zenbi Card

Et kort uden ekstra card-afhængigheder, med Zenbis ikon, lys/mørk tilstand,
børnevælger, lektier og opgaver, syvdageskalender, beskeder, ugeplaner og
opslag. Tryk på et element for at folde teksten ud. Børn og entiteter findes
fra HA's entitetsregister; du behøver ikke kende deres entity-id'er.

**Installér kortet:**

1. Opdater Zenbi til **0.1.0-beta.2** i HACS og genstart HA.
2. Aktivér avanceret tilstand på din HA-profil, hvis Ressourcer ikke vises.
3. Åbn **Indstillinger → Dashboards → ⋮ → Ressourcer** og tilføj
   `/zenbi-card/zenbi-card.js?v=0.1.0-beta.2` som **JavaScript Module**.
4. Genindlæs dashboardet. Tilføj kortet **Zenbi · Skoleoverblik**, eller
   indsæt YAML nedenfor som et manuelt kort.

```yaml
type: custom:zenbi-card
title: Familiens skoleoverblik
max_items: 5
show_posts: true
```

Card-filen følger med integrationens HACS-download. Den kræver en opsat Zenbi-
integration for at kunne vises på `/zenbi-card/`. Resource tilføjes én gang;
ved kommende opdateringer skal versionsparameteren ændres for at undgå gammel
browsercache. Kortet kan konfigureres i den visuelle editor (titel, konto,
antal rækker og opslag). Har du flere Zenbi-konti, vælg konto i editoren.
For YAML-dashboards tilføjes URL'en under Lovelaces `resources` med `type: module`.

![Zenbi Card — syntetiske demodata](docs/images/zenbi-card-light.png)

Beskeder og opslag er fælles for kontoen, også når et barn er valgt. Ugeplaner
for **Alle børn** samles uden dubletter. Ukendte/utilgængelige kilder vises som
manglende data; kortet tolker dem ikke som nul. Kalenderen hentes gennem HA's
kalender-API, uden at kortet får adgang til Zenbi-tokens. Opdater-knappen
kalder integrationens eksisterende opdatering. Kortet markerer ikke beskeder
læst og indeholder ingen automatiske notifikationer.

### Manuel binding af entiteter

Hvis entitetsregisteret ikke er tilgængeligt, eller du vil styre indholdet,
kan du angive egne entiteter. Erstat eksemplerne med dine faktiske id'er:

```yaml
type: custom:zenbi-card
title: Familiens skoleoverblik
homework_entity: sensor.zenbi_alle_lektier
tasks_entity: sensor.zenbi_alle_opgaver
calendar_entity: calendar.zenbi_kalender
messages_entity: sensor.zenbi_beskeder
unread_entity: sensor.zenbi_ulaeste_beskeder
posts_entity: sensor.zenbi_opslag
status_entity: sensor.zenbi_datastatus
update_entity: button.zenbi_opdater
children:
  - name: Barn 1
    homework_entity: sensor.zenbi_barn_1_lektier
    tasks_entity: sensor.zenbi_barn_1_opgaver
    weekly_plans_entity: sensor.zenbi_barn_1_ugeplaner
    calendar_entity: calendar.zenbi_barn_1_kalender
```

Browserprøver bruger syntetiske data: automatisk entitetsvalg, børnefiltrering,
kalender, udfoldning, HTML-escaping, utilgængelige kilder, editor og mobilbredde.
Screenshots viser demodata. Kortet skal stadig prøves med din faktiske HA-instans.

## Hvad er testet?

- Login og adgang til forældrevisningerne blev bekræftet i Zenbis webapp.
- API-ruter, HTTP-metoder, loginfelter, tokenfornyelse, samlinger, tilknytning
  via grupper og kalendergentagelser er kortlagt fra offentlig JavaScript
  leveret af webappen den 11. oktober 2026.
- 21 automatiske tests med kunstige data er bestået: tokenfornyelse, HTTP-fejl,
  gruppefiltrering, tekstkonvertering, gentagelser, flytninger, sommertid og
  delvise kildefejl.
- Python-filer er syntakskontrolleret.

**Ikke testet endnu:** direkte autentificerede API-svar gennem denne klient,
installation i en rigtig HA-instans og HA's fulde config flow.
Brugerfladeadgang er ikke en end-to-end-test af integrationskoden. API-svar kan
kræve tilpasning ved første installation. Automatiske HACS- og hassfest-checks
kører på GitHub; se repositoryets Actions-side for deres aktuelle status.

## Installer første testversion manuelt

1. Pak ZIP-filen ud.
2. Kopiér mappen `custom_components/zenbi` til `/config/custom_components/zenbi`
   på din Home Assistant. Opret `custom_components`, hvis den mangler.
3. Genstart Home Assistant.
4. Åbn **Indstillinger → Enheder og tjenester → Tilføj integration → Zenbi**.
5. Indtast din Zenbi-mail og adgangskode i HA-dialogen.
6. Vælg organisation/skole, hvis kontoen har flere.
7. Vælg de børn/relationer, der skal oprettes entiteter for.

Integrationen gemmer adgangstoken og refresh-token i HA's config entry; den
gemmer ikke adgangskoden. Hvis Zenbi afviser eller udløber refresh-tokenet,
beder HA om nyt login. Tokens er følsomme og indgår i normale HA-backups.

## Entiteter

| Entitet | Indhold |
| --- | --- |
| Ulæste beskeder | Antal ulæste element-id'er fra Zenbi |
| Beskeder | Antal i den hentede side (højst 50), tekst i `items` |
| Opslag | Tilgængelige opslag i den hentede periode, tekst i `items` |
| Alle lektier / Alle opgaver | Daterede elementer fra i dag og frem |
| Lektier / Opgaver pr. barn | Filtreres på barnets id og grupper |
| Ugeplaner pr. barn | Tilgængelige planer i den hentede periode |
| Kalender | Kontoens kalender som HA-kalender |
| Kalender pr. barn | Kalender filtreret på barnets id og grupper |
| Lektiefrister pr. barn | Lektier som heldagsaftaler; opgaver ved fristen |
| Datastatus | `ok` eller `delvis`, med status for hver kilde |
| Opdater | Henter en ny opdatering |

HA tildeler selv entity-id'er. Find de faktiske id'er under integrationens
entiteter. Tekstdata ligger i attributten `items`; teksten er begrænset til
4.000 tegn pr. element og højst 50 elementer pr. sensor for at begrænse
størrelsen på HA's tilstande. Længere tekst findes fortsat i Zenbi.

Standardintervallet er 15 minutter. Under integrationens indstillinger kan
du vælge 5–120 minutter og 7–90 dage frem. Standardperioden er 30 dage frem
og 2 dage tilbage; opslag hentes yderligere 30 dage tilbage. Ved en
server-rategrænse øges intervallet midlertidigt til mindst 30 minutter.
**Genkonfigurer** kan ændre relationerne. Gamle entiteter, som ikke længere
oprettes, kan bagefter fjernes manuelt fra entitetsregisteret.

## Første test i HA

1. Tjek at begge børn kan vælges under opsætningen.
2. Find sensoren **Datastatus**. I attributten `datakilder` skal hver kilde
   vise `ok`. En fejl får den berørte entitet til at blive utilgængelig.
3. Sammenlign ulæsttal, ugeplan og en kendt lektie med Zenbis webapp.
4. Sammenlign en kendt kalenderaftale og en gentagelse.
5. Tryk **Opdater** og kontrollér `senest_opdateret`.

Hvis en kilde viser `SchemaError`, `PermissionError` eller en anden fejl,
download integrationens **Diagnostik** og brug den til fejlretning. Diagnostik
indeholder kun kilde-status og antal; den indeholder ikke adgangskoder,
tokens, navne, identifikatorer, beskedtekster eller lektietekster. Upload ikke
config entries, HAR-filer eller rå netværkslogger med loginoplysninger.

Hvis tilknytning til et barn ikke kan bevises, vises barnets sensor som
utilgængelig; den samlede liste og tallet `uden_barnetilknytning` hjælper med
at finde datamodellen uden at vise et misvisende nul.

## Begrænsninger i denne beta

- Totrinslogin/passkeys understøttes endnu ikke i HA-dialogen. Hvis Zenbi
  kræver det, stopper opsætningen med en forklarende besked.
- Beskeder er den første API-side (op til 50), ikke hele historikken. Tallet
  er antal hentede beskedrækker, ikke nødvendigvis antal tråde.
- Ulæsttallet er antal id'er fra Zenbi og kan omfatte svar/kommentarer.
- Daglige og ugentlige gentagelser med trin, antal og flytninger understøttes.
  Andre frekvenser bliver meldt som en schemafejl. Månedlige gentagelser var
  heller ikke implementeret i den undersøgte webapp-generator.
- Lektiefrist-kalenderen bruger den hentede periode; forespørgsler udenfor
  perioden får en forklarende fejl. Almindelige kalendere kan hente andre
  perioder direkte.
- Fødselsdage, fravær, vedhæftede filer og svar/tilmeldinger er ikke hentet i
  denne version. Der medtages kun antal vedhæftninger, hvor API'et leverer det.
- API'et er reverse-engineeret fra webappen og kan ændre sig.
- Ingen automatiske notifikationer aktiveres ved installationen. Eksempler
  på dashboard og notifikation ligger i `examples/`.

Dataoperationerne er GET-kald. Der kaldes ikke skrive-endpoints for at markere
beskeder læst, sende beskeder, redigere lektier eller oprette aftaler.

## Læg på GitHub og tilføj i HACS

1. Opret et GitHub-repository, fx `ha-zenbi`.
2. Opdater manifestets repositoryoplysninger med dit virkelige GitHub-navn:
   `python scripts/prepare_repository.py --repo DIT_BRUGERNAVN/ha-zenbi`
3. Læg **indholdet af denne mappe** i repositoryets rod. Mappen
   `custom_components/zenbi` og `hacs.json` skal ligge direkte i roden.
4. Kør HACS- og hassfest-validering og ret eventuelle krav, før udgivelse.
   GitHub-workflowet i `.github/workflows/validate.yml` er inkluderet.
5. En release med tag `v0.1.0-beta.2` er valgfri; HACS kan hente fra `main`.
6. I HACS: **Custom repositories / Brugerdefinerede repositories**, tilføj
   repositoryets URL, vælg **Integration**, og installer Zenbi.

Manifestets dokumentationslink, issue-link og codeowner er konfigureret til
`Timhonore/ha-zenbi`. Dette er ikke en integration, som Zenbi har udgivet eller godkendt.

HACS-workflowet kontrollerer integrationspakken, manifest, branding og øvrige
installationskrav. Kontrollerne af GitHub-beskrivelse og topics er undtaget,
da denne beta installeres som et custom repository. GitHub-connectoren kan
ikke ændre disse repositoryindstillinger. Før en ansøgning om optagelse i
HACS' standardkatalog skal en beskrivelse og topics tilføjes i GitHubs
**About**, fx `home-assistant`, `hacs`, `zenbi`, og undtagelserne fjernes.

## Udvikling

Python 3.12+, `aiohttp` til klienttests:

```bash
python -m unittest discover -s tests -v
python -m compileall -q custom_components scripts
```

Testene bruger syntetiske skoledata og lette HA-interface-doubles. En rigtig
HA-test og autentificerede API-tests skal supplere dem før en stabil release.

Se `docs/API_NOTES.md` for de observerede kontrakter og åbne spørgsmål.
