#!/usr/bin/env python3
"""
Generate roster reports for Yahoo H2H Fantasy League
Shows per-game averages for 9 statistical categories:
FG%, FT%, 3PM, PTS, REB, AST, STL, BLK, TO
"""

import json
import sys
import unicodedata
from datetime import datetime

def normalize(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()

def load_data():
    with open('players_data.json', encoding='utf-8') as f:
        players_data = json.load(f)
    with open('my_roster.json', encoding='utf-8') as f:
        my_roster = json.load(f)
    return players_data, my_roster

def find_player(players_dict, name):
    """Find player in dict by normalized name matching."""
    name_norm = normalize(name)
    parts = name_norm.split()
    first = parts[0] if len(parts) >= 2 else ""
    last = parts[-1]

    # Exact match
    for pname in players_dict:
        if normalize(pname) == name_norm:
            return players_dict[pname]

    # First + last name
    if first:
        for pname in players_dict:
            pn = normalize(pname)
            if first in pn and last in pn:
                return players_dict[pname]

    return None

def generate_report(period="recent"):
    """
    Generate H2H roster report with 9-category stats.
    period: 'recent' (L15) or 'season' (full season)
    """
    players_data, my_roster = load_data()

    # Build lookup dicts
    if period == "recent":
        players_dict = {p['PLAYER_NAME']: p for p in players_data['recent']['players']}
        title = "近 15 場平均 (H2H)"
    else:
        players_dict = {p['PLAYER_NAME']: p for p in players_data['season']['players']}
        title = "整季平均 (H2H)"

    # Match roster with player data
    roster_with_stats = []
    for roster_player in my_roster['roster']:
        name = roster_player['api_name']
        player_data = find_player(players_dict, name)

        if player_data:
            roster_with_stats.append({
                'roster': roster_player,
                'stats': player_data,
                'found': True
            })
        else:
            roster_with_stats.append({
                'roster': roster_player,
                'stats': None,
                'found': False
            })

    # Generate output
    output = f"\n╔{'═'*135}╗\n"
    output += f"║  {my_roster['league_info']['name']:^130}  ║\n"
    output += f"║  {title} - 2025-26 季度 ({datetime.now().strftime('%Y-%m-%d')}){'':>78}║\n"
    output += f"╚{'═'*135}╝\n\n"

    # Header with 9 stat categories
    output += "球員名              隊伍  出賽   FG%   FT%   3PM   PTS   REB   AST   STL   BLK    TO\n"
    output += "─" * 138 + "\n"

    stats_collection = []

    for item in roster_with_stats:
        name = item['roster']['name'][:18].ljust(18)
        team = item['roster']['team'].ljust(4)

        if not item['found'] or item['stats'] is None or item['stats']['GP'] == 0:
            output += f"{name} {team} ❌ 無當季數據\n"
        else:
            stats = item['stats']

            # Collect stats for summary
            stats_collection.append({
                'name': item['roster']['name'],
                'team': stats['TEAM_ABBREVIATION'],
                'gp': int(stats['GP']),
                'fg_pct': stats['FG_PCT'] * 100,
                'ft_pct': stats['FT_PCT'] * 100,
                '3pm': stats['FG3M'],
                'pts': stats['PTS'],
                'reb': stats['REB'],
                'ast': stats['AST'],
                'stl': stats['STL'],
                'blk': stats['BLK'],
                'to': stats['TOV'],
            })

            output += (f"{name} {team} "
                      f"{int(stats['GP']):2}   "
                      f"{stats['FG_PCT']*100:5.1f}% {stats['FT_PCT']*100:5.1f}% "
                      f"{stats['FG3M']:5.1f} {stats['PTS']:5.1f} {stats['REB']:5.1f} "
                      f"{stats['AST']:5.1f} {stats['STL']:5.1f} {stats['BLK']:5.1f} "
                      f"{stats['TOV']:6.1f}\n")

    output += "─" * 138 + "\n"

    # Summary statistics
    if stats_collection:
        output += f"\n陣容統計彙總 ({len(stats_collection)}/{my_roster['league_info']['roster_size']} 球員):\n\n"

        output += "平均數據:\n"
        avg_fg = sum(s['fg_pct'] for s in stats_collection) / len(stats_collection)
        avg_ft = sum(s['ft_pct'] for s in stats_collection) / len(stats_collection)
        avg_3pm = sum(s['3pm'] for s in stats_collection) / len(stats_collection)
        avg_pts = sum(s['pts'] for s in stats_collection) / len(stats_collection)
        avg_reb = sum(s['reb'] for s in stats_collection) / len(stats_collection)
        avg_ast = sum(s['ast'] for s in stats_collection) / len(stats_collection)
        avg_stl = sum(s['stl'] for s in stats_collection) / len(stats_collection)
        avg_blk = sum(s['blk'] for s in stats_collection) / len(stats_collection)
        avg_to = sum(s['to'] for s in stats_collection) / len(stats_collection)

        output += (f"  FG%: {avg_fg:5.1f}%  FT%: {avg_ft:5.1f}%  3PM: {avg_3pm:5.1f}  PTS: {avg_pts:5.1f}\n"
                  f"  REB: {avg_reb:5.1f}    AST: {avg_ast:5.1f}   STL: {avg_stl:5.1f}  BLK: {avg_blk:5.1f}  TO: {avg_to:5.1f}\n")

        # Top performers by category
        output += f"\n各項類別前 3 名:\n"

        categories = [
            ('FG%', 'fg_pct'),
            ('FT%', 'ft_pct'),
            ('3PM', '3pm'),
            ('PTS', 'pts'),
            ('REB', 'reb'),
            ('AST', 'ast'),
            ('STL', 'stl'),
            ('BLK', 'blk'),
        ]

        for cat_name, cat_key in categories:
            if cat_key == 'fg_pct' or cat_key == 'ft_pct':
                top_3 = sorted(stats_collection, key=lambda x: x[cat_key], reverse=True)[:3]
                output += f"  {cat_name:4}: "
                output += ", ".join([f"{s['name'][:12]}({s[cat_key]:5.1f}%)" for s in top_3])
            else:
                top_3 = sorted(stats_collection, key=lambda x: x[cat_key], reverse=True)[:3]
                output += f"  {cat_name:4}: "
                output += ", ".join([f"{s['name'][:12]}({s[cat_key]:5.1f})" for s in top_3])
            output += "\n"

    return output

if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "recent"
    report = generate_report(period)
    sys.stdout.buffer.write(report.encode('utf-8'))
