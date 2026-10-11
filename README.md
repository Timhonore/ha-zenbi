# Zenbi til Home Assistant

<img src="custom_components/zenbi/brand/icon.png" alt="Zenbi" width="96">

**Version 0.1.0-beta.1 — uofficiel integration og første testversion.**

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
5. Opret en release med tag `v0.1.0-beta.1`.
6. I HACS: **Custom repositories / Brugerdefinerede repositories**, tilføj
   repositoryets URL, vælg **Integration**, og installer Zenbi.

Manifestets dokumentationslink, issue-link og codeowner er konfigureret til
`Timhonore/ha-zenbi`. Dette er ikke en integration, som Zenbi har udgivet eller godkendt.

## Udvikling

Python 3.12+, `aiohttp` til klienttests:

```bash
python -m unittest discover -s tests -v
python -m compileall -q custom_components scripts
```

Testene bruger syntetiske skoledata og lette HA-interface-doubles. En rigtig
HA-test og autentificerede API-tests skal supplere dem før en stabil release.

Se `docs/API_NOTES.md` for de observerede kontrakter og åbne spørgsmål.
