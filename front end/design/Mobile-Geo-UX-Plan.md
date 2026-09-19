# Mobiele geo-interface — uitvoeringsplan

## Doel
Op een telefoon snel kunnen zien waar je bent, een spelpunt vinden en de juiste actie starten. Donkere CyberJoti-stijl behouden, zonder grid. De footer blijft zichtbaar.

## Richtlijnen en keuzes
- Aanraakvlakken van minimaal 48 × 48 CSS-pixels voor primaire bediening, ruimte tussen knoppen, zichtbare toetsenbordfocus. Dit is onze web-ontwerpkeuze, geïnspireerd op [Android 48 dp](https://support.google.com/accessibility/android/answer/7101858); [WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum/) vereist minimaal 24 CSS-pixels met uitzonderingen.
- Kaart krijgt de resterende schermhoogte, rekening houdend met mobiele browserbalken en safe areas. Details komen in een compact, inklapbaar paneel boven de navigatie.
- Begin op eigen GPS; handmatig verkennen stopt automatisch centreren. Een expliciete locatieknop brengt de speler terug. Dit sluit aan op het [MapLibre interactiepatroon](https://maplibre.org/maplibre-gl-js/docs/API/classes/GeolocateControl/).
- GPS zoeken, geweigerde toestemming, onnauwkeurigheid en verouderde locatie krijgen concrete tekst. Geen onvoorwaardelijke “GPS LIVE”.
- Filterknoppen werken daadwerkelijk. Markers hebben namen; een geselecteerd punt toont type, afstand (hemelsbreed), actieradius en spelactie. Geen navigatieroute suggereren.
- Ringen alleen rond het gecentreerde locatiepunt; verdwijnen bij handmatige kaartbeweging. Geen grid of “Jij”-overlay.

## Uitvoering
- [x] Mobiele kaartpagina en compact, inklapbaar puntenpaneel; spelers openen na inloggen op de kaart.
- [x] Werkende categorieën en selectie via marker/lijst, hemelsbrede afstand en spelacties.
- [x] Eigen-positieknop en vrije kaartbeweging; late GPS neemt de camera niet over na handmatig verkennen.
- [x] GPS-status en lokale telefoonpositie los van API-vertraging; melding bij geweigerde toestemming, fouten of een positie ouder dan een minuut.
- [x] Aanraakvlakken, leesbare tekst, safe areas, focusstijlen en reduced motion. Ontbrekende mobiele viewport hersteld.
- [x] TypeScript/Vue-productie-build en gerichte gedragscontroles (`node tests/map-behavior.cjs`) geslaagd.

## Verificatie
De componenttest gebruikt de echte Vue-component met een MapLibre-testdouble: eigen team selecteren, GPS na openen, handmatig zoomen, late GPS na slepen, hercentreren, puntselectie en opruimen. Deze test verifieert gedrag, niet de grafische weergave. De ingebouwde browser kon niet starten door een Windows/WSL-padfout; visuele apparaatcontroles hieronder blijven open. Bestaande browserdialoogvensters voor puzzelantwoorden en NFC-invoer blijven een mogelijke volgende UX-verbetering.

## Nog fysiek te controleren
- [ ] Buiten lopen met echte telefoon-GPS, toestemming weigeren/herstellen en slechte verbinding.
- [ ] iOS Safari en Android Chrome, portret/landschap en grotere systeemtekst.
