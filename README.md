# Life Tracker

A Flask-based life total tracker for tabletop card games, built for streaming with OBS. Tracks **two simultaneous matches**, each with two players, plus per-match timers, game score, poison counters, player info, event/commentator details, and an interview scene. Everything is controlled from a set of web pages and rendered onto transparent OBS overlays.

## Disclaimer

This was developed with the help of Claude.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

The server starts on port `5008` and binds to all network interfaces, so other devices on the same network can reach it (see [Accessing from other devices](#accessing-from-other-devices)).

## Pages

### Control pages

| URL | Purpose |
|-----|---------|
| `http://localhost:5008/` | **Control panel** — adjust life, poison, score, and timers for both matches. Links to all other entry pages. |
| `http://localhost:5008/players` | **Player info** — set each player's name, pronouns, deck, and record for both matches. |
| `http://localhost:5008/event` | **Event info** — set the shared event name, round, and both commentators (name, social handle, pronouns). |
| `http://localhost:5008/interview` | **Interview** — set the player name, deck, and interviewer for the interview scene. |

### OBS overlays

| URL | Purpose |
|-----|---------|
| `http://localhost:5008/overlay/match1` | **Match 1 overlay** |
| `http://localhost:5008/overlay/match2` | **Match 2 overlay** |
| `http://localhost:5008/overlay/commentators` | **Commentator overlay** — event name plus both commentators' names, social handles, and pronouns |
| `http://localhost:5008/overlay/interview` | **Interview overlay** — player name and deck centered on screen, event name/round/interviewer in the bottom bar |

All pages poll the server every 2 seconds, so the admin panel and overlays stay in sync across multiple open devices automatically.

## Features

### Two matches
Two fully independent matches (`match1`, `match2`), each with its own players, timer, and score. Each gets its own OBS overlay URL.

### Life totals
Increase, decrease (by 1 or 5), and reset per player. Reset sets life back to 20. Per-match and global reset buttons are available.

### Poison counters
Per-player poison counter with + / − controls (floored at 0). On the overlay, poison displays beneath the life total and is **hidden entirely when 0**.

### Timer
Each match has its own 50-minute timer that can be started, paused, and reset from the admin panel.
- Counts **down** from 50:00 by default and stops at 0:00.
- A **Count up** checkbox switches it to a stopwatch counting up from 0 with no upper limit. Switching mode pauses and resets the timer.
- Timer state is computed server-side, so reloading an overlay mid-match shows the correct time. Displays as `MM:SS`, centered at the top of the overlay.

### Game score
Per-match win counter for each player, adjustable from the admin panel. Displays beneath the timer on the overlay as `1-1`.

### Player info
Set from `/players`, displayed on the overlay beside each life total:
- **Name** and **Deck** (anchored toward the life total)
- **Pronouns** and **Record** (anchored toward the center/timer)

Empty fields are hidden so they leave no gaps. Long names truncate with an ellipsis rather than pushing other elements out of position.

### Event info
Shared across all overlays, set from `/event`:
- **Event name** — displayed bottom-center on match overlays and the interview overlay
- **Round** — displayed bottom-right on match overlays and the interview overlay
- **Commentator 1** and **Commentator 2** — each with optional **social handle** and **pronouns**. On match overlays the names appear bottom-left joined with ` & ` and prefixed with 🎤. If only one is filled in, just that name shows; if both are empty, nothing shows.

### Commentator overlay
A dedicated overlay at `/overlay/commentators` showing the event name and both commentators' names, social handles, and pronouns, intended to be composited over an existing lower-third or intro graphic. Commentator 1 is anchored a fixed distance from the left edge and commentator 2 the same distance from the right edge. All positions, font sizes, and colors are exposed as CSS variables at the top of `templates/commentator_overlay.html`.

### Interview scene
A dedicated entry page at `/interview` and overlay at `/overlay/interview` for use during player interviews.
- **Entry page** fields: player name, deck, and interviewer name.
- **Overlay**: player name and deck displayed large and centered at two-thirds down the screen. The bottom bar mirrors the match overlays exactly — event name bottom-center, round bottom-right, and interviewer name at the commentator position bottom-left.

## OBS Setup

For each overlay you want to show:

1. In OBS, add a **Browser Source**.
2. Set the URL to the overlay URL (e.g. `http://localhost:5008/overlay/match1`).
3. Set Width: `1920`, Height: `1080`.
4. The overlay background is transparent — no extra configuration needed.

## Accessing from other devices

The server binds to `0.0.0.0`, so any device on the same network can connect.

1. Find your computer's local IP:
   - **macOS:** `ipconfig getifaddr en0`
   - **Windows:** `ipconfig` (look for the IPv4 address)
2. On the other device, browse to `http://<your-ip>:5008` (e.g. `http://192.168.1.50:5008`).
3. If the connection is refused, check your firewall:
   - **macOS:** System Settings → Network → Firewall — allow Python, or turn it off to test.
   - **Windows:** Allow inbound TCP on port 5008 through Windows Defender Firewall.

Both devices must be on the same network.

## API Endpoints

All POST endpoints accept and return JSON. `<match>` is `match1` or `match2`; `<player>` is `player1` or `player2`.

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| GET  | `/api/state` | — | Full state for both matches, event info, and interview info |
| GET  | `/api/state/<match>` | — | State for a single match (used by its overlay) |
| POST | `/api/life/<match>/<player>` | `{"action": "increase", "amount": 1}` | Adjust life. Actions: `increase`, `decrease`, `reset`, `set` |
| POST | `/api/poison/<match>/<player>` | `{"action": "increase"}` | Adjust poison. Actions: `increase`, `decrease`, `reset` |
| POST | `/api/score/<match>/<player>` | `{"action": "increase"}` | Adjust score. Actions: `increase`, `decrease`, `reset` |
| POST | `/api/timer/<match>` | `{"action": "start"}` | Control timer. Actions: `start`, `pause`, `reset`, `set_mode` (with `{"count_up": true}`) |
| POST | `/api/player/<match>/<player>` | `{"name": "...", "deck": "...", "record": "...", "pronouns": "..."}` | Update any subset of a player's info |
| POST | `/api/name/<match>/<player>` | `{"name": "Alice"}` | Update just a player's name |
| POST | `/api/event_info` | `{"event": "...", "round": "...", "commentator1": "...", "commentator1_social": "...", "commentator1_pronouns": "...", "commentator2": "...", "commentator2_social": "...", "commentator2_pronouns": "..."}` | Update any subset of the shared event info |
| POST | `/api/round` | `{"round": "..."}` | Update just the round (legacy; `/api/event_info` is preferred) |
| POST | `/api/interview` | `{"name": "...", "deck": "...", "interviewer": "..."}` | Update any subset of the interview scene info |
| POST | `/api/reset/<match>` | — | Reset both players in one match to 20 life |
| POST | `/api/reset_all` | — | Reset all players in both matches to 20 life |

## Notes

- State is held **in memory** and resets when the server restarts.
- All state mutations are guarded by a thread `Lock` for safe concurrent access.
- The overlays use Arial/Helvetica, white text, and a fixed 1920×1080 canvas. Life totals occupy a fixed 3-digit-wide slot so surrounding info doesn't shift as the numbers change.
- Timer values are authoritative on the server; clients tick locally between polls for smooth display and re-sync on drift.
