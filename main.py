from dotenv import load_dotenv
from flask import Flask, render_template_string
from markupsafe import Markup
import os
import requests
from werkzeug.middleware.proxy_fix import ProxyFix

def find_player(name, app_id):
    query = f"https://api.worldoftanks.eu/wot/account/list/?application_id={app_id}&search={name}"
    r = requests.get(query).json()
    return r["data"][0]["account_id"]

def all_tanks_id(app_id):
    query = f"https://api.worldoftanks.eu/wot/encyclopedia/vehicles/?application_id={app_id}&fields=short_name%2Ctank_id"
    r = requests.get(query).json()
    return r

def find_tank_id(name, app_id):
    query = f"https://api.worldoftanks.eu/wot/account/list/?application_id={app_id}&search={name}"
    r = all_tanks_id(app_id)["data"].values() 
    return list(filter(lambda x: x["short_name"] == name, r))[0]["tank_id"]

def get_recent_battles(player_id, tank_id):
    query = f"https://api.tomato.gg/api/player/combined-battles/{player_id}?pageSize=10&sortBy=battle_time&sortDirection=desc&tankId={tank_id}"
    r = requests.get(query).json()["data"]
    return r

def get_most_recent_battle(player_id, tank_id):
    return get_recent_battles(player_id, tank_id)[0]

def get_player_stats(player_name, player_id):
    query = f"https://tomato.gg/_next/data/ChBl5gn1Emb2oRQwzfDlf/en/stats/{player_name}-{player_id}/EU.json?id={player_name}-{player_id}&server=EU"
    return requests.get(query).json()

def get_tank_moe(player_name, player_id, tank_id):
    stats = get_player_stats(player_name, player_id)
    tanks = stats.get("pageProps", {}).get("overallStats", {}).get("data", {}).get("tanks", [])
    tank = next((t for t in tanks if t["id"] == tank_id), None)

    if tank:
        return {
            "moe": tank.get("moe", 0),
            "mastery": tank.get("mastery", 0),
            "tank_image": tank.get("bigImage") or tank.get("image", "")
        }
    else:
        return {"moe": 0, "mastery": 0, "tank_image": ""}


load_dotenv()
app_id = os.getenv("APP_ID")
player_name = "Stesio10"
tank_name  = "EBR 105"
player_id = find_player(player_name, app_id)
tank_id = find_tank_id(tank_name, app_id)

app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

def format_moe_diff(moe_diff_str):
    try:
        diff = float(moe_diff_str)
    except Exception:
        return Markup('<span class="badge bg-secondary">n/a</span>')

    if diff > 0:
        return Markup(f'<span class="badge bg-success">▲ +{diff:.2f}</span>')
    elif diff < 0:
        return Markup(f'<span class="badge bg-danger">▼ {diff:.2f}</span>')
    else:
        return Markup('<span class="badge bg-secondary">0.00</span>')

def format_marks(marks):
    if marks == 3:
        return "*** (3 Marks)"
    elif marks == 2:
        return "** (2 Marks)"
    elif marks == 1:
        return "* (1 Mark)"
    else:
        return "No Marks"

@app.route("/")
def index():
    html = """
    <!doctype html>
    <html>
    <head>
      <title>Main site</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
      <div class="container py-5">
        <p><a href="/moe" class="btn btn-primary">Stesio10 EBR Tracker</a></p>
      </div>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route("/moe")
def moe_page():
    battles = get_recent_battles(player_id, tank_id)
    latest_battle = next(battle for battle in battles if float(battle.get("moe", 0)) != 0)
    # Get tank stats from overall MOE (to check 3 marks)
    tank_stats = get_tank_moe(player_name, player_id, tank_id)
    tank_image = tank_stats["tank_image"]
    overall_moe_marks = tank_stats["moe"]  # integer marks 0-3
    three_marks_answer = "Yes" if overall_moe_marks >= 3 else "No"

    
    # Current MOE progress comes from the most recent battle
    if latest_battle:
        try:
            current_moe_percent = float(latest_battle["moe"])  # e.g., 91.99%
        except Exception:
            current_moe_percent = 0.0

        try:
            moe_diff = float(latest_battle.get("moe_diff", 0))
        except Exception:
            moe_diff = 0.0

        progress_text = f"{current_moe_percent:.2f}% (Δ {moe_diff:+.2f}%)"
    else:
        progress_text = "0.00% (Δ 0.00%)"

    html = """
    <!doctype html>
    <html>
    <head>
      <title>MOE Dashboard</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

      <style>
        body { background: #0f1115; color: white; }
        .page-wrapper { display: flex; gap: 20px; align-items: flex-start; }
        .left-widget {
            width: 250px;
            background: #1a1d25;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            flex-shrink: 0;
        }
        .left-widget img { width: 150px; margin-bottom: 10px; border-radius: 8px; }
        .left-widget .progress-text { font-size: 18px; font-weight: bold; margin-top: 8px; color: #ffd700; }
        .left-widget .three-marks { font-size: 16px; margin-top: 6px; color: #00ff00; }
        .battle-card {
            background: #1a1d25;
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
        }
        .tank { width: 140px; text-align: center; }
        .tank img { width: 110px; }
        .main { flex-grow: 1; padding-left: 15px; }
        .right { width: 200px; text-align: right; font-size: 14px; color: #9aa4b2; }
        .win { color: #4caf50; }
        .loss { color: #f44336; }
        .statline { font-size: 14px; color: #b0bac8; }
      </style>
    </head>

    <body>
      <div class="container py-4">
        <a href="/" class="btn btn-secondary mb-3">&larr; Back</a>
        <h3>Recent Battles — {{ player_name }} ({{ tank_name }})</h3>

        <div class="page-wrapper">
          <!-- Left Widget -->
          <div class="left-widget">
            <img src="{{ tank_image }}" alt="{{ tank_name }}">
            <div>{{ tank_name }}</div>
            <div class="progress-text">{{ progress_text }}</div>
            <div class="three-marks">3 marks? {{ three_marks_answer }}</div>
          </div>

          <!-- Battle Cards -->
          <div class="flex-grow-1">
          {% for b in battles %}
            <div class="battle-card">
                <div class="tank">
                    <img src="{{ b.image }}">
                    <div>{{ b.short_name }}</div>
                    <div class="text-muted">Tier {{ b.tier }}</div>
                </div>

                <div class="main">
                    <div><strong>{{ b.map }}</strong></div>
                    <div class="{{ 'win' if b.won else 'loss' }}">
                        {{ 'Victory' if b.won else 'Defeat' }}
                    </div>
                    <div class="statline">
                        Damage: {{ b.damage }} |
                        Frags: {{ b.frags }} |
                        Assist: {{ b.spotting_assist + b.tracking_assist }}
                    </div>
                    <div class="statline">
                        {{ 'Survived' if b.survived else 'Destroyed' }}
                        • {{ b.battle_time }}
                    </div>
                </div>

                <div class="right">
                    <div>MOE: {{ b.moe }}%</div>
                    <div>Δ MOE: {{ b.moe_diff }}</div>
                    <div>WN8: {{ b.wn8 }}</div>
                    <div>XP: {{ b.base_xp }}</div>
                    <div>Credits: {{ b.net_credit_earnings }}</div>
                </div>
            </div>
          {% endfor %}
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    return render_template_string(
        html,
        battles=battles,
        player_name=player_name,
        tank_name=tank_name,
        tank_image=tank_image,
        progress_text=progress_text,
        three_marks_answer=three_marks_answer
    )
