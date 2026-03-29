"""
Data loader for Yahoo H2H Fantasy League
Reads from: players_data.json, my_roster.json
"""

import json
import os
import unicodedata

def normalize(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()

def load_players_data():
    """Load all player data from players_data.json"""
    with open('players_data.json', encoding='utf-8') as f:
        return json.load(f)

def load_my_roster():
    """Load user's roster from my_roster.json"""
    with open('my_roster.json', encoding='utf-8') as f:
        return json.load(f)

def find_player(players_list, name):
    """Find player by normalized name matching"""
    name_norm = normalize(name)
    parts = name_norm.split()
    first = parts[0] if len(parts) >= 2 else ""
    last = parts[-1]

    # Exact match
    for p in players_list:
        if normalize(p['PLAYER_NAME']) == name_norm:
            return p

    # First + last name match
    if first:
        for p in players_list:
            pn = normalize(p['PLAYER_NAME'])
            if first in pn and last in pn:
                return p

    return None

def get_roster_with_stats(period='season'):
    """
    Get user's roster with player stats
    period: 'season' | 'recent' | '7d' | '14d' | '30d'
    """
    roster = load_my_roster()
    result = {'league': roster['league_info'], 'players': []}

    # 7d/14d/30d: use nba_live to fetch live NBA API stats
    if period in ('7d', '14d', '30d'):
        n = int(period.replace('d', ''))
        try:
            from data.nba_live import _fetch_n_game_stats, _find_player, _f
            raw = _fetch_n_game_stats(n)
            for rp in roster['roster']:
                row = _find_player(raw, rp['api_name'])
                if row:
                    result['players'].append({
                        'id': rp['id'],
                        'name': rp['name'],
                        'position': rp.get('position', '—'),
                        'team': row.get('TEAM_ABBREVIATION', '—'),
                        'gp': int(row.get('GP', 0)),
                        'stats': {
                            'fg_pct': _f(row, 'FG_PCT', scale=100),
                            'ft_pct': _f(row, 'FT_PCT', scale=100),
                            '3pm':    _f(row, 'FG3M'),
                            'pts':    _f(row, 'PTS'),
                            'reb':    _f(row, 'REB'),
                            'ast':    _f(row, 'AST'),
                            'stl':    _f(row, 'STL'),
                            'blk':    _f(row, 'BLK'),
                            'to':     _f(row, 'TOV'),
                        }
                    })
                else:
                    result['players'].append({
                        'id': rp['id'], 'name': rp['name'],
                        'position': rp.get('position', '—'),
                        'team': '—', 'gp': 0, 'stats': None
                    })
            return result
        except Exception as e:
            print(f"[data_loader] nba_live L{n} 失敗，回退到整季: {e}")
            period = 'season'

    data = load_players_data()

    # Select correct data period
    if period == 'recent':
        players_list = data['recent']['players']
    else:
        players_list = data['season']['players']

    for roster_player in roster['roster']:
        player_data = find_player(players_list, roster_player['api_name'])

        if player_data:
            result['players'].append({
                'id': roster_player['id'],
                'name': roster_player['name'],
                'position': roster_player.get('position', '—'),
                'team': player_data['TEAM_ABBREVIATION'],
                'gp': int(player_data['GP']),
                'stats': {
                    'fg_pct': round(player_data['FG_PCT'] * 100, 1),
                    'ft_pct': round(player_data['FT_PCT'] * 100, 1),
                    '3pm': round(player_data['FG3M'], 1),
                    'pts': round(player_data['PTS'], 1),
                    'reb': round(player_data['REB'], 1),
                    'ast': round(player_data['AST'], 1),
                    'stl': round(player_data['STL'], 1),
                    'blk': round(player_data['BLK'], 1),
                    'to': round(player_data['TOV'], 1),
                }
            })
        else:
            result['players'].append({
                'id': roster_player['id'],
                'name': roster_player['name'],
                'position': roster_player.get('position', '—'),
                'team': '—',
                'gp': 0,
                'stats': None,
                'status': 'Not Found'
            })

    return result

def get_category_leaders():
    """Get top 3 players in each category"""
    data = load_players_data()
    roster = load_my_roster()
    players_list = data['season']['players']

    # Find all roster players' stats
    roster_stats = []
    for r_player in roster['roster']:
        p_data = find_player(players_list, r_player['api_name'])
        if p_data and p_data['GP'] > 0:
            roster_stats.append({
                'name': r_player['name'],
                'fg_pct': p_data['FG_PCT'] * 100,
                'ft_pct': p_data['FT_PCT'] * 100,
                '3pm': p_data['FG3M'],
                'pts': p_data['PTS'],
                'reb': p_data['REB'],
                'ast': p_data['AST'],
                'stl': p_data['STL'],
                'blk': p_data['BLK'],
                'to': p_data['TOV'],
            })

    # Get top 3 per category
    leaders = {}
    for cat in ['fg_pct', 'ft_pct', '3pm', 'pts', 'reb', 'ast', 'stl', 'blk']:
        sorted_cat = sorted(roster_stats, key=lambda x: x[cat], reverse=True)[:3]
        leaders[cat] = [{'name': p['name'], 'value': round(p[cat], 1)} for p in sorted_cat]

    # TO is opposite (lower is better)
    to_sorted = sorted(roster_stats, key=lambda x: x['to'])[:3]
    leaders['to'] = [{'name': p['name'], 'value': round(p['to'], 1)} for p in to_sorted]

    return leaders

def calculate_team_stats(roster_players, players_list, use_totals=False):
    """
    Calculate aggregate stats for a roster of 16 players
    use_totals=True: SUM for counting stats (PTS/REB/AST/STL/BLK/3PM/TO), AVG for FG%/FT%
    use_totals=False: AVG for all (used for weak category detection in FA recommendations)
    """
    SUM_CATEGORIES = {'3pm', 'pts', 'reb', 'ast', 'stl', 'blk', 'to'}

    stats = {
        'fg_pct': [],
        'ft_pct': [],
        '3pm': [],
        'pts': [],
        'reb': [],
        'ast': [],
        'stl': [],
        'blk': [],
        'to': [],
    }

    for player_data in roster_players:
        if player_data and player_data.get('GP', 0) > 0:
            stats['fg_pct'].append(player_data['FG_PCT'] * 100)
            stats['ft_pct'].append(player_data['FT_PCT'] * 100)
            stats['3pm'].append(player_data['FG3M'])
            stats['pts'].append(player_data['PTS'])
            stats['reb'].append(player_data['REB'])
            stats['ast'].append(player_data['AST'])
            stats['stl'].append(player_data['STL'])
            stats['blk'].append(player_data['BLK'])
            stats['to'].append(player_data['TOV'])

    result = {}
    for cat, values in stats.items():
        if values:
            if use_totals and cat in SUM_CATEGORIES:
                result[cat] = round(sum(values), 1)
            else:
                result[cat] = round(sum(values) / len(values), 2)
        else:
            result[cat] = 0

    return result

def generate_opponent_roster(exclude_names):
    """
    Generate a mock opponent roster using real players from players_data.json
    Excludes players already in user's roster
    """
    data = load_players_data()
    all_players = data['season']['players']
    roster = load_my_roster()

    # Normalize exclude names
    exclude_norm = [normalize(name) for name in exclude_names]

    # Select 16 players not in user's roster
    opponent_players = []
    for player in all_players:
        if (len(opponent_players) < 16 and
            player['GP'] > 5 and  # Only active players
            normalize(player['PLAYER_NAME']) not in exclude_norm):
            opponent_players.append(player)

    return opponent_players

def calculate_h2h_matchup(period='season'):
    """
    Calculate H2H matchup comparison between user and opponent
    Returns detailed category comparison
    """
    data = load_players_data()
    roster = load_my_roster()

    # Get correct period data
    if period == 'recent':
        players_list = data['recent']['players']
    else:
        players_list = data['season']['players']

    # Get user roster stats
    user_players = []
    user_names = []
    for r_player in roster['roster']:
        p_data = find_player(players_list, r_player['api_name'])
        if p_data:
            user_players.append(p_data)
            user_names.append(r_player['name'])

    user_stats = calculate_team_stats(user_players, players_list, use_totals=True)

    # 嘗試從 Yahoo API 取得真實對手數據
    opponent_name = 'Computer Opponent'
    is_real_data = False
    yahoo_opp_stats = None
    yahoo_my_stats = None

    try:
        from yahoo_api import get_opponent_info, get_team_stats_for_week, get_my_stats_for_week
        from yahoo_config import CURRENT_WEEK

        opp_info = get_opponent_info(CURRENT_WEEK)
        if opp_info:
            yahoo_opp_stats = get_team_stats_for_week(opp_info['team_key'], CURRENT_WEEK)
            yahoo_my_stats = get_my_stats_for_week(CURRENT_WEEK)
            if yahoo_opp_stats and yahoo_my_stats:
                opponent_name = opp_info['name']
                is_real_data = True
    except Exception as e:
        print(f"[data_loader] Yahoo API 不可用，使用模擬數據: {e}")

    # 若 Yahoo API 失敗，使用模擬對手
    if not is_real_data:
        opponent_players = generate_opponent_roster(user_names)
        opponent_stats = calculate_team_stats(opponent_players, players_list, use_totals=True)
    else:
        # Yahoo API 欄位名稱對應到 categories 使用的 key
        # yahoo: tov→to, threepm→3pm
        def normalize(stats):
            return {
                'fg_pct':  stats.get('fg_pct', 0),
                'ft_pct':  stats.get('ft_pct', 0),
                '3pm':     stats.get('threepm', 0),
                'pts':     stats.get('pts', 0),
                'reb':     stats.get('reb', 0),
                'ast':     stats.get('ast', 0),
                'stl':     stats.get('stl', 0),
                'blk':     stats.get('blk', 0),
                'to':      stats.get('tov', 0),
            }
        user_stats = normalize(yahoo_my_stats)
        opponent_stats = normalize(yahoo_opp_stats)

    # Determine winners for each category
    categories = [
        ('FG%', 'fg_pct', False),      # False = higher is better
        ('FT%', 'ft_pct', False),
        ('3PM', '3pm', False),
        ('PTS', 'pts', False),
        ('REB', 'reb', False),
        ('AST', 'ast', False),
        ('STL', 'stl', False),
        ('BLK', 'blk', False),
        ('TO', 'to', True),             # True = lower is better
    ]

    matchup_data = []
    user_wins = 0
    opponent_wins = 0

    for label, key, reverse in categories:
        user_val = user_stats[key]
        opp_val = opponent_stats[key]

        if reverse:
            if user_val < opp_val:
                status = 'winning'; user_wins += 1
            elif user_val > opp_val:
                status = 'losing'; opponent_wins += 1
            else:
                status = 'tied'
        else:
            if user_val > opp_val:
                status = 'winning'; user_wins += 1
            elif user_val < opp_val:
                status = 'losing'; opponent_wins += 1
            else:
                status = 'tied'

        diff = round(abs(user_val - opp_val), 2)
        matchup_data.append({
            'label': label,
            'my': round(user_val, 1),
            'opp': round(opp_val, 1),
            'status': status,
            'diff': f"{'+' if user_val >= opp_val else ''}{diff}",
            'lower_is_better': reverse
        })

    return {
        'record': f"{user_wins}W-{opponent_wins}L-{9 - user_wins - opponent_wins}T",
        'wins': user_wins,
        'losses': opponent_wins,
        'opponent': opponent_name,
        'is_real_data': is_real_data,
        'categories': matchup_data
    }

def get_free_agent_recommendations(limit=5):
    """
    Recommend free agents based on user roster deficiencies.
    Uses all league team rosters to determine true free agents.
    """
    data = load_players_data()
    all_players = data['season']['players']
    roster = load_my_roster()

    # Get user roster stats and names
    user_players = []
    user_names = []
    for r_player in roster['roster']:
        p_data = find_player(all_players, r_player['api_name'])
        if p_data:
            user_players.append(p_data)
            user_names.append(r_player['name'])

    user_stats = calculate_team_stats(user_players, all_players)

    # Find weakest categories (use averages for comparison)
    weak_cats = sorted(user_stats.items(), key=lambda x: x[1])[:3]
    weak_keys = [cat[0] for cat in weak_cats]

    # Build rostered names set from ALL league teams (not just user's roster)
    try:
        from yahoo_api import get_all_teams_with_rosters
        all_teams = get_all_teams_with_rosters()
        rostered_names_norm = set()
        for team in all_teams:
            for player in team.get('players', []):
                rostered_names_norm.add(normalize(player['name']))
        print(f"[FA] 取得全聯盟陣容：{len(rostered_names_norm)} 位球員已被選走")
    except Exception as e:
        print(f"[FA] Yahoo API 失敗，僅排除自己陣容: {e}")
        rostered_names_norm = {normalize(n) for n in user_names}

    candidates = []

    for player in all_players:
        if (player['GP'] > 10 and
            normalize(player['PLAYER_NAME']) not in rostered_names_norm):
            score = 0
            if 'pts' in weak_keys:
                score += player['PTS'] * 0.5
            if '3pm' in weak_keys:
                score += player['FG3M'] * 2
            if 'ast' in weak_keys:
                score += player['AST'] * 0.8
            if 'reb' in weak_keys:
                score += player['REB'] * 0.4
            if 'stl' in weak_keys:
                score += player['STL'] * 3
            if 'blk' in weak_keys:
                score += player['BLK'] * 3

            if score > 0:
                candidates.append((player, score))

    # Sort by score and return top N
    candidates.sort(key=lambda x: x[1], reverse=True)

    return [
        {
            'name': p[0]['PLAYER_NAME'],
            'team': p[0]['TEAM_ABBREVIATION'],
            'position': '—',
            'match_score': round(p[1] / 10, 1),
            'recommendation': '強烈推薦' if p[1] > 50 else '推薦',
            'ownership': 25,
            'add_trend': '↑ +5%',
            'rank_fantasy': int(p[0].get('NBA_FANTASY_PTS_RANK', 200)),
            'avg_7d': {
                'pts': round(p[0]['PTS'], 1),
                'reb': round(p[0]['REB'], 1),
                'ast': round(p[0]['AST'], 1),
                'stl': round(p[0]['STL'], 1),
                'threes': round(p[0]['FG3M'], 1),
                'fantasy_pts': round(p[0]['NBA_FANTASY_PTS'], 1),
                'ft_pct': round(p[0]['FT_PCT'] * 100, 1),
                'plus_minus': round(p[0]['PLUS_MINUS'], 1)
            },
            'reason': f"補強 {', '.join(weak_keys)} 不足"
        }
        for p in candidates[:limit]
    ]

def get_all_free_agents(offset=0, limit=30, sort='rank'):
    """
    回傳所有 FA 球員（分頁），並標記推薦球員
    sort: 'rank' | 'pts' | 'reb' | 'ast'
    """
    data = load_players_data()
    all_players = data['season']['players']

    # 取得全聯盟已選球員
    try:
        from yahoo_api import get_all_teams_with_rosters
        all_teams = get_all_teams_with_rosters()
        rostered = {normalize(p['name']) for t in all_teams for p in t.get('players', [])}
    except Exception as e:
        print(f"[FA] Yahoo 失敗，改用本地陣容: {e}")
        rostered = {normalize(p['name']) for p in load_my_roster()['roster']}

    # 取得推薦球員名單
    try:
        rec_names = {normalize(r['name']) for r in get_free_agent_recommendations(10)}
    except Exception:
        rec_names = set()

    # 建立近期出賽 map（recent section = 近 15 場），GP=0 視為受傷/停賽
    recent_players = data.get('recent', {}).get('players', [])
    recent_gp_map = {normalize(p['PLAYER_NAME']): p.get('GP', 0) for p in recent_players}

    # 建立 FA 位置 map（Yahoo API，每日快取）
    fa_pos_map = {}
    try:
        from yahoo_api import get_fa_players_positions
        fa_pos_map = get_fa_players_positions()
    except Exception:
        pass

    # 篩選 FA：賽季場次 > 10、未被任何隊選走、近期有出賽（過濾長期傷兵）
    fas = [
        p for p in all_players
        if p.get('GP', 0) > 10
        and normalize(p['PLAYER_NAME']) not in rostered
        and recent_gp_map.get(normalize(p['PLAYER_NAME']), 0) > 0
    ]

    # 排序
    sort_keys = {
        'rank': lambda p: p.get('NBA_FANTASY_PTS_RANK', 9999),
        'pts':  lambda p: -p.get('PTS', 0),
        'reb':  lambda p: -p.get('REB', 0),
        'ast':  lambda p: -p.get('AST', 0),
    }
    fas.sort(key=sort_keys.get(sort, sort_keys['rank']))

    total = len(fas)
    page = fas[offset: offset + limit]

    return {
        'total': total,
        'offset': offset,
        'limit': limit,
        'has_more': (offset + limit) < total,
        'players': [
            {
                'name': p['PLAYER_NAME'],
                'team': p['TEAM_ABBREVIATION'],
                'position': fa_pos_map.get(p['PLAYER_NAME'].lower(), '—'),
                'rank_fantasy': int(p.get('NBA_FANTASY_PTS_RANK', 999)),
                'recommended': normalize(p['PLAYER_NAME']) in rec_names,
                'avg': {
                    'pts':       round(p['PTS'], 1),
                    'reb':       round(p['REB'], 1),
                    'ast':       round(p['AST'], 1),
                    'stl':       round(p['STL'], 1),
                    'threes':    round(p['FG3M'], 1),
                    'fg_pct':    round(p['FG_PCT'] * 100, 1),
                    'ft_pct':    round(p['FT_PCT'] * 100, 1),
                    'plus_minus': round(p['PLUS_MINUS'], 1),
                }
            }
            for p in page
        ]
    }


def get_league_teams():
    """
    取得全聯盟所有隊伍陣容，並對照 players_data.json 補充球員統計
    回傳: list of team dicts，每個包含 players 清單（附帶賽季均值）
    """
    try:
        from yahoo_api import get_all_teams_with_rosters, get_league_standings
        teams = get_all_teams_with_rosters()
        standings = get_league_standings()
        print(f"[data_loader] 取得聯盟陣容: {len(teams)} 隊，排名: {len(standings)} 隊")
    except Exception as e:
        print(f"[data_loader] 無法取得聯盟陣容: {e}")
        import traceback
        traceback.print_exc()
        return []

    if not teams:
        print(f"[data_loader] 警告: teams 為空，standings = {standings}")
        return []

    data = load_players_data()
    players_list = data['season']['players']

    result = []
    for team in teams:
        record = standings.get(team['team_key'], {})

        enriched_players = []
        for p in team['players']:
            p_data = find_player(players_list, p['name'])
            player_info = {
                'name': p['name'],
                'position': p['position'],
            }
            if p_data and p_data.get('GP', 0) > 0:
                player_info['nba_team'] = p_data['TEAM_ABBREVIATION']
                player_info['stats'] = {
                    'pts': round(p_data['PTS'], 1),
                    'reb': round(p_data['REB'], 1),
                    'ast': round(p_data['AST'], 1),
                    'stl': round(p_data['STL'], 1),
                    'blk': round(p_data['BLK'], 1),
                    'fg_pct': round(p_data['FG_PCT'] * 100, 1),
                    'ft_pct': round(p_data['FT_PCT'] * 100, 1),
                    '3pm': round(p_data['FG3M'], 1),
                    'gp': int(p_data['GP']),
                }
            else:
                player_info['nba_team'] = '—'
                player_info['stats'] = None
            enriched_players.append(player_info)

        result.append({
            'team_key': team['team_key'],
            'team_id': team['team_id'],
            'name': team['name'],
            'is_my_team': team['is_my_team'],
            'wins': record.get('wins', 0),
            'losses': record.get('losses', 0),
            'ties': record.get('ties', 0),
            'players': enriched_players
        })

    return result


def get_ai_recommendations():
    """
    Generate AI recommendations based on roster analysis
    """
    data = load_players_data()
    all_players = data['season']['players']
    roster = load_my_roster()

    # Analyze user roster
    user_stats = {}
    high_performers = []
    underperformers = []

    for r_player in roster['roster']:
        p_data = find_player(all_players, r_player['api_name'])
        if p_data and p_data['GP'] > 5:
            user_stats[r_player['name']] = {
                'pts': p_data['PTS'],
                'gp': p_data['GP'],
                'fantasy_pts': p_data['NBA_FANTASY_PTS']
            }

            # Categorize players
            if p_data['NBA_FANTASY_PTS'] > 20:
                high_performers.append(r_player['name'])
            elif p_data['NBA_FANTASY_PTS'] < 10 and p_data['GP'] > 10:
                underperformers.append(r_player['name'])

    recommendations = []

    # Recommendation 1: Monitor high performers
    if high_performers:
        recommendations.append({
            'player': high_performers[0],
            'priority': 'medium',
            'type': 'schedule',
            'action': 'Monitor',
            'reason': f"{high_performers[0]} is performing well. Monitor schedule for favorable matchups.",
            'drop_suggestion': None
        })

    # Recommendation 2: Consider benching underperformers
    if underperformers:
        recommendations.append({
            'player': underperformers[0],
            'priority': 'high',
            'type': 'warning',
            'action': 'Review',
            'reason': f"{underperformers[0]} has low production recently. Consider trading or benching.",
            'drop_suggestion': f"Monitor injury status for {underperformers[0]}"
        })

    # Recommendation 3: General advice
    recommendations.append({
        'player': 'Roster Management',
        'priority': 'low',
        'type': 'add',
        'action': 'Optimize',
        'reason': 'Review free agent pool for potential upgrades in weak categories.',
        'drop_suggestion': None
    })

    return recommendations

if __name__ == "__main__":
    # Test
    roster = get_roster_with_stats('season')
    print(f"Loaded {len(roster['players'])} players")
    print(f"League: {roster['league']['name']}")

    # Test H2H matchup
    matchup = calculate_h2h_matchup()
    print(f"\nMatchup record: {matchup['record']}")

    # Test free agents
    fas = get_free_agent_recommendations(3)
    print(f"\nTop free agents: {len(fas)} recommended")
