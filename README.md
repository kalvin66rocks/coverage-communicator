# Life Tracker

A Flask-based life total tracker for tabletop card games, built for streaming with OBS. Tracks **two simultaneous matches**, each with two players, plus per-match timers, game score, poison counters, player info, and event/commentator details. Everything is controlled from a web admin panel and rendered onto transparent OBS overlays.

## Disclaimer

This was developed with the help of Claude.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

The server starts on port `5008` and binds to all network interfaces, so other devices on the same network can reach it (see [Accessing from other devices](#accessing-from-other-devices)).

## Pages

| URL | Purpose |
|-----|---------|
| `http://localhost:5008/` | **Control panel** — adjust life, poison, score, and timers for both matches. Player names are shown read-only here. |
| `http://localhost:5008/players` | **Player info editor** — set each player's name, pronouns, deck, and record, plus the shared event name, commentators, and round. |
| `http://localhost:5008/overlay/match1` | **OBS overlay for match 1** |
| `http://localhost:5008/overlay/match2` | **OBS overlay for match 2** |
| `http://localhost:5008/overlay/commentators` | **Commentator overlay** — event name plus both commentators' names and pronouns, with positioning that's easy to align to an existing graphic |

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
Set from the `/players` page, displayed on the overlay beside each life total:
- **Name** and **Deck** (anchored toward the life total)
- **Pronouns** and **Record** (anchored toward the center/timer)

Empty fields are hidden so they leave no gaps.

### Event info
Shared across both matches, set from the `/players` page:
- **Event name** — displayed bottom-center of the match overlays
- **Commentator 1** and **Commentator 2** — entered separately, each with optional **social handle** and **pronouns** fields. On the match overlays the names appear to the left of the event name joined with ` & ` and prefixed with 🎤 (e.g. `🎤 Alex & Sam`). If only one is filled in, just that name shows; if both are empty, nothing shows.
- **Round** — displayed bottom-right of the match overlays

### Commentator overlay
A separate overlay at `/overlay/commentators` showing the event name and both commentators' names, social handles, and pronouns, intended to be composited over an existing lower-third or intro graphic. Under each name, the social handle and pronouns share one line (social first, then pronouns, separated by a space) centered with the name. All positions (event and each commentator's anchor point, alignment, font sizes, and colors) are exposed as CSS variables in a clearly labeled block at the top of `templates/commentator_overlay.html`, so you can line the text up with your graphic by editing just those values. Commentator 1 is anchored a fixed distance from the left edge and commentator 2 the same distance from the right edge; each block's `align-center` / `align-left` / `align-right` class controls whether its anchor point is its center, left, or right edge.

## OBS Setup

For each match you want to show:

1. In OBS, add a **Browser Source**.
2. Set the URL to `http://localhost:5008/overlay/match1` (or `match2`).
3. Set Width: `1920`, Height: `1080`.
4. The overlay background is transparent — no extra configuration needed.

Run two browser sources (one per match) if you're streaming both tables.

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
| GET  | `/api/state` | — | Full state for both matches plus event info |
| GET  | `/api/state/<match>` | — | State for a single match (used by its overlay) |
| POST | `/api/life/<match>/<player>` | `{"action": "increase", "amount": 1}` | Adjust life. Actions: `increase`, `decrease`, `reset`, `set` |
| POST | `/api/poison/<match>/<player>` | `{"action": "increase"}` | Adjust poison. Actions: `increase`, `decrease`, `reset` |
| POST | `/api/score/<match>/<player>` | `{"action": "increase"}` | Adjust score. Actions: `increase`, `decrease`, `reset` |
| POST | `/api/timer/<match>` | `{"action": "start"}` | Control timer. Actions: `start`, `pause`, `reset`, `set_mode` (with `{"count_up": true}`) |
| POST | `/api/player/<match>/<player>` | `{"name": "...", "deck": "...", "record": "...", "pronouns": "..."}` | Update any subset of a player's info |
| POST | `/api/name/<match>/<player>` | `{"name": "Alice"}` | Update just a player's name |
| POST | `/api/event_info` | `{"event": "...", "commentator1": "...", "commentator1_social": "...", "commentator1_pronouns": "...", "commentator2": "...", "commentator2_social": "...", "commentator2_pronouns": "...", "round": "..."}` | Update any subset of the shared event info |
| POST | `/api/round` | `{"round": "..."}` | Update just the round (legacy; `/api/event_info` is preferred) |
| POST | `/api/reset/<match>` | — | Reset both players in one match to 20 life |
| POST | `/api/reset_all` | — | Reset all players in both matches to 20 life |

## Notes

- State is held **in memory** and resets when the server restarts.
- All state mutations are guarded by a thread `Lock` for safe concurrent access.
- The overlay uses Arial/Helvetica, white text, and a fixed 1920×1080 canvas. Life totals occupy a fixed 3-digit-wide slot so surrounding info doesn't shift as the numbers change.
- Timer values are authoritative on the server; clients tick locally between polls for smooth display and re-sync on drift.
