# API-kortlægning, 11. oktober 2026

Observationer stammer fra offentlig frontendkode på `https://app.zenbi.dk`
og en brugerautoriseret forældrevisning i browseren. Der er ingen persondata,
adgangskoder eller sessionsoplysninger i dette repository.

## Login

- POST `/api/authentication/api/v1/account/authenticate`
- Felter: `username`, `password`, `uniqueDeviceId`, `organizationId`,
  `twoFactorType`. Frontendens "ukendt" totrinstype er nul-GUID.
- Svar kan indeholde `token`, `refreshToken`, `error`, `organizations`,
  `twoFactorAuthentication` eller `changePassword`.
- Organisationsvalg: POST `/api/authentication/api/v1/account/swap`, med
  `uniqueDeviceId`, `tempToken`, `twoFactorType`.
- Fornyelse: POST `/api/authentication/api/v1/account/refresh-token`, med
  `token`, `refreshToken`.
- Token er Bearer-token. JWT-payload bruger `usr`, `org`, `rel`, `exp`.
  GUID'er kan være base92-kodede; `rel` er par af relationstype og person-id.
- Intet autentificeret HTTP-svar er endnu verificeret i integrationsklienten.

## Data

| Formål | GET-rute | Forventet form fra frontendens handler |
| --- | --- | --- |
| Grupper og navne | `/api/authentication/api/v1/globaldata` | `groupModelTimeFrames`, `userModelTimeFrames`, `meInfo` |
| Skole | `/api/organisation/api/v1/organisation` | `organisationModel` |
| Lektier | `/api/calendar/api/v1/homeworks/relations` | Liste med bl.a. `calendarItemId`, `date`, `description` |
| Opgaver | `/api/homework/api/v1/homework/tasks/relations` | `homeworkTasks`, `recipients`, `recipientGroups`, `corrects` |
| Ugeplaner | `/api/homework/api/v1/weeklyschedules/relations` | Liste med `participantIds`, `start`, `end`, `description` |
| Egen kalender | `/api/calendar/api/v1/calendaritems/own/dates` | Liste med `start`, `end`, `onlyDate`, `participantModels`, evt. `repetition` |
| Relationskalender | `/api/calendar/api/v1/calendaritems/own/relation/users` | Samme kalenderform |
| Beskeder | `/api/message/api/v1/messageitems` | `messageParents`, `messageChilds`, `paginationKey` og relaterede samlinger |
| Ulæste id'er | `/api/message/api/v1/messageitem/unread/ids` | Liste af id-strenge |
| Opslag/dagbog | `/api/diary/api/v1/diary/relations` | `diaries` og relaterede samlinger |

Lektier/ugeplaner/kalender/opgaver bruger `start` og `end` i query.
Dagbog/opslag bruger **`starttime` og `endtime`**. Beskeder bruger `take` og
eventuelt `paginationKey`; denne beta henter kun første side. Arrayparametre
sendes som gentagne queryparametre i frontendens generelle HTTP-klient.

## Relationer

- Personer identificeres ud fra JWT's relationer; brugeren vælger relevante
  relationer i HA under opsætningen.
- Navne ligger som personfelter i `userMetadata`, med faste felt-GUID'er.
  Kun navne og skoleklasse medtages i integrationsdata.
- `groupModelTimeFrames[].users` giver gruppetilknytning.
- Kalenderdeltagere kan være grupper eller person-id'er.
- Lektier refererer til en kalenderaftale, hvis deltagere giver barnetilknytning.
- Opgavernes `recipients[].recipientIds` knyttes via `homeworkTaskId`.
- Ugeplanernes `participantIds` knyttes direkte eller gennem grupper.

## Åbne spørgsmål, som første HA-test skal afklare

1. Er alle de forventede samlinger tilgængelige på forældrekontoen?
2. Er organisationsnavnet inkluderet i loginudfordringen, eller skal det hentes?
3. Skal et `timeframeId` tilføjes på nogle kald ved andre skolers opsætning?
4. Er al lektietekst i `description`, eller findes skolespecifikke felter?
5. Er opslagssamlingen kun skoleopslag eller også andre diary-typer?
6. Er første beskedside sorteret og grupperet som forventet?
7. Skal afleveringsstatus fra `corrects`/assignment-samlinger indgå?
8. Skal fravær, fødselsdage, tilmeldinger og dokumenter tilføjes som egne kilder?

Dokumentation til HA/HACS:

- https://developers.home-assistant.io/docs/core/integration/config_flow/
- https://developers.home-assistant.io/docs/integration_fetching_data/
- https://developers.home-assistant.io/docs/core/entity/calendar/
- https://www.hacs.xyz/docs/publish/integration/

Beta.3: Første HA-diagnostik viste kun posts=PermissionError (HTTP 403);
øvrige syv kilder var ok. Offentlig diary-store definerer postsRelations
på /diary/relations med starttime/endtime og samme diaries-samling.
Den tidligere /diary/dates-rute beholdes ikke som fallback ved en afvisning.

## Profilbilleder (12. oktober 2026)

Offentlig `global-DcdiRgVK.js` definerer billedfeltet
`c4c7bc12-045d-462e-8acb-af5533f670fb` (`imageUrl`). Frontendens handlers
bygger billedstien `https://zenbistore.blob.core.windows.net/profile-photos/`
+ organisationens id + `/` + feltets filnavn. Integrationen læser kun
valgte relationers ukoblede billedmetadata; direkte billedvisning mangler live-test.
