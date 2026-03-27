import os
import json
from pathlib import Path
from flask import Flask, jsonify, render_template
from data_loader import (
    get_roster_with_stats,
    get_category_leaders,
    calculate_h2h_matchup,
    get_free_agent_recommendations,
    get_ai_recommendations,
    get_league_teams
)

app = Flask(__name__)

# 初始化：如果 TOKEN_DIR=/data (Railway Volume)，確保初始 token 檔案存在
def initialize_token_file():
    """On Railway: copy initial token from env vars to /data/yahoo_token.json if not exists"""
    token_dir = os.environ.get('TOKEN_DIR', '.')
    token_path = Path(token_dir) / 'yahoo_token.json'

    # 如果 token 檔案已存在，跳過
    if token_path.exists():
        return

    # 嘗試從環境變數重建 token 檔案
    access_token = os.environ.get('YAHOO_ACCESS_TOKEN')
    refresh_token = os.environ.get('YAHOO_REFRESH_TOKEN')

    if access_token and refresh_token:
        try:
            token_data = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': 3600,
                'token_type': 'bearer',
                'scope': None,
                'created_at': int(__import__('time').time())
            }
            Path(token_dir).mkdir(parents=True, exist_ok=True)
            with open(token_path, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            print(f"[初始化] Token 檔案已建立: {token_path}")
        except Exception as e:
            print(f"[警告] 無法建立 token 檔案: {e}")

initialize_token_file()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/roster/season")
def roster_season():
    """Get roster with full season stats"""
    return jsonify(get_roster_with_stats('season'))

@app.route("/api/roster/recent")
def roster_recent():
    """Get roster with last 15 game stats"""
    return jsonify(get_roster_with_stats('recent'))

@app.route("/api/roster")
def roster():
    """Get roster players with stats"""
    roster_data = get_roster_with_stats('season')
    # Transform to match frontend expectations
    players = []
    for p in roster_data['players']:
        if p.get('stats'):
            players.append({
                'name': p['name'],
                'team': p['team'],
                'position': '—',
                'status': 'Active',
                'games_played': 32,
                'games_remaining': 18,
                'trend': 'neutral',
                'injury': None,
                'avg': {
                    'pts': p['stats']['pts'],
                    'reb': p['stats']['reb'],
                    'ast': p['stats']['ast'],
                    'min': 28,
                    'threes': p['stats']['3pm'],
                    'fg_pct': p['stats']['fg_pct'],
                    'ft_pct': p['stats']['ft_pct'],
                    'stl': p['stats']['stl'],
                    'blk': p['stats']['blk'],
                    'fantasy_pts': 32,
                    'plus_minus': 2.5,
                    'dd2': 0,
                    'td3': 0,
                    'ranks': {
                        'pts': 15,
                        'reb': 20,
                        'ast': 18,
                        'fantasy_pts': 22
                    }
                }
            })
    return jsonify(players)

@app.route("/api/leaders")
def leaders():
    """Get category leaders in roster"""
    return jsonify(get_category_leaders())

@app.route("/api/stats")
def stats():
    """Get all roster stats data"""
    season = get_roster_with_stats('season')
    recent = get_roster_with_stats('recent')
    return jsonify({
        'season': season,
        'recent': recent,
        'leaders': get_category_leaders()
    })

@app.route("/api/matchup")
def matchup():
    """Get H2H matchup with real data"""
    try:
        return jsonify(calculate_h2h_matchup('season'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/news")
def news():
    """Get ticker news (mock data)"""
    return jsonify([
        {'severity': 'warning', 'player': 'LeBron James', 'message': '依舊因左腳踝傷缺陣', 'time': '2小時前'},
        {'severity': 'success', 'player': 'Kennedy Chandler', 'message': '全場8次助攻，創賽季新高', 'time': '12小時前'},
        {'severity': 'info', 'player': 'Deni Avdija', 'message': '本週對戰安排公布，4場比賽', 'time': '1天前'},
    ])

@app.route("/api/free-agents")
def free_agents():
    """Get free agent recommendations based on real data"""
    try:
        return jsonify(get_free_agent_recommendations(5))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/ai-recommendations")
def ai_recommendations():
    """Get AI recommendations based on real data"""
    try:
        return jsonify(get_ai_recommendations())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/league/teams")
def league_teams_api():
    """Get all league teams with rosters and player stats (Task 9)"""
    try:
        return jsonify(get_league_teams())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/token-status")
def token_status():
    """Check Yahoo OAuth token health (Task 6)"""
    try:
        from yahoo_config import load_token, is_token_expired, is_configured
        import time
        token = load_token()
        now = int(time.time())
        env_access = os.environ.get('YAHOO_ACCESS_TOKEN')
        env_refresh = os.environ.get('YAHOO_REFRESH_TOKEN')
        env_created = os.environ.get('YAHOO_TOKEN_CREATED_AT')
        if not token:
            return jsonify({
                'configured': False,
                'status': 'missing',
                'YAHOO_ACCESS_TOKEN_set': bool(env_access),
                'YAHOO_REFRESH_TOKEN_set': bool(env_refresh),
                'YAHOO_TOKEN_CREATED_AT_set': bool(env_created),
                'YAHOO_TOKEN_JSON_set': bool(os.environ.get('YAHOO_TOKEN_JSON')),
            })
        created_at = token.get('created_at', 0)
        expires_in = token.get('expires_in', 3600)
        elapsed = now - created_at
        remaining = max(0, expires_in - elapsed)
        # 判斷實際來源
        if env_access:
            source = 'env_individual'
        elif os.environ.get('YAHOO_TOKEN_JSON'):
            source = 'env_json'
        else:
            source = 'file'
        return jsonify({
            'configured': True,
            'status': 'expired' if remaining == 0 else ('expiring_soon' if remaining < 300 else 'ok'),
            'expires_in_seconds': int(remaining),
            'expires_in_minutes': round(remaining / 60, 1),
            'source': source,
            'created_at': created_at,
            'now': now,
            'elapsed_minutes': round(elapsed / 60, 1),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    import sys
    import io

    # Fix encoding for Windows terminal
    if sys.stdout.encoding.lower() in ['cp950', 'mbcs', 'utf-8']:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    port = int(os.environ.get('PORT', 5000))
    debug = not os.environ.get('RAILWAY_ENVIRONMENT')  # 部署環境關閉 debug

    print("\n" + "="*60)
    print("  Yahoo H2H Fantasy NBA Analysis Platform")
    print("="*60)
    print(f"\n  Port: {port}  |  Debug: {debug}")
    print("="*60 + "\n")
    app.run(debug=debug, host='0.0.0.0', port=port)
