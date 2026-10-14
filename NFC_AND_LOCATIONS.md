# NFC-eendjes en standaardlocaties

Na deployment: voer `alembic upgrade head` uit. Migratie 0011 voegt de eendidentiteiten toe; bestaande locaties worden hierdoor niet overschreven.

In **Beheer → Objecten**, kies eerst een spelronde. **Load locations · Ronde A/B** laadt de gekozen standaardindeling in die geselecteerde ronde: 20 eendjes, 8 puzzels, 8 fotopunten, 8 zendmasten en 2 scanners. De ronde krijgt de status READY. De huidige locaties worden vervangen; teams, foto's en scoregeschiedenis blijven bewaard. Pauzeer een lopende ronde eerst. Opnieuw laden of een eend verplaatsen geeft geen nieuwe beloning aan teams die die eend al gevonden hebben.

Kies **Aanpassen** bij een eendje, klik op de kaart of pas de coördinaten aan en sla op. De dropdown bevat de huidige eend en eendjes die nog niet actief in die ronde staan. Een verwijderde eend wordt opnieuw beschikbaar. De backend vergrendelt de spelronde tijdens plaatsingen en weigert dubbele plaatsingen. Bij wisselen naar een andere eend blijven de scores bij de oorspronkelijke fysieke eend horen.

Voor spelers is **SCAN NFC** de grote hoofdactie. De browser vraagt toestemming na die druk. De NFC-UID wordt intern gekoppeld aan de 20 eenden uit het aangeleverde Excelbestand; spelers hoeven geen serienummer te kennen. De kleine backup eronder vraagt uitsluitend het nummer op de eend, 1 t/m 20. Beide manieren vereisen recente GPS binnen de activatiecirkel en leveren maximaal één beloning per team per fysieke eend per ronde op. De standaardbeloning is 50 volgers.

Web NFC vereist HTTPS, een geschikte Android-browser, ingeschakelde NFC en een NDEF-tag. Zorg dat elke tag NDEF-geformatteerd is; een eenvoudig tekstrecord is voldoende omdat de app de UID gebruikt. Er is geen specifieke URL of geheim token op de tag nodig. Als de browser geen UID doorgeeft, de tag niet leesbaar is of toestemming is geweigerd, verschijnt de nummerbackup. iPhone-gebruikers gebruiken de nummerbackup. Controleer vóór het spel ook een echte tag op een Android-telefoon; de automatische browsertest simuleert de NFC-hardware.

De standaardindeling is berekend met OpenStreetMap-wandelpaden van 14 oktober 2026. Bij 4 km/u is het verste spelpunt inclusief 100 meter marge 1.192 meter vanaf Allart (circa 18 minuten); de langste route tussen spelpunten is 1.672 meter (circa 25 minuten). Dit betreft lopen, zonder zoeken, puzzelen, captures of het bezoeken van alle 46 locaties. Handmatig verplaatste locaties veranderen deze afstanden.

De data staan in `backend/app/data/allart_joti_2026_walkable_v3.json`; het routingnetwerk en de onafhankelijke afstandstests staan ernaast en in `backend/tests/test_numbered_ducks.py`. De generator `backend/scripts/build_walkable_board.py` gebruikt het aangeleverde Excelbestand en de openbare OSM-download uit de `sources`-lijst (opslaan als `backend/app/data/allart_walk_network.osm`).

Validatie: backendtests, TypeScript-controle, productiebouw en `frontend/tests/ducks-ui.cjs` (tegen een lokale preview op poort 5173). De mobiele UI-test controleert de nummerbackup, NFC-toestemmingsfouten, een gesimuleerde UID-scan, stoppen bij sluiten, laadknoppen en de dropdown bij aanpassen.

Bronnen: [Chrome Web NFC](https://developer.chrome.com/docs/capabilities/nfc), [MDN NDEFReader](https://developer.mozilla.org/en-US/docs/Web/API/NDEFReader), [OpenStreetMap](https://www.openstreetmap.org/copyright).
