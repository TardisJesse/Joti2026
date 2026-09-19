# CyberJoti – MTDF: spelcodes, teams, GPS en admin-games

Status: **gepland**  
Datum: 2026-09-19

## Doel

Vervang de speler-login met wachtwoord door een snelle start voor op het veld:

1. Een team voert een spelcode in.
2. Bestaat die spelronde nog niet, dan wordt zij aangemaakt.
3. Het team kiest een unieke teamnaam.
4. De telefoon is daarna als dat team actief in die spelronde en verschijnt op het scorebord.

Alleen admins blijven met een administratoraccount inloggen. Zij beheren spelrondes en objecten en zien de locaties van alle teams in de geselecteerde spelronde.

## Begrippen en regels

| Begrip | MVP-regel |
| --- | --- |
| Spelcode | Niet-hoofdlettergevoelige, korte code, bijvoorbeeld `RONDE-A`. Eén code wijst naar precies één spelronde. |
| Nieuwe spelronde | De eerste invoer van een nog onbekende geldige code maakt direct een open/actieve spelronde met die code. |
| Team | Een teamnaam is uniek binnen één spelronde. Dezelfde naam mag wel in een andere spelronde bestaan. |
| Eén telefoon per team | Het eerste apparaat ontvangt een willekeurig teamsessie-token in lokale opslag. Een tweede apparaat kan die teamnaam niet overnemen zolang de sessie actief is. Dit is een praktische MVP-beperking; het is geen waterdichte hardwareblokkade. |
| Speler | Heeft geen wachtwoord en kan alleen de eigen teamsessie, eigen score en eigen locatie zien. |
| Admin | Logt wel in, kiest een spelronde en kan die beheren. Een admin kan alle teamlocaties binnen die ene geselecteerde spelronde zien. |

## Spelerflow

### Startscherm

- Vervang het huidige speler-naam/wachtwoordformulier door een veld **Spelcode** en knop **Ga naar spel**.
- Bij een onbekende code maakt de API de spelronde aan en retourneert de ronde-id en status `RUNNING`.
- Bij een bekende code wordt dezelfde spelronde geopend.
- Toon vervolgens een veld **Teamnaam** en knop **Maak team aan / Doe mee**.
- Als de naam al door een actief team in die ronde gebruikt wordt, toon een begrijpelijke melding en vraag om een andere naam.
- Sla alleen een ondoorzichtig teamsessie-token op; sla geen wachtwoord of admin-token op in deze spelersflow.

### Na deelname

- Open direct het teamdashboard, scorebord en radarkaart voor deze spelronde.
- Laat de browser om locatietoestemming vragen zodra de teamweergave voor het eerst wordt geopend, met een duidelijke uitleg waarom.
- Bij toestemming: gebruik `navigator.geolocation.watchPosition` met hoge nauwkeurigheid, verstuur updates naar de API en centreer de kaart op de actuele positie.
- Bij weigering of fout: de app blijft bruikbaar, maar toont een duidelijke status en meldt dat locatie-afhankelijke opdrachten niet kunnen worden gevalideerd.

## Locatie- en kaartgedrag

- De telefoon is de bron van de teamlocatie; handmatig ingevoerde of statische kaartcoördinaten zijn geen vervanging voor GPS.
- De spelerkaart toont uitsluitend de eigen actuele positie, eigen objecten/opdrachten en de grenzen/radius die voor het spel nodig zijn.
- De adminkaart toont uitsluitend teams uit de geselecteerde spelronde, met teamnaam, laatste update en nauwkeurigheid.
- Locatie-updates en WebSocket-berichten krijgen altijd een `game_id`; locaties van andere spelrondes mogen nooit meekomen.
- Voeg een zichtbare status toe: `Locatie actief`, `Locatie wordt gezocht`, `Toestemming geweigerd` of `Verouderde locatie`.

## Adminflow

- Admins loggen in via de bestaande beveiligde admin-login; de spelerstart toont deze niet als primaire keuze, maar biedt een subtiele link **Admin login**.
- Voeg bovenaan de adminweergave een spelronde-kiezer toe met spelcode, naam en status.
- Een admin kan een spelronde kiezen, starten, pauzeren, beëindigen en naar een andere ronde wisselen.
- Alle adminacties voor objecten ontvangen expliciet het gekozen `game_id`; zij mogen niet meer afhankelijk zijn van één globale `active_game()`-zoekopdracht.
- Plaats een object altijd in de geselecteerde spelronde. Als nog geen ronde bestaat, toont de adminweergave een knop om er één aan te maken in plaats van `No game is currently running`.
- De admin-radarkaart toont locaties alleen van de geselecteerde spelronde.

## Backendwerk

- [ ] Voeg `game_code` toe aan `Game`, met unieke index en genormaliseerde opslag.
- [ ] Voeg een teamsessie-entiteit of sessie-token toe met `team_id`, `game_id`, apparaat-/sessie-id, aanmaak- en vervaltijd.
- [ ] Voeg endpoints toe voor spelcode opzoeken/aanmaken en team deelnemen/herstellen.
- [ ] Laat speler-endpoints autoriseren op teamsessie in plaats van gebruikerswachtwoord.
- [ ] Houd admin-JWT-autorisatie apart en ongewijzigd voor beheerfuncties.
- [ ] Geef iedere object-, score-, locatie- en WebSocket-query expliciet een `game_id`.
- [ ] Vervang globale actieve-game-afhankelijkheid in admin-objectcreatie door geselecteerde ronde-validatie.
- [ ] Maak een Alembic-migratie en behoud bestaande demo-/admingegevens waar mogelijk.

## Frontendwerk

- [ ] Bouw startscherm: spelcode, teamnaam, foutmeldingen en herstel van bestaande lokale teamsessie.
- [ ] Scheid speler- en adminnavigatie; toon admin-login alleen als secundaire route.
- [ ] Start GPS-watcher na deelname, toon toestemming/status en stuur locatie betrouwbaar door.
- [ ] Centreer de spelersradar op de echte GPS-locatie en toon geen andere teams.
- [ ] Voeg admin-spelronde-kiezer, rondebeheer en teamlocatielaag toe.
- [ ] Gebruik de geselecteerde admin-game voor objecten plaatsen, scores en kaartdata.
- [ ] Maak lege staten begrijpelijk: geen GPS, geen objecten, onbekende code, bezette teamnaam en geen geselecteerde ronde.

## Acceptatiecriteria

- [ ] Een speler kan zonder account of wachtwoord met `RONDE-A` starten, teamnaam `Valken` kiezen en op het scorebord verschijnen.
- [ ] Een tweede telefoon kan niet stilzwijgend `Valken` in `RONDE-A` overnemen.
- [ ] `RONDE-B` is volledig gescheiden van `RONDE-A`: teams, scores, objecten en locaties lekken niet tussen rondes.
- [ ] De browser vraagt om locatie en de spelerkaart volgt de werkelijke telefoonpositie na toestemming.
- [ ] Een speler ziet nooit locaties van andere teams.
- [ ] Een admin kan tussen rondes wisselen, alle teamlocaties van de gekozen ronde zien en objecten op die ronde plaatsen.
- [ ] Objecten plaatsen geeft nooit meer `No game is currently running`; de UI vraagt om een ronde te kiezen of aan te maken.
- [ ] Test op telefoon: code invoeren, team maken, GPS-toestemming, object in de buurt en scorebordupdate.

## Bouwvolgorde

1. Datamodel, migratie en spelcode/team-sessie API.
2. Spelerstart zonder wachtwoord en sessieherstel.
3. GPS-toestemming, echte kaartpositie en privacyfiltering.
4. Admin-gamekiezer en game-gebonden objectbeheer.
5. WebSocket/scorebord-scheiding per spelronde.
6. Mobiele veldtest met twee spelcodes, twee teams en een admin.

## Beveiligingsopmerking

Een spelcode is in deze MVP een deelnamesleutel, geen geheim. Voor een publiek evenement moeten admins sterke, unieke wachtwoorden gebruiken. De teamsessie is bewust beperkt tot één browser/apparaat en kan later worden uitgebreid met een organiser-reset of QR-overdracht.
