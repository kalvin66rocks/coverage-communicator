from flask import Flask, jsonify, request, render_template
from threading import Lock
import time

app = Flask(__name__)

COUNTDOWN_SECONDS = 50 * 60  # 50 minutes

def make_timer():
    return {
        "seconds":    COUNTDOWN_SECONDS,  # current value (counts down or up)
        "running":    False,
        "count_up":   False,              # True = stopwatch, False = countdown
        "last_tick":  None,               # epoch float when timer was last started
    }

def make_player(name):
    return {"name": name, "life": 20, "poison": 0, "deck": "", "record": "", "pronouns": ""}

state = {
    "match1": {
        "player1": make_player("Player 1"),
        "player2": make_player("Player 2"),
        "timer":   make_timer(),
        "score":   {"player1": 0, "player2": 0},
    },
    "match2": {
        "player1": make_player("Player 3"),
        "player2": make_player("Player 4"),
        "timer":   make_timer(),
        "score":   {"player1": 0, "player2": 0},
    },
    "round": "",
    "event": "",
    "commentators": "",
}
lock = Lock()

VALID_MATCHES = ("match1", "match2")
VALID_PLAYERS = ("player1", "player2")


def current_timer_seconds(timer):
    """Return the live second value, accounting for time elapsed since last tick."""
    secs = timer["seconds"]
    if timer["running"] and timer["last_tick"] is not None:
        elapsed = time.time() - timer["last_tick"]
        if timer["count_up"]:
            secs = secs + elapsed
        else:
            secs = max(0, secs - elapsed)
    return secs


def timer_snapshot(timer):
    """Return a JSON-safe dict with the computed current seconds."""
    secs = current_timer_seconds(timer)
    return {
        "seconds":  secs,
        "running":  timer["running"],
        "count_up": timer["count_up"],
    }


# ── Pages ──────────────────────────────────────────────────────────────────

@app.route("/")
def admin():
    return render_template("admin.html")

@app.route("/players")
def players_page():
    return render_template("players.html")

@app.route("/overlay/<match>")
def overlay(match):
    if match not in VALID_MATCHES:
        return "Not found", 404
    return render_template("overlay.html", match=match)


# ── API ────────────────────────────────────────────────────────────────────

@app.route("/api/state")
def get_state():
    with lock:
        out = {}
        for m in VALID_MATCHES:
            out[m] = {
                "player1": state[m]["player1"],
                "player2": state[m]["player2"],
                "timer":   timer_snapshot(state[m]["timer"]),
                "score":   state[m]["score"],
            }
        out["round"] = state["round"]
        out["event"] = state["event"]
        out["commentators"] = state["commentators"]
        return jsonify(out)

@app.route("/api/state/<match>")
def get_match_state(match):
    if match not in VALID_MATCHES:
        return jsonify({"error": "Unknown match"}), 400
    with lock:
        m = state[match]
        return jsonify({
            "player1": m["player1"],
            "player2": m["player2"],
            "timer":   timer_snapshot(m["timer"]),
            "score":   m["score"],
            "round":   state["round"],
            "event":   state["event"],
            "commentators": state["commentators"],
        })

@app.route("/api/event_info", methods=["POST"])
def update_event_info():
    data = request.json or {}
    with lock:
        if "round"        in data: state["round"]        = data["round"].strip()
        if "event"        in data: state["event"]        = data["event"].strip()
        if "commentators" in data: state["commentators"] = data["commentators"].strip()
        return jsonify({
            "round":        state["round"],
            "event":        state["event"],
            "commentators": state["commentators"],
        })

@app.route("/api/round", methods=["POST"])
def update_round():
    data = request.json or {}
    with lock:
        state["round"] = data.get("round", "").strip()
        return jsonify({"round": state["round"]})

@app.route("/api/player/<match>/<player>", methods=["POST"])
def update_player_info(match, player):
    if match not in VALID_MATCHES or player not in VALID_PLAYERS:
        return jsonify({"error": "Unknown match or player"}), 400
    data = request.json or {}
    with lock:
        p = state[match][player]
        if "name"     in data: p["name"]     = data["name"].strip()
        if "deck"     in data: p["deck"]     = data["deck"].strip()
        if "record"   in data: p["record"]   = data["record"].strip()
        if "pronouns" in data: p["pronouns"] = data["pronouns"].strip()
        return jsonify(p)

@app.route("/api/poison/<match>/<player>", methods=["POST"])
def update_poison(match, player):
    if match not in VALID_MATCHES or player not in VALID_PLAYERS:
        return jsonify({"error": "Unknown match or player"}), 400
    data   = request.json or {}
    action = data.get("action")
    amount = int(data.get("amount", 1))
    with lock:
        if action == "increase":
            state[match][player]["poison"] += amount
        elif action == "decrease":
            state[match][player]["poison"] = max(0, state[match][player]["poison"] - amount)
        elif action == "reset":
            state[match][player]["poison"] = 0
        else:
            return jsonify({"error": "Unknown action"}), 400
        return jsonify(state[match][player])


@app.route("/api/life/<match>/<player>", methods=["POST"])
def update_life(match, player):
    if match not in VALID_MATCHES or player not in VALID_PLAYERS:
        return jsonify({"error": "Unknown match or player"}), 400
    data   = request.json or {}
    action = data.get("action")
    amount = int(data.get("amount", 1))
    with lock:
        if action == "increase":
            state[match][player]["life"] += amount
        elif action == "decrease":
            state[match][player]["life"] -= amount
        elif action == "reset":
            state[match][player]["life"] = 20
        elif action == "set":
            state[match][player]["life"] = amount
        else:
            return jsonify({"error": "Unknown action"}), 400
        return jsonify(state[match][player])

@app.route("/api/name/<match>/<player>", methods=["POST"])
def update_name(match, player):
    if match not in VALID_MATCHES or player not in VALID_PLAYERS:
        return jsonify({"error": "Unknown match or player"}), 400
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400
    with lock:
        state[match][player]["name"] = name
        return jsonify(state[match][player])

@app.route("/api/timer/<match>", methods=["POST"])
def timer_action(match):
    if match not in VALID_MATCHES:
        return jsonify({"error": "Unknown match"}), 400
    data   = request.json or {}
    action = data.get("action")
    with lock:
        t = state[match]["timer"]
        if action == "start":
            if not t["running"]:
                # Don't start a finished countdown
                if not t["count_up"] and t["seconds"] <= 0:
                    return jsonify(timer_snapshot(t))
                t["last_tick"] = time.time()
                t["running"]   = True
        elif action == "pause":
            if t["running"]:
                # Freeze the current value
                t["seconds"]  = current_timer_seconds(t)
                t["last_tick"] = None
                t["running"]   = False
        elif action == "reset":
            t["running"]   = False
            t["last_tick"] = None
            t["seconds"]   = 0 if t["count_up"] else COUNTDOWN_SECONDS
        elif action == "set_mode":
            # Pause and reset whenever mode changes
            t["running"]   = False
            t["last_tick"] = None
            t["count_up"]  = bool(data.get("count_up", False))
            t["seconds"]   = 0 if t["count_up"] else COUNTDOWN_SECONDS
        else:
            return jsonify({"error": "Unknown action"}), 400
        return jsonify(timer_snapshot(t))

@app.route("/api/score/<match>/<player>", methods=["POST"])
def update_score(match, player):
    if match not in VALID_MATCHES or player not in VALID_PLAYERS:
        return jsonify({"error": "Unknown match or player"}), 400
    data   = request.json or {}
    action = data.get("action")
    with lock:
        if action == "increase":
            state[match]["score"][player] += 1
        elif action == "decrease":
            state[match]["score"][player] = max(0, state[match]["score"][player] - 1)
        elif action == "reset":
            state[match]["score"]["player1"] = 0
            state[match]["score"]["player2"] = 0
        else:
            return jsonify({"error": "Unknown action"}), 400
        return jsonify(state[match]["score"])


def reset_match(match):
    if match not in VALID_MATCHES:
        return jsonify({"error": "Unknown match"}), 400
    with lock:
        state[match]["player1"]["life"] = 20
        state[match]["player2"]["life"] = 20
        return jsonify({
            "player1": state[match]["player1"],
            "player2": state[match]["player2"],
        })

@app.route("/api/reset/<match>", methods=["POST"])
def reset_match(match):
    if match not in VALID_MATCHES:
        return jsonify({"error": "Unknown match"}), 400
    with lock:
        state[match]["player1"]["life"] = 20
        state[match]["player2"]["life"] = 20
        return jsonify({
            "player1": state[match]["player1"],
            "player2": state[match]["player2"],
        })

@app.route("/api/reset_all", methods=["POST"])
def reset_all():
    with lock:
        for m in VALID_MATCHES:
            for p in VALID_PLAYERS:
                state[m][p]["life"] = 20
        return jsonify(state)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
