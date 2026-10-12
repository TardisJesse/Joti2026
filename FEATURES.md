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
