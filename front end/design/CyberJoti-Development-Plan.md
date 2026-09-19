# CyberJoti – Development Plan

## 1. Doel

CyberJoti is een locatiegebaseerd teamspel voor JOTI Allart van Heemstede. Teams lopen fysiek door het speelgebied, delen periodiek hun locatie met de server en voeren verschillende soorten opdrachten uit.

De eerste versie ondersteunt drie spelobjecten:

- **Puzzle Point** – speler moet naar een locatie lopen en daar een vraag of puzzel beantwoorden.
- **Capture The Flag Point** – een team neemt een gebied over door er gedurende een ingestelde tijd aanwezig te zijn.
- **Physical Duck** – speler gaat naar een zoekgebied, vindt een fysieke eend en scant een unieke NFC-tag.

Spelers zien alleen de locaties van hun eigen team. Bestuur/Game Masters zien alle actieve spelers.

---

# 2. Technische stack

## Frontend

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- MapLibre GL JS
- WebSocket client

## Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Redis client
- WebSockets

## Data

- PostgreSQL – permanente data
- Redis – tijdelijke en realtime data

## Hosting

- Cloudflare voor DNS, CDN, HTTPS en frontend
- Railway voor FastAPI, PostgreSQL en Redis

---

# 3. Architectuur

```text
                    CLOUDFLARE
                        │
             ┌──────────┴──────────┐
             │                     │
        Vue frontend          /api + /ws
             │                     │
             │                FastAPI
             │                     │
             │          ┌──────────┴──────────┐
             │          │                     │
             │      PostgreSQL              Redis
             │          │                     │
             │      Game data           Live state
             │      Accounts            Locations
             │      Scores              Cooldowns
             │      History             Presence
             │
             └──────── WebSocket ──────────────┘
```

De backend is authoritative.

Een client mag locatiegegevens versturen:

```json
{
  "latitude": 52.123,
  "longitude": 4.456,
  "accuracy": 9
}
```

maar nooit zelf bepalen dat punten zijn verdiend of een capture is voltooid.

---

# 4. Rollen

## PLAYER

- eigen positie zien
- teamgenoten zien
- game-objecten zien
- puzzels oplossen
- capture points veroveren
- fysieke eenden scannen
- scoreboard bekijken

## TEAM_LEADER

Zelfde rechten als PLAYER, met eventueel beperkte extra teaminformatie.

## ADMIN

- alle spelers zien
- alle teams zien
- game beheren
- objecten beheren
- scores bekijken en corrigeren
- game starten, pauzeren en stoppen

---

# FASE 1 – MVP

Doel: een volledig speelbare versie waarin teams kunnen inloggen, hun locatie delen, hun eigen team zien en de drie kernactiviteiten kunnen uitvoeren.

## Implementation log

| Date | Status | Scope |
| --- | --- | --- |
| 2026-09-19 | Done | Runnable Docker development stack, authoritative FastAPI game API, Vue player UI, seeded demo data, and MVP activity flows added. |
| 2026-09-19 | Verified | Alembic migration + development seed, FastAPI import, authenticated login smoke test, and Vue production build passed in Docker. |
| 2026-09-19 | Done | MapLibre/OpenStreetMap live map and admin map-click object builder added. Admin can add or deactivate puzzle, capture, and NFC-duck points; an NFC token is shown once when a duck is created. |
| 2026-09-19 | Fixed and verified | Docker backend startup migration fixed by setting the application Python path. The complete local stack is running; health and admin-login checks pass. |
| 2026-09-19 | Fixed and verified | Frontend API and WebSocket traffic now uses same-origin Vite proxying to the backend container. Login through the frontend API route passes, including WSL-IP browser access. |
| 2026-09-19 | Done | Mobile-first CyberJoti tactical visual system applied to the Vue app: HUD login, team dashboard, radar map, scoreboard, admin builder, and touch-friendly bottom navigation. Production build passes. |
| 2026-09-19 | Done | Vue UI refined against the supplied React Field Terminal prototype: mascot identity, Material icon system, NFC quick action, segmented radar HUD, and prototype-style compact cards added without replacing the Vue game implementation. |
| 2026-09-19 | Done | Responsive wide-screen layout added: desktop/tablet uses the complete available canvas for dashboard, maps, scores, and the object builder; phone layout remains single-column and touch-first. Production build passes. |
| 2026-09-19 | Done | Wide dashboard changed into a full command board: primary mission, NFC action, and each available game-object action grow into large viewport-filling tiles instead of leaving empty space around compact cards. Production build passes. |
| 2026-09-19 | Done | Persistent, safe-area-aware footer navigation added. Equal-sized field controls remain visible at every scroll position, and all content reserves footer clearance. Production build passes. |
| 2026-09-19 | Done | Dashboard hierarchy refined: full-width team card, three equal-width status categories, full-width active mission at roughly 30% viewport height, then full-width NFC action. Production build passes. |
| 2026-09-19 | Prepared | Railway production configuration added and locally validated: Caddy-served frontend, private backend proxy, Railway PostgreSQL URL compatibility, and non-seeding backend startup. Deployment remains unchecked: the GitHub push needs authenticated credentials and no callable Railway deployment action is exposed in this session. |
| 2026-09-19 | Deployed; final publish pending | Railway production services are live (frontend, FastAPI backend, PostgreSQL, and Redis). Fixed the backend build context, connected it to Railway-managed Postgres through its reference variable, and forced the frontend to use its Dockerfile rather than Railpack autodetection. The source now also has explicit Caddy API/WebSocket routes ahead of the SPA fallback; commit and push this routing fix before treating public login as verified. |
| 2026-09-19 | Remaining | MapLibre map, Redis Pub/Sub across multiple backend instances, exhaustive automated/mobile/load/field testing, CI, and production operations remain deliberately unchecked until implemented and verified. |

---

# Epic 1 – Project setup

- [ ] Git repository aanmaken
- [x] `/frontend` Vue-project
- [x] `/backend` FastAPI-project
- [x] Docker Compose voor lokale development
- [x] PostgreSQL container
- [x] Redis container
- [x] `.env.example`
- [x] Development config
- [x] Alembic initial migration
- [ ] Backend logging
- [x] Health endpoint
- [ ] CI pipeline
- [ ] Frontend linting
- [ ] Backend linting
- [x] README met lokale installatie

## Gewenste structuur

```text
cyberjoti/
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── pages/
│       ├── stores/
│       ├── composables/
│       └── types/
├── backend/
│   └── app/
│       ├── api/
│       ├── auth/
│       ├── models/
│       ├── schemas/
│       ├── services/
│       ├── game/
│       └── websocket/
├── docker-compose.yml
└── README.md
```

## Definition of done

```bash
docker compose up
```

start lokaal frontend, backend, PostgreSQL en Redis.

---

# Epic 2 – Database

Basismodellen:

- Game
- Team
- User
- GameObject
- Puzzle
- CapturePoint
- Duck
- PuzzleAttempt
- CaptureEvent
- DuckScan
- ScoreEvent

## Game

```python
class Game:
    id: UUID
    name: str
    status: GameStatus
    starts_at: datetime
    ends_at: datetime
    created_at: datetime
```

Statussen:

```text
DRAFT
READY
RUNNING
PAUSED
FINISHED
```

## Team

```python
class Team:
    id: UUID
    game_id: UUID
    name: str
    color: str
    created_at: datetime
```

## User

```python
class User:
    id: UUID
    team_id: UUID | None
    name: str
    role: UserRole
    password_hash: str
    active: bool
```

Rollen:

```text
PLAYER
TEAM_LEADER
ADMIN
```

## GameObject

```python
class GameObject:
    id: UUID
    game_id: UUID
    type: GameObjectType
    name: str
    description: str | None
    latitude: float
    longitude: float
    activation_radius_meters: int
    active: bool
```

Types:

```text
PUZZLE
CAPTURE_POINT
PHYSICAL_DUCK
```

## Taken

- [x] SQLAlchemy models
- [x] Foreign keys
- [x] Indexes
- [x] Alembic initial migration
- [x] UUID primary keys
- [x] timestamps
- [x] enum types
- [x] seed development data

---

# Epic 3 – Authentication

API:

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

Taken:

- [x] Loginpagina
- [x] Password hashing
- [x] Authentication tokens of sessies
- [x] PLAYER-role
- [x] TEAM_LEADER-role
- [x] ADMIN-role
- [x] Backend authorization
- [x] Frontend route guards
- [x] Session expiry
- [x] Logout
- [ ] Basis rate limiting op login

Belangrijk:

```python
@router.get("/locations")
async def locations(user: User = Depends(current_user)):
    if user.role == UserRole.ADMIN:
        return await location_service.all_players()

    return await location_service.for_team(user.team_id)
```

Een gewone speler ontvangt nooit locaties van tegenstanders.

---

# Epic 4 – GPS tracking

Frontend-flow:

```text
navigator.geolocation
        ↓
Vue location service
        ↓
POST /api/location
        ↓
FastAPI
        ↓
Redis
```

Endpoint:

```text
POST /api/location
```

Request:

```json
{
  "latitude": 52.123456,
  "longitude": 4.123456,
  "accuracy": 8.2,
  "timestamp": "..."
}
```

Redis-key:

```text
player:location:{user_id}
```

Data:

```json
{
  "lat": 52.123456,
  "lng": 4.123456,
  "accuracy": 8.2,
  "updated_at": "..."
}
```

Standaard TTL:

```text
180 seconden
```

Taken:

- [x] Browser GPS permission
- [x] GPS watcher
- [ ] Default 15 seconden
- [x] API endpoint
- [x] Redis storage
- [x] TTL
- [x] Accuracy opslaan
- [x] Timestamp server-side registreren
- [x] Ongeldige coordinates weigeren
- [ ] Offline-status
- [x] GPS-uitgeschakeld melding
- [ ] App-background gedrag testen
- [ ] Mobiele browsers testen

---

# Epic 5 – Realtime

WebSocket:

```text
/ws/game
```

Events:

```text
PLAYER_LOCATION
PLAYER_ONLINE
PLAYER_OFFLINE
OBJECT_UPDATED
CAPTURE_STARTED
CAPTURE_CANCELLED
CAPTURE_COMPLETED
SCORE_UPDATED
```

Voorbeeld:

```json
{
  "type": "PLAYER_LOCATION",
  "data": {
    "player_id": "...",
    "lat": 52.12,
    "lng": 4.12
  }
}
```

Taken:

- [x] WebSocket authentication
- [x] Team channels
- [x] Admin channel
- [x] Reconnect
- [x] Heartbeat
- [ ] Redis Pub/Sub
- [x] Connection cleanup
- [x] Geen enemy-location leakage

---

# Epic 6 – Spelerskaart

Route:

```text
/game/map
```

Kaart bevat:

- eigen locatie
- teamgenoten
- puzzels
- capture points
- fysieke eenden

Taken:

- [x] MapLibre installeren
- [x] Map renderen
- [x] Eigen locatie
- [x] Teamgenoten
- [x] Game objects
- [x] Verschillende markers per type
- [x] Object selecteren
- [x] Object details
- [ ] Afstand tot object
- [ ] GPS accuracy tonen
- [ ] Online/offline status teamgenoten
- [x] Kaart automatisch centreren
- [ ] Mobiele bediening

---

# Epic 7 – Puzzle

```python
class Puzzle:
    game_object_id: UUID
    question: str
    answer_hash: str
    reward_points: int
    max_attempts: int | None
```

Endpoints:

```text
GET  /api/game-objects/{id}
POST /api/puzzles/{id}/answer
```

Servercontrole:

```text
Spel actief?
    ↓
Puzzle actief?
    ↓
Speler dichtbij genoeg?
    ↓
Al voltooid?
    ↓
Antwoord correct?
    ↓
ScoreEvent maken
```

Taken:

- [ ] Puzzle marker
- [x] Distance calculation backend
- [x] Activation radius
- [x] Antwoord indienen
- [x] Antwoord controleren
- [x] Incorrect response
- [x] Correct response
- [x] Reward
- [x] Completion per team
- [x] PuzzleAttempt opslaan
- [x] Dubbele rewards voorkomen

---

# Epic 8 – Capture The Flag

```python
class CapturePoint:
    game_object_id: UUID
    capture_seconds: int
    cooldown_seconds: int
    capture_reward: int
    owner_team_id: UUID | None
```

State:

```text
NEUTRAL
CAPTURING
OWNED
```

Flow:

```text
Speler komt radius binnen
        ↓
POST capture/start
        ↓
Server controleert locatie
        ↓
capture timer Redis
        ↓
periodieke locatiecontrole
        ↓
60 seconden geldig aanwezig
        ↓
CAPTURED
        ↓
score
        ↓
team cooldown
```

Endpoints:

```text
POST /api/capture/{id}/start
POST /api/capture/{id}/cancel
GET  /api/capture/{id}/status
```

Redis:

```text
capture:{point_id}:{team_id}
cooldown:{point_id}:{team_id}
```

Taken:

- [x] Capture radius
- [x] Start capture
- [x] 60 sec server timer
- [ ] Progress naar frontend
- [x] Radius opnieuw controleren
- [x] Capture annuleren bij verlaten gebied
- [x] Capture voltooien
- [x] Owner aanpassen
- [x] Reward
- [x] Cooldown
- [x] 5 minuten standaard cooldown
- [x] Andere teams kunnen overnemen
- [ ] Race conditions voorkomen
- [ ] Atomic Redis operation of locking
- [x] CaptureEvent audit record

---

# Epic 9 – Physical Duck

```python
class Duck:
    game_object_id: UUID
    scan_token_hash: str
    reward_points: int
    search_radius_meters: int
```

Flow:

```text
Duck marker
   ↓
naar gebied lopen
   ↓
eend zoeken
   ↓
NFC openen
   ↓
unieke URL/token
   ↓
backend validatie
   ↓
reward
```

Aanbevolen NFC-inhoud voor MVP:

```text
https://cyberjoti.nl/scan/<token>
```

Taken:

- [x] Duck aanmaken
- [x] Uniek random token
- [x] Alleen hash token opslaan
- [x] Backend tokenvalidatie
- [x] GPS-validatie
- [x] Reward
- [x] Eenmalig per team
- [x] DuckScan registreren
- [x] Duplicate scan blokkeren

---

# Epic 10 – Score engine

Scorewijzigingen worden append-only opgeslagen.

Niet:

```python
team.score += 500
```

Wel:

```python
ScoreEvent(
    team_id=team.id,
    type="DUCK_FOUND",
    points=500,
    reference_id=duck.id
)
```

Score:

```sql
SUM(score_events.points)
```

Types:

```text
PUZZLE_SOLVED
CAPTURE_COMPLETED
DUCK_FOUND
ADMIN_ADJUSTMENT
```

Taken:

- [x] ScoreEvent model
- [x] Puzzle rewards
- [x] Capture rewards
- [x] Duck rewards
- [x] Team totals
- [x] Score API
- [x] Scoreboard
- [x] Realtime score updates
- [x] Audit trail

---

# Epic 11 – Admin control center

Route:

```text
/admin
```

Bestuur ziet alle spelers.

Taken:

- [x] Admin login
- [x] Admin dashboard
- [x] Alle spelers op kaart
- [ ] Teamkleur
- [ ] Player selecteren
- [ ] Laatste locatie
- [ ] Accuracy
- [ ] Last seen
- [ ] Online/offline
- [x] Game objects
- [x] Scores
- [ ] Start game
- [ ] Pause game
- [ ] Stop game

---

# MVP Definition of Done

De complete flow moet werken:

```text
Admin maakt game
        ↓
Teams bestaan
        ↓
Spelers loggen in
        ↓
GPS wordt gedeeld
        ↓
Teamleden zien elkaar
        ↓
Admin ziet iedereen
        ↓
Speler ziet game objects
        ↓
Puzzle werkt
Capture werkt
Duck scan werkt
        ↓
punten worden toegekend
        ↓
scoreboard update realtime
```

Daarnaast:

- [ ] Geen enemy GPS-data via API
- [ ] Geen enemy GPS-data via WebSocket
- [ ] Geen punten vanuit client te manipuleren
- [ ] Capture server-side gevalideerd
- [ ] Duck dubbel scannen levert geen punten op
- [ ] Puzzle dubbel oplossen levert geen punten op
- [ ] Mobiel speelbaar
- [ ] 20+ simultane testspelers getest
- [ ] PostgreSQL backup ingericht
- [ ] Production logging

---

# FASE 2 – CyberJoti 1.0

# Game Builder

- [ ] Game aanmaken vanuit admin
- [ ] Game dupliceren
- [ ] Start/eindtijd instellen
- [ ] Teams beheren
- [ ] Spelers beheren
- [x] Objecten aan/uit zetten
- [x] Objecten op kaart plaatsen
- [ ] Marker verslepen
- [ ] Radius visueel instellen

# Puzzle Builder

- [x] Puzzle maken
- [x] Titel
- [x] Beschrijving
- [x] Vraag
- [x] Antwoord
- [ ] Multiple choice
- [ ] Tekstantwoord
- [x] Punten
- [x] Radius
- [ ] Max attempts
- [ ] Hint
- [ ] Hint penalty
- [ ] Publicatietijd

# CTF Builder

- [x] Capture point maken
- [x] Radius
- [x] Capture duration
- [x] Cooldown
- [x] Capture reward
- [ ] Ownership zichtbaar
- [ ] Capture history
- [ ] Optioneel periodieke punten voor langdurig bezit

# Duck Builder

- [x] Duck maken
- [x] NFC-token genereren
- [ ] Printable NFC URL
- [x] Zoekgebied
- [x] Reward
- [x] Duck activeren/deactiveren
- [ ] Scan history

---

# Game configuratie 1.0

```json
{
  "location": {
    "update_interval": 15,
    "offline_after": 180,
    "maximum_accuracy": 50
  },
  "capture": {
    "default_radius": 40,
    "default_duration": 60,
    "default_cooldown": 300
  },
  "map": {
    "show_team_members": true,
    "show_enemy_players": false
  }
}
```

Taken:

- [ ] Config model
- [ ] Admin configuration UI
- [ ] Input validation
- [ ] Defaults
- [ ] Per-game configuratie

---

# Anti-cheat 1.0

- [ ] Impossible movement detectie
- [ ] GPS accuracy checks
- [ ] Capture vereist meerdere locatie-updates
- [ ] Duck vereist locatie + token
- [ ] Rate limiting
- [ ] Puzzle brute-force bescherming
- [ ] Duplicate request bescherming
- [ ] Idempotency voor score rewards
- [ ] Suspicious event logging
- [ ] Admin security dashboard

Verdachte beweging alleen markeren, niet automatisch diskwalificeren.

---

# Privacy 1.0

- [ ] Duidelijke informatie over locatiegebruik
- [ ] Alleen tracking tijdens het spel
- [ ] Tracking stoppen na afloop
- [ ] Retentiebeleid
- [ ] Locatiehistorie beperken
- [ ] Admin-only toegang
- [ ] Basis audit logging admin
- [ ] Account deletion proces
- [ ] Privacyverklaring
- [ ] HTTPS verplicht

Live locaties in Redis krijgen een TTL zodat ze automatisch verdwijnen.

---

# FASE 3 – Afronding / Production Ready

# Testing

- [ ] Backend unit tests
- [ ] Game-engine tests
- [ ] API integration tests
- [ ] Frontend tests
- [ ] E2E tests
- [ ] Permission tests
- [ ] Basis security tests
- [ ] GPS spoof scenario testen
- [ ] Redis failure testen
- [ ] Database restart testen
- [ ] WebSocket reconnect testen

Belangrijke testscenario's:

```text
PLAYER Team A
GET Team B locations
→ geen data

PLAYER
POST fake score
→ onmogelijk

PLAYER buiten radius
POST puzzle answer
→ rejected

PLAYER buiten radius
POST capture
→ rejected

DUCK token opnieuw gebruiken
→ geen tweede reward
```

---

# Load testing

Richtpunt:

```text
100 spelers
iedere 15 seconden GPS
≈ 6,7 location updates/sec
```

Test:

- [ ] 50 spelers
- [ ] 100 spelers
- [ ] 250 spelers
- [ ] 500 spelers
- [ ] WebSocket load
- [ ] Location API load
- [ ] Redis load
- [ ] Scoreboard load

---

# Monitoring

Voor dit hobbyproject hoeft monitoring eenvoudig te blijven.

- [ ] API error logging
- [ ] Backend logs
- [ ] Database health check
- [ ] Redis health check
- [ ] WebSocket connection count
- [ ] GPS update count
- [ ] Basis uptime monitoring

Optioneel later:

- Sentry
- Grafana
- Prometheus

---

# Deployment

- [ ] Productiedomain
- [ ] Cloudflare DNS
- [ ] Cloudflare proxy
- [ ] HTTPS
- [ ] Frontend deployment
- [ ] Backend deployment
- [ ] PostgreSQL
- [ ] Redis
- [ ] Database backup
- [ ] Environment secrets
- [ ] GitHub Actions of platform auto-deploy
- [ ] Staging omgeving indien nodig
- [ ] Rollbackprocedure documenteren

---

# JOTI READY checklist

- [ ] Productiedatabase backup getest
- [ ] Restore getest
- [ ] Admin accounts getest
- [ ] Alle teams getest
- [ ] Alle NFC-eenden fysiek getest
- [ ] Iedere puzzellocatie getest
- [ ] Iedere CTF-locatie getest
- [ ] GPS-radii buiten getest
- [ ] iPhone getest
- [ ] Android getest
- [ ] Chrome getest
- [ ] Safari getest
- [ ] Slechte mobiele verbinding getest
- [ ] WebSocket reconnect getest
- [ ] 100+ virtuele spelers load test
- [ ] Emergency game pause getest
- [ ] Admin scorecorrectie getest
- [ ] Monitoring actief
- [ ] Backup admin aanwezig
- [ ] Game starten getest
- [ ] Game beëindigen getest

---

# 5. Aanbevolen ontwikkelvolgorde

```text
01  Repository + Docker
 ↓
02  PostgreSQL + Redis
 ↓
03  Users + Teams + Auth
 ↓
04  Game model
 ↓
05  GPS API
 ↓
06  Live team locations
 ↓
07  Map
 ↓
08  GameObject engine
 ↓
09  Puzzle
 ↓
10  Capture The Flag
 ↓
11  Physical Duck
 ↓
12  Score engine
 ↓
13  Admin live map
 ↓
──────── MVP ────────
 ↓
14  Game Builder
 ↓
15  Configuration
 ↓
16  Anti-cheat
 ↓
17  Privacy / security basis
 ↓
18  UX polish
 ↓
──────── 1.0 ────────
 ↓
19  Automated testing
 ↓
20  Load testing
 ↓
21  Monitoring
 ↓
22  Production deployment
 ↓
23  Field test
 ↓
24  JOTI READY
```

Aanbevolen milestones:

1. **MVP**
2. **1.0**
3. **JOTI READY**

---

# 6. Hostingadvies voor hobbyproject

## Aanbevolen opzet

```text
Cloudflare
├── DNS
├── SSL
├── CDN
└── Vue frontend

Railway
├── FastAPI
├── PostgreSQL
└── Redis
```

Dit is bewust simpel gehouden. Het doel is dat vrijwilligers makkelijk kunnen deployen en debuggen zonder zelf Kubernetes, VPS-patching of databasebeheer te hoeven doen.

## Waarom Cloudflare voor frontend

Cloudflare Pages is geschikt voor statische Vue-builds. Statische asset requests zijn op de Free tier gratis en onbeperkt volgens de actuele Cloudflare-documentatie.

Gebruik bijvoorbeeld:

```text
app.cyberjoti.nl  → Vue frontend
api.cyberjoti.nl  → Railway FastAPI
```

## Waarom Railway voor backend

Railway is voor dit project aantrekkelijk omdat FastAPI, PostgreSQL en Redis binnen één project kunnen draaien.

Voordelen:

- Git-based deploys
- weinig infrastructuurbeheer
- environment variables
- PostgreSQL templates
- Redis template
- private networking tussen services
- logs in dezelfde omgeving
- Hobby-plan is gericht op side projects

Het Railway Hobby-plan kost momenteel minimaal ongeveer **$5 per maand**, waarbij dat bedrag meetelt als usage credit. Werkelijk gebruik boven dat bedrag wordt extra afgerekend.

Voor een klein CyberJoti-evenement verwacht ik dat deze architectuur technisch ruim voldoende kan zijn, maar voer voor het evenement wel een loadtest uit met minimaal het verwachte aantal gelijktijdige spelers.

## Development

Lokaal blijft Docker Compose de standaard:

```text
Vue
FastAPI
PostgreSQL
Redis
```

Productie gebruikt dezelfde conceptuele services op Cloudflare en Railway.

## Wat we bewust NIET doen voor MVP

Voor dit hobbyproject niet vooraf bouwen tenzij daar later een duidelijke reden voor ontstaat:

- Kubernetes
- meerdere backend replicas
- Kafka
- Celery clusters
- dedicated Redis cluster
- multi-region databases
- complexe WAF-regels
- uitgebreide SIEM/security monitoring
- volledige microservice-architectuur

Start met één FastAPI-service, één Postgres-database en één Redis-instance.

---

# 7. Minimum security baseline

Ook voor een hobbyproject blijven een paar beveiligingsmaatregelen belangrijk omdat locatiegegevens worden verwerkt.

Minimaal:

- [ ] HTTPS
- [ ] passwords hashen
- [ ] secrets niet in Git
- [ ] spelers mogen alleen eigen teamlocaties opvragen
- [ ] admins apart autoriseren
- [ ] server bepaalt scores
- [ ] PostgreSQL niet publiek toegankelijk maken als dit niet nodig is
- [ ] Redis niet publiek toegankelijk maken
- [ ] basis rate limiting op login
- [ ] databasebackups rond het evenement

De rest kan pragmatisch worden toegevoegd wanneer het project groeit.

---

# 8. Eerste production setup

```text
GitHub repository
      │
      ├── frontend/
      │      │
      │      └── Cloudflare Pages
      │
      └── backend/
             │
             └── Railway
                   ├── FastAPI
                   ├── PostgreSQL
                   └── Redis
```

Aanbevolen domeinen:

```text
cyberjoti.nl
app.cyberjoti.nl
api.cyberjoti.nl
```

Voor een eerste versie kan `cyberjoti.nl` direct naar de Vue-app wijzen en is een aparte `app.` subdomain niet noodzakelijk.

---

# 9. Samenvatting

Voor CyberJoti is de aanbevolen eerste hostingopzet:

**Cloudflare Pages + Railway.**

Deze combinatie houdt beheer klein, deploys eenvoudig en kosten passend bij een hobbyproject. De applicatie blijft ondertussen technisch netjes opgesplitst in frontend, backend, PostgreSQL en Redis, waardoor later migreren naar een andere provider relatief eenvoudig blijft.
