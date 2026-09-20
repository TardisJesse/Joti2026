# Telefoonmeldingen voor captures

De app verstuurt na een bevestigde capture een melding naar alle ingeschreven spelers in dezelfde ronde. De service worker ontvangt ook wanneer de website gesloten is. Een WebSocket-bericht toont daarnaast direct een banner in de geopende app.

## Railway activeren

1. Push de code; de backend moet bij starten `alembic upgrade head` uitvoeren. Migratie 0003 verdeelt bestaande teams over unieke kleuren per ronde; 0004 voegt pushabonnementen toe.
2. Genereer eenmalig sleutels op je eigen computer (uitvoer bevat een geheim):

   ```sh
   docker compose run --rm --no-deps backend python scripts/generate_push_keys.py
   ```

3. Zet de uitvoer als backend Railway-variabelen: `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_SUBJECT`. Vervang de voorbeeldwaarde bij SUBJECT door `mailto:` plus je eigen contactadres. Bewaar de sleutels; vervanging maakt opnieuw inschrijven noodzakelijk. Commit deze waarden nooit.
4. Herstart de backend. Er zijn geen frontend-buildvariabelen nodig; de publieke sleutel komt van `/api/push/config`.
5. Spelers kiezen op het dashboard **Telefoonmeldingen inschakelen** en geven toestemming. Op iPhone/iPad eerst via Safari toevoegen aan het beginscherm en vanuit dat icoon openen. Zie [WebKit](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/).
6. Test met twee teams in dezelfde ronde en een derde team in een andere ronde. Sluit de website van team 2, verover een punt met team 1. Team 2 hoort de telefoonmelding te krijgen, team 3 niet.

## Grenzen en status

- Zonder VAPID-variabelen blijven captures en meldingen in de app werken; het dashboard meldt dat telefoonmeldingen nog niet ingesteld zijn.
- Toestemming en ondersteuning door het apparaat zijn noodzakelijk; levering is afhankelijk van browser/pushprovider en internet.
- Uitschakelen/uitloggen verwijdert de serverinschrijving; vervallen abonnementen (404/410) worden opgeruimd.
- Verwijderen van spelpunten is uitschakelen: punten verdwijnen voor spelers, bestaande scores blijven behouden.
- Capturevoortgang en WebSocket-kanalen gebruiken de bestaande enkele backend-instance. Capturepolling stopt wanneer de veroverende speler de app sluit. Web Push kan wel andere spelers met een gesloten app bereiken na bevestigde afronding.
- Pushverzending is een achtergrondtaak, zonder duurzame wachtrij/retry bij een backendherstart.
- [ ] Railway-variabelen ingesteld en echte pushlevering op Android/iOS getest.
