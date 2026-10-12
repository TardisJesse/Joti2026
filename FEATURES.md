# Profiles, capture income and photo points

Players can set or change their profile photo on the scoreboard. A clickable
plus appears in the profile circle until a photo has been added. Their
photo is shown in the GPS marker and represents their team on the scoreboard.
The scoreboard shows the three leaders on a podium, then ranks all remaining
teams by descending score. Ties use team name, then team ID. Admin map popups
show team names rather than generated usernames.

Capture points retain their existing one-time capture reward and also award
their owner 1 point per full minute by default. Admins can configure the rate
when creating a post. Income is calculated on the server from a persistent
clock whenever scores are read or ownership/round status changes. It catches up
after disconnection or restart. Paused rounds and inactive points do not accrue
income. Partial minutes survive pauses and reset when ownership changes.

Admins can create a **Fotopunt** with a radius and reward. Players must share
a recent, accurate GPS position inside the radius to view the point's gallery
or submit a team photo. Each team can submit and earn the reward once per point.
Admins can review galleries without the location restriction. The challenge
asks players to include themselves and their team; image content is not
automatically checked.

Admins have a separate **Timer** tab. Setting a duration (1–1440 minutes) starts
the selected round and sends a shared red countdown to everyone's top bar.
At zero, the server finishes the round and blocks further scoring. A background
clock enforces the deadline without connected browsers, and overdue rounds are
finished after a server restart. Capture income is capped at the deadline.
Pausing a round freezes its remaining time; starting it again resumes the timer.
Admins can restart or remove the timer. Removing it leaves the round's current
status unchanged.

Uploads support JPEG, PNG and WebP. The browser resizes photos, and the server
decodes and re-encodes them to strip metadata and store bounded raster images
in the database. Profile thumbnails are public to signed-in players in the
same round through scores; challenge photos are served through the range gate.

## Apply to an existing installation

Install the updated backend requirements and run `alembic upgrade head` from
`backend` before starting the updated backend. Rebuild the frontend. Docker
users can rebuild using the existing Compose setup, whose backend startup runs
migrations.

## Verification

- Backend: from `backend`, run `python -m unittest discover -s tests -v`.
- Frontend: from `frontend`, run `npm test` and `npm run build`.
- Browser: serve the frontend build at `http://127.0.0.1:5179`, then run
  `npm run test:ui`. The test uses Edge on Windows and Playwright Chromium on
  other platforms. It mocks API responses, tests player/admin flows, and writes
  mobile and desktop screenshots to `frontend/tests`.

## Rotating bonus locations and returning teams

After ten minutes of running play, one active capture point becomes a bonus
location for five minutes. The bonus doubles ownership income (not the one-off
capture reward). Every ten playing minutes the next post takes its turn.
Players see a rotating rainbow marker border, a map banner, and a notice.
Pauses freeze the bonus clock; restarts retain it. Settlement includes bonus
intervals missed while offline and stops at the round deadline. Only active
capture points participate; add capture points in the admin object editor.

Joining with the same game code and case-insensitive team name returns the
existing active team account, including its score and photo. Existing teams
can return to finished rounds to view results; new teams cannot join them.
These two values grant team access; there is no separate player password.

## Followers, introduction, news and scanners

Visible rewards and scores now use **volgers**; the existing score schema and
amounts are unchanged. Object metadata includes the configured one-off reward.

The sign-in screen and dashboard offer **Speluitleg**. The 135-second MP4 uses
the existing duck mascot, Dutch Windows voice narration, animated activity
symbols and a Dutch WebVTT caption track. The separate download has embedded
subtitles for use on a beamer, avoiding double captions in the app. It never
autoplays, stops on closing, and includes a complete text alternative. Download
the MP4 for a shared start moment. Source scene timings, narration and renderer
are in `video-source`; imported MP4s can be edited in Canva. The renderer uses
Pillow and imageio-ffmpeg and expects Dutch voice WAVs for each scene.

`GET /api/news` returns the latest 50 persisted events, scoped to the player's
round (admins select `game_id`). New events also arrive as `NEWS_EVENT` messages.
Capture, bonus activation and round/timer status changes appear in the feed.
There is no historical backfill, per-minute income spam or scanner usage news.
Bonus events are idempotent per round/cycle; clients deduplicate by event ID and
refresh the feed after reconnecting.

Admins can add **Scannerpunt**, with a 40-metre default radius and no reward.
`GET /api/scanners/{object_id}/locations` requires a running round and a nearby,
fresh, accurate GPS fix on every request. It returns one recent location per
other active team in the same round, with photo/name; stale/inaccurate fixes
are omitted and responses cannot be cached. Players poll every five seconds
while open. Closing, moving out, invalid GPS, failed requests, switching screens
or ending/pausing the round clears all revealed markers and cancels requests.
The admin's existing full map remains unchanged. Run migration 0008 before
starting the backend; PostgreSQL enum additions remain after downgrade.

## Allart JOTI 2026 boards

Migration 0009 installs the requested Ronde-Test, Ronde A and Ronde B once.
It matches existing round codes ignoring separators/case, then exact normalized
round names; ambiguous matches abort instead of guessing. Existing codes are
preserved. Old objects are deactivated with an undo snapshot; player profiles,
teams and historical scores are retained. All three rounds are prepared in
READY state with their timer stopped and a fresh bonus clock. Start a timer
from the admin tab when the group is ready. Repeated installation does not
overwrite subsequent admin changes. A migration downgrade restores the prior
objects and round settings without deleting gameplay history.

Ronde-Test: 6 stations near the clubhouse, a roughly 0.7 km return walk and a
20-minute suggested timer. Ronde A: 21 stations in Holierhoek/Veenpad, with a
roughly 4.1 km example circuit. Ronde B: 21 different stations in Woudhoek via
the pedestrian/cycle network, roughly 4.2 km. Use 90 minutes for the full outer
boards; teams freely choose missions. Each outer board has five capture posts,
six photo challenges, eight puzzles and two private scanners. Capture posts
give 30 followers on capture and 5/minute, with a 45-second capture. Photo
challenges give 60, puzzles 40–80, and scanners give no score. The training
board uses smaller rewards and a 15-second capture. Owned posts cannot be
recaptured by the same team to farm the one-off reward.

Locations are snapped to mapped walking/cycle paths, excluding explicitly
private/no-foot ways. The points stay within 2 km of the verified clubhouse
location; their activation circles do not overlap. Main-board zones range from
30 to 40 metres, training zones are 20 metres. All capture circles are shown
on the map; selected photo/scanner zones use their own activity colours.
Map coordinates and example routes use OpenStreetMap data retrieved on
12 October 2026; this is a map-based layout, not a field access survey. The
organiser should inspect paths/current access before the event, and bring
torches when playing after dark. JOTI tasks focus on world friendship, messages,
codes and safe online contact. No NFC ducks are added without physical tags.

The immutable board pack is in backend/app/data/allart_joti_2026_v1.json.
It contains answer hashes, not plaintext puzzle solutions. Locally prepared
organiser maps, full briefing and solution key are in board-design; the solution
key is deliberately not shipped in the app or repository.
