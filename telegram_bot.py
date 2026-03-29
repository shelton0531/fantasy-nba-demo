"""
Fantasy NBA Telegram Bot
ä¸»é¸?®ï??‘ç???®¹ / ?¬é€±å???/ ?¥è©¢?ƒå“¡ / ?¯ç??’å? / ä»Šæ—¥è³½ç?
å®šæ??¨æ’­ï¼?9:00 å°æˆ°?´æ–° / 14:00 ?ƒå“¡?¥å ± / ?±ä? 14:00 ?¬é€±ç???"""

import os
import json
import logging
from datetime import datetime, time as datetime_time, date
from pathlib import Path

import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TAIPEI_TZ = pytz.timezone("Asia/Taipei")
CACHE_DIR = Path("cache")

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?³æ???®¹ï¼ˆYahoo API + æ¯æ—¥å¿«å?ï¼?# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def get_live_roster_cached() -> list[dict]:
    """
    ?–å??³æ???®¹ï¼Œå„ª?ˆè?ä»Šæ—¥å¿«å?ï¼Œå¦?‡å? Yahoo API ?“å???    æ¯ä??ƒå“¡?å‚³ï¼š{name, position, status, injury_note, player_key, team}
    å¤±æ???fallback ??my_roster.json??    """
    cache_path = CACHE_DIR / f"roster_{date.today().isoformat()}.json"

    # è®€ä»Šæ—¥å¿«å?
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # å¾?Yahoo API ?“å?
    try:
        from yahoo_api import get_my_roster_with_keys
        from data_loader import load_players_data

        yahoo_players = get_my_roster_with_keys()
        if not yahoo_players:
            raise ValueError("Yahoo ?å‚³ç©ºé™£å®?)

        # å¾?players_data.json è£œå??ƒé?ç¸®å¯«
        season_players = load_players_data().get("season", {}).get("players", [])
        team_map = {p["PLAYER_NAME"].lower(): p["TEAM_ABBREVIATION"] for p in season_players}

        roster = [
            {
                "name":         p["name"],
                "position":     p["position"],
                "status":       p["status"],
                "injury_note":  p["injury_note"],
                "player_key":   p["player_key"],
                "team":         team_map.get(p["name"].lower(), "??),
            }
            for p in yahoo_players
        ]

        CACHE_DIR.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(roster, ensure_ascii=False), encoding="utf-8")
        logger.info(f"[Roster] ?³æ???®¹å·²æ›´?°ï?{len(roster)} ä½ç???)
        return roster

    except Exception as e:
        logger.warning(f"[Roster] Yahoo ?“å?å¤±æ?ï¼Œæ”¹??my_roster.jsonï¼š{e}")
        try:
            with open("my_roster.json", encoding="utf-8") as f:
                roster_data = json.load(f)
            return [
                {
                    "name":        p["name"],
                    "position":    p.get("position", "??),
                    "status":      p.get("status", "Active"),
                    "injury_note": "",
                    "player_key":  "",
                    "team":        p.get("team", "??),
                }
                for p in roster_data.get("roster", [])
            ]
        except Exception:
            return []


# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# Inline Keyboard å·¥å?
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("?? ?‘ç???®¹", callback_data="menu_roster"),
         InlineKeyboardButton("?”ï? ?¬é€±å???, callback_data="menu_matchup")],
        [InlineKeyboardButton("?? ?¥è©¢?ƒå“¡", callback_data="menu_search"),
         InlineKeyboardButton("?? ?¯ç??’å?", callback_data="menu_standings")],
        [InlineKeyboardButton("?? ä»Šæ—¥è³½ç?", callback_data="menu_schedule")],
    ])

def roster_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("7å¤©å???, callback_data="roster_7d"),
         InlineKeyboardButton("14å¤©å???, callback_data="roster_14d")],
        [InlineKeyboardButton("?? ä»Šæ—¥?†æ?", callback_data="roster_report")],
        [InlineKeyboardButton("?¥ ?·å…µæ¦‚è¦½", callback_data="roster_injuries")],
        [InlineKeyboardButton("â¬…ï? è¿”å?ä¸»é¸??, callback_data="back_main")],
    ])

def matchup_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("?? ?¶å?å°æˆ°?¸æ?", callback_data="matchup_stats")],
        [InlineKeyboardButton("?’¡ FA ?¿æ?å»ºè­°", callback_data="matchup_fa")],
        [InlineKeyboardButton("â¬…ï? è¿”å?ä¸»é¸??, callback_data="back_main")],
    ])

def schedule_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("?‘ç??ƒå“¡ä»Šæ—¥?ºè³½", callback_data="schedule_mine")],
        [InlineKeyboardButton("?¨éƒ¨ä»Šæ—¥è³½ç?", callback_data="schedule_all")],
        [InlineKeyboardButton("â¬…ï? è¿”å?ä¸»é¸??, callback_data="back_main")],
    ])

def back_kb(target="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï? è¿”å?", callback_data=target)]])

def player_list_kb(period: str) -> InlineKeyboardMarkup:
    """?ƒå“¡?¸æ??µç›¤ï¼?äººä??’ï??‚period: '7d' | '14d' | 'rpt'"""
    players = get_live_roster_cached()
    buttons = []
    row = []
    for i, p in enumerate(players):
        row.append(InlineKeyboardButton(p["name"], callback_data=f"pd_{period}_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("â¬…ï? è¿”å???®¹?¸å–®", callback_data="menu_roster")])
    return InlineKeyboardMarkup(buttons)

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# å·¥å…·ï¼šç???emoji
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def format_trend_line(label: str, v7: float, v14: float) -> str:
    """é¡¯ç¤º?®ä??¸æ???7å¤?vs 14å¤©è¶¨?¢ï?threshold 5%"""
    if v14 == 0:
        return f"   {label:4s}  {v7}"
    diff_pct = (v7 - v14) / v14
    if diff_pct > 0.05:
        arrow = "??
    elif diff_pct < -0.05:
        arrow = "??
    else:
        arrow = "="
    return f"   {label:4s}  {v7} {arrow}ï¼ˆvs {v14}ï¼?


def status_emoji(status: str) -> str:
    s = (status or "").upper()
    if s in ("INJ", "OUT", "NA"):
        return "?”´"
    if s in ("Q", "QUESTIONABLE", "DTD"):
        return "?Ÿ¡"
    return "?Ÿ¢"

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?¼å??–ï???®¹?¡ç?
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def format_roster_cards(players: list, period_label: str, today_teams: set) -> list[str]:
    """
    ?å‚³ list of strï¼Œæ??‡è??¯æ?å¤?4096 å­—å?
    today_teams: ä»Šæ—¥?‰è³½??NBA ?ƒé?ç¸®å¯« set
    """
    header = f"?? <b>?‘ç???®¹ ??{period_label}</b>\n\n"
    lines = []
    for p in players:
        s = p.get("stats") or {}
        if not s:
            lines.append(f"??{p['name']} ???¡æ•¸?š\n")
            continue
        team = p.get("team", "??)
        pos  = p.get("position", "??)
        gp   = p.get("gp", 0)
        has_game = "?Ÿ¢" if team in today_teams else "??
        lines.append(
            f"\n{has_game} <b>{p['name']}</b>  {team} Â· {pos} Â· {gp}?´\n"
            f"   PTS {s.get('pts',0)} | REB {s.get('reb',0)} | AST {s.get('ast',0)}\n"
            f"   STL {s.get('stl',0)} | 3PM {s.get('3pm',0)} | FG {s.get('fg_pct',0)}%\n"
        )

    # ?‡å??å??‡è??¯ï?æ¯å?ä¸Šé? 4000 å­—ï?
    messages = []
    chunk = header
    for line in lines:
        if len(chunk) + len(line) > 3900:
            messages.append(chunk.rstrip())
            chunk = ""
        chunk += line
    if chunk.strip():
        messages.append(chunk.rstrip())
    return messages or [header + "ï¼ˆç„¡?¸æ?ï¼?]

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?¼å??–ï?å°æˆ°?¸æ?
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def format_matchup(m: dict) -> str:
    cats = m.get("categories", [])
    wins   = m.get("wins", 0)
    losses = m.get("losses", 0)
    ties   = 9 - wins - losses

    winning, losing, tied = [], [], []
    for c in cats:
        label = c["label"]
        if c["status"] == "winning":
            winning.append(label)
        elif c["status"] == "losing":
            my  = c["my"]
            opp = c["opp"]
            diff = round(abs(my - opp), 1)
            sign = "?? if c["lower_is_better"] else "??
            losing.append(f"{label}({sign}{diff})")
        else:
            tied.append(label)

    opp_name = m.get("opponent", "å°æ?")
    real = "?“¡ Yahoo ?Ÿå¯¦?¸æ?" if m.get("is_real_data") else "? ï? æ¨¡æ“¬?¸æ?"
    week_num = os.environ.get("CURRENT_WEEK", "")
    week_label = f"ç¬?{week_num} ?? " if week_num else ""

    lines = [
        f"?”ï? <b>?¬é€±å???/b>  {week_label}",
        f"ä½?vs <b>{opp_name}</b>",
        f"?®å?: <b>{wins}W ??{losses}L ??{ties}T</b>  {real}",
        "",
    ]
    if winning:
        lines.append(f"???˜å?: {' '.join(winning)}")
    if losing:
        lines.append(f"???½å?: {' '.join(losing)}")
    if tied:
        lines.append(f"??å¹³æ?: {' '.join(tied)}")

    lines += ["", "<b>è©³ç´°?¸æ?ï¼?/b>"]
    for c in cats:
        icon = "?? if c["status"] == "winning" else ("?? if c["status"] == "losing" else "??)
        lines.append(f"{icon} {c['label']:4s}: {c['my']} vs {c['opp']}")

    return "\n".join(lines)

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?¼å??–ï?FA ?¿æ?å»ºè­°
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def format_fa_suggestions(fa_data: dict, losing_cats: list, ai_notes: dict = None) -> str:
    players = fa_data.get("players", [])[:3]
    cats_str = " / ".join(losing_cats[:3]) if losing_cats else "?´é?è£œå¼·"
    lines = [
        f"?’¡ <b>FA ?¿æ?å»ºè­°</b>",
        f"è£œå¼·?é?ï¼š{cats_str}",
        "",
    ]
    for i, p in enumerate(players, 1):
        a = p.get("avg", {})
        rec = " <b>?…æ¨??/b>" if p.get("recommended") else ""
        note = f"\n   ?? {ai_notes[p['name']]}" if ai_notes and p["name"] in ai_notes else ""
        lines += [
            f"{i}. <b>{p['name']}</b>{rec}  {p.get('team','??)} Â· {p.get('position','??)}",
            f"   Fantasy #{p.get('rank_fantasy','??)}",
            f"   PTS {a.get('pts',0)} | AST {a.get('ast',0)} | 3PM {a.get('threes',0)} | FG {a.get('fg_pct',0)}%{note}",
            "",
        ]
    lines += [
        "?? <a href=\"https://basketball.fantasysports.yahoo.com/nba/46147/players?status=FA\">Yahoo FA å¸‚å ´</a>",
    ]
    return "\n".join(lines)

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?¼å??–ï??’å?
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def format_standings(teams: list, standings: dict, opp_name: str | None = None) -> str:
    # ?‰å??´æ?åº?    def sort_key(t):
        rec = standings.get(t["team_key"], {})
        return (-rec.get("wins", 0), rec.get("losses", 99))

    sorted_teams = sorted(teams, key=sort_key)
    opp_lower = opp_name.lower().strip() if opp_name else None

    lines = ["?? <b>?¯ç??’å?</b>\n"]
    for rank, t in enumerate(sorted_teams, 1):
        rec = standings.get(t["team_key"], {})
        w, l, tie = rec.get("wins", 0), rec.get("losses", 0), rec.get("ties", 0)
        if t.get("is_my_team"):
            marker = " ?€ ä½?
        elif opp_lower and t["name"].lower().strip() == opp_lower:
            marker = " ???¬é€±å???
        else:
            marker = ""
        lines.append(f"#{rank:2d} {t['name'][:14]:14s} {w}W-{l}L-{tie}T{marker}")

    return "\n".join(lines)

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?¼å??–ï?ä»Šæ—¥è³½ç?
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

import re as _re

def _et_to_tst(status_text: str) -> str:
    """
    å°?NBA API ?å‚³??ET ?‚é?å­—ä¸²è½‰ç‚º?°ç£?‚é?ï¼ˆUTC+8ï¼‰ã€?    ?…è??†å??ªé?è³½ç??¼å?ï¼Œå? "7:30 pm ET"??    å·²é?è³½ï?Q1/Final/?¦ï??´æ¥?å‚³?Ÿæ???    """
    m = _re.match(r"(\d{1,2}):(\d{2})\s*(am|pm)\s*ET", status_text.strip(), _re.IGNORECASE)
    if not m:
        return status_text

    hour = int(m.group(1))
    minute = int(m.group(2))
    meridiem = m.group(3).lower()

    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0

    # 3?ˆï?EDTï¼? UTC-4ï¼›å°??= UTC+8ï¼Œå·® 12 å°æ?
    tst_hour = (hour + 12) % 24
    next_day = (hour + 12) >= 24
    tst_str  = f"{tst_hour:02d}:{minute:02d}"
    if next_day:
        tst_str += " ?”æ—¥"

    return f"{status_text}ï¼ˆå°??{tst_str}ï¼?


def format_schedule_all(games: list) -> str:
    if not games:
        return "?? <b>ä»Šæ—¥è³½ç?</b>\n\nä»Šæ—¥??NBA æ¯”è³½"
    lines = [f"?? <b>ä»Šæ—¥è³½ç?</b>ï¼ˆå…± {len(games)} ?´ï?\n"]
    for g in games:
        time_str = _et_to_tst(g["status"])
        lines.append(f"?? {g['away_abbr']} @ {g['home_abbr']}  {time_str}")
    return "\n".join(lines)

def format_schedule_mine(games: list, my_teams: set) -> str:
    my_games = [g for g in games if g["home_abbr"] in my_teams or g["away_abbr"] in my_teams]
    lines = [f"?? <b>?‘ç??ƒå“¡ä»Šæ—¥?ºè³½</b>\n"]
    if not my_games:
        lines.append("ä»Šæ—¥ä½ ç??ƒå“¡?‡ç„¡æ¯”è³½")
    else:
        for g in my_games:
            time_str = _et_to_tst(g["status"])
            lines.append(f"?Ÿ¢ {g['away_abbr']} @ {g['home_abbr']}  {time_str}")
    return "\n".join(lines)

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?ƒå“¡?œå??¼å???# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def format_player_card(season_row: dict, row_7d: dict | None, yahoo_status: dict | None) -> str:
    name  = season_row.get("PLAYER_NAME", "Unknown")
    team  = season_row.get("TEAM_ABBREVIATION", "??)

    status_txt = ""
    inj_txt = ""
    if yahoo_status:
        st = yahoo_status.get("status", "Active")
        inj = yahoo_status.get("injury_note", "")
        status_txt = f"\n?€?? {status_emoji(st)} {st}"
        if inj:
            status_txt += f" ??{inj}"

    lines = [f"?? <b>{name}</b>  {team}{status_txt}", ""]

    if row_7d:
        from data.nba_live import _f
        lines += [
            "<b>è¿?å¤©å??¼ï?</b>",
            f"PTS {_f(row_7d,'PTS')} | REB {_f(row_7d,'REB')} | AST {_f(row_7d,'AST')}",
            f"STL {_f(row_7d,'STL')} | BLK {_f(row_7d,'BLK')} | 3PM {_f(row_7d,'FG3M')}",
            f"FG {_f(row_7d,'FG_PCT',scale=100)}% | FT {_f(row_7d,'FT_PCT',scale=100)}% | TO {_f(row_7d,'TOV')}",
        ]
    else:
        pts = round(season_row.get("PTS", 0), 1)
        reb = round(season_row.get("REB", 0), 1)
        ast = round(season_row.get("AST", 0), 1)
        lines += [
            "<b>è³½å­£?‡å€¼ï?</b>",
            f"PTS {pts} | REB {reb} | AST {ast}",
        ]

    return "\n".join(lines)

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# Claude AI ?†æ?ï¼ˆé? ANTHROPIC_API_KEYï¼?# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

async def analyze_player_with_claude(name: str, stats_7d: dict, stats_14d: dict,
                                     status: str, gp_7d: int) -> str:
    """?¼å« Claude claude-haiku-4-5 ?†æ??®ä??ƒå“¡è¿‘æ?è¡¨ç¾?‚ç„¡ API Key ?‚å??³ç©ºå­—ä¸²??""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""
    try:
        import anthropic
        import asyncio
        client = anthropic.Anthropic(api_key=api_key)
        stats_text = (
            f"?ƒå“¡ï¼š{name}  ?€?‹ï?{status}\n"
            f"è¿?å¤©ï?{gp_7d}?´ï?ï¼šPTS {stats_7d.get('pts',0)} | REB {stats_7d.get('reb',0)} "
            f"| AST {stats_7d.get('ast',0)} | STL {stats_7d.get('stl',0)} "
            f"| 3PM {stats_7d.get('3pm',0)} | FG {stats_7d.get('fg_pct',0)}%"
        )
        if stats_14d:
            stats_text += (
                f"\nè¿?4å¤©ï?PTS {stats_14d.get('pts',0)} | REB {stats_14d.get('reb',0)} "
                f"| AST {stats_14d.get('ast',0)}"
            )

        def _call():
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": (
                        "ä½ æ˜¯ Fantasy NBA ?†æ?å¸«ã€‚è??¹æ??ƒå“¡7å¤©è?14å¤©å??¼ç?è¶¨å‹¢ï¼?
                        "??-3?¥ç?é«”ä¸­?‡å??è¡¨?¾è¶¨?¢ï?ä¸Šå?/ä¸‹é?/ç©©å?ï¼‰ï?"
                        "?€å¾Œçµ¦?ºå»ºè­°ï??æ? / è§€å¯?/ ?ƒæ…®?¾æ?ï¼‰ã€‚ä?è¦é?è¤‡å??ºæ•¸å­—ã€‚\n\n" + stats_text
                    )
                }]
            )
            return msg.content[0].text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)
    except Exception as e:
        logger.warning(f"Claude analysis failed for {name}: {e}")
        return ""


async def analyze_fa_with_claude(players: list, losing_cats: list) -> dict:
    """
    ?¹æ¬¡?†æ? FA ?ƒå“¡ï¼Œæ?ä½å??³ä??¥èªª?ã€?    ?å‚³: {player_name: note_str}ï¼Œç„¡ API Key ?‚å???{}
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not players:
        return {}
    try:
        import anthropic
        import asyncio
        import re as _re2
        client = anthropic.Anthropic(api_key=api_key)

        cats_str = "??.join(losing_cats[:3]) if losing_cats else "?´é??‡è¡¡è£œå¼·"
        players_text = ""
        for i, p in enumerate(players, 1):
            a = p.get("avg", {})
            players_text += (
                f"{i}. {p['name']}  {p.get('team','??)} Â· {p.get('position','??)}\n"
                f"   PTS {a.get('pts',0)} | REB {a.get('reb',0)} | AST {a.get('ast',0)} "
                f"| 3PM {a.get('threes',0)} | STL {a.get('stl',0)} | FG {a.get('fg_pct',0)}%\n"
            )

        prompt = (
            f"ä½ æ˜¯ Fantasy NBA ?†æ?å¸«ã€‚æ??¬é€±è½å¾Œç?é¡åˆ¥?¯ï?{cats_str}?‚\n"
            f"ä»¥ä???3 ä½è‡ª?±ç??¡å€™é¸ï¼š\n\n{players_text}\n"
            f"è«‹é?å°æ?ä½ç??¡ï??¨ä??¥ç?é«”ä¸­?‡èªª?ä??½å¦è£œå¼·ä¸Šè¿°?½å?é¡åˆ¥ï¼Œæ ¼å¼å?ä¸‹ï??¿å??¶ä??§å®¹ï¼‰ï?\n"
            f"1. [èªªæ?]\n2. [èªªæ?]\n3. [èªªæ?]"
        )

        def _call():
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, _call)

        notes = {}
        for i, p in enumerate(players, 1):
            m = _re2.search(rf"^{i}\.\s*(.+)", raw, _re2.MULTILINE)
            if m:
                notes[p["name"]] = m.group(1).strip()
        return notes

    except Exception as e:
        logger.warning(f"analyze_fa_with_claude failed: {e}")
        return {}


async def show_player_detail(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             period: str, player_idx: int, edit: bool = True):
    """é¡¯ç¤º?®ä??ƒå“¡è©³ç´°?¸æ?ï¼Œperiod: '7d' | '14d' | 'rpt'"""
    try:
        from data_loader import get_roster_with_stats

        all_players = get_live_roster_cached()
        if player_idx >= len(all_players):
            return

        cached_player = all_players[player_idx]
        player_name = cached_player["name"]

        # ?€?‹ç›´?¥å? live roster cache ?–å?ï¼Œä??é?è¤‡å‘¼??Yahoo API
        status = cached_player.get("status", "Active")
        inj    = cached_player.get("injury_note", "")
        se       = status_emoji(status)
        inj_line = f"\n? ï? {inj}" if inj else ""

        if period in ("7d", "14d"):
            roster_data = get_roster_with_stats(period)
            p_data = next((p for p in roster_data.get("players", []) if p["name"] == player_name), {})
            s    = p_data.get("stats") or {}
            gp   = p_data.get("gp", 0)
            team = p_data.get("team", cached_player.get("team", "??))
            pos  = p_data.get("position", cached_player.get("position", "??))
            label = "è¿?å¤? if period == "7d" else "è¿?4å¤?
            msg = (
                f"{se} <b>{player_name}</b>  {team} Â· {pos}{inj_line}\n"
                f"{label}ï¼ˆ{gp}?´ï?\n"
                f"   PTS {s.get('pts',0)} | REB {s.get('reb',0)} | AST {s.get('ast',0)}\n"
                f"   STL {s.get('stl',0)} | 3PM {s.get('3pm',0)} | FG {s.get('fg_pct',0)}%"
            )
            analysis = await analyze_player_with_claude(player_name, s, {}, status, gp)

        else:  # rpt ??ä»Šæ—¥?†æ?ï¼šä??¥å‡ºè³?+ 7å¤?vs 14å¤©è¶¨??+ è¦å?å»ºè­°
            from data.nba_live import get_today_games
            games = []
            try:
                games = get_today_games()
            except Exception:
                pass
            today_teams = {g["home_abbr"] for g in games} | {g["away_abbr"] for g in games}

            r7   = get_roster_with_stats("7d")
            r14  = get_roster_with_stats("14d")
            p7   = next((p for p in r7.get("players", []) if p["name"] == player_name), {})
            p14  = next((p for p in r14.get("players", []) if p["name"] == player_name), {})
            s7   = p7.get("stats") or {}
            s14  = p14.get("stats") or {}
            gp7  = p7.get("gp", 0)
            team = p7.get("team", cached_player.get("team", "??))
            pos  = p7.get("position", cached_player.get("position", "??))

            # ä»Šæ—¥?ºè³½è³‡è?ï¼ˆå«æ¯”è³½?‚é?ï¼?            if team in today_teams:
                opp_game = next((g for g in games if team in (g["home_abbr"], g["away_abbr"])), None)
                if opp_game:
                    time_str = _et_to_tst(opp_game.get("status", ""))
                    game_line = f"?Ÿ¢ ä»Šæ—¥?ºè³½ï¼š{opp_game['away_abbr']} @ {opp_game['home_abbr']}\n   {time_str}"
                else:
                    game_line = f"?Ÿ¢ ä»Šæ—¥?ºè³½ï¼š{team}"
            else:
                game_line = "??ä»Šæ—¥?¡æ?è³?

            # è¦å?å»ºè­°ï¼ˆå«è¶¨å‹¢?¤æ–·ï¼?            pts7  = float(s7.get("pts", 0) or 0)
            pts14 = float(s14.get("pts", 0) or 0)
            reb7  = float(s7.get("reb", 0) or 0)
            ast7  = float(s7.get("ast", 0) or 0)
            trend_up = pts7 > pts14 * 1.1 if pts14 > 0 else False
            status_upper = (status or "").upper()
            if status_upper in ("INJ", "OUT", "NA"):
                advice = "??å»ºè­°ï¼šè?å¯Ÿï??·å…µï¼?
            elif gp7 < 3:
                advice = "?Ÿ¡ å»ºè­°ï¼šè?å¯Ÿï??ºè³½?´æ•¸å°‘ï?"
            elif pts7 >= 15 or (pts7 >= 12 and (reb7 >= 6 or ast7 >= 5)):
                suffix = "ï¼ˆå??†ä??‡è¶¨?¢ï?" if trend_up else ""
                advice = f"??å»ºè­°ï¼šæ??‰{suffix}"
            else:
                advice = "?Ÿ¡ å»ºè­°ï¼šæ??‰è?å¯?

            # ?–å? Claude AI ?†æ?ï¼ˆå‚³?¥ç?å¯?stats_14dï¼?            analysis = await analyze_player_with_claude(player_name, s7, s14, status, gp7)

            # çµ„å?è¨Šæ¯ï¼šç„¡ AI ?‚é¡¯ç¤ºè¶¨?¢å?æ¯”ï???AI ?‚é¡¯ç¤ºå??æ?å­?            trend_lines = "\n".join([
                "?? è¿‘æ?è¶¨å‹¢ï¼?å¤?vs 14å¤©å??¼ï?",
                format_trend_line("PTS",  round(pts7, 1),               round(pts14, 1)),
                format_trend_line("REB",  round(reb7, 1),               round(float(s14.get("reb", 0) or 0), 1)),
                format_trend_line("AST",  round(ast7, 1),               round(float(s14.get("ast", 0) or 0), 1)),
                format_trend_line("FG",   round(float(s7.get("fg_pct", 0) or 0), 1),
                                          round(float(s14.get("fg_pct", 0) or 0), 1)),
            ])

            if analysis:
                msg = (
                    f"{se} <b>{player_name}</b>  {team} Â· {pos}{inj_line}\n\n"
                    f"{game_line}\n\n"
                    f"?? AI è¶¨å‹¢?†æ?\n{analysis}"
                )
            else:
                msg = (
                    f"{se} <b>{player_name}</b>  {team} Â· {pos}{inj_line}\n\n"
                    f"{game_line}\n\n"
                    f"{trend_lines}\n\n"
                    f"{advice}"
                )

        if analysis and period in ("7d", "14d"):
            msg += f"\n\n?? <b>è¿‘æ??†æ?</b>\n{analysis}"

        kb = back_kb(f"pl_{period}")
        if edit:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)

    except Exception as e:
        logger.error(f"show_player_detail error: {e}")
        err = f"è¼‰å…¥?ƒå“¡?¸æ?å¤±æ?ï¼š{e}"
        if edit:
            await update.callback_query.edit_message_text(err, parse_mode="HTML",
                reply_markup=back_kb("menu_roster"))
        else:
            await update.message.reply_text(err, parse_mode="HTML")


# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# Handlersï¼?start ?‡ä¸»?¸å–®
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "?? <b>Fantasy NBA Bot</b>\n\nè«‹é¸?‡å??½ï?",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )

async def refresh_roster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """å¼·åˆ¶?·æ–°ä»Šæ—¥??®¹å¿«å?ï¼?refreshï¼?""
    from datetime import date
    cache_path = CACHE_DIR / f"roster_{date.today().isoformat()}.json"
    deleted = False
    if cache_path.exists():
        cache_path.unlink()
        deleted = True
    await update.message.reply_text("???æ–°?“å???®¹ä¸?..", parse_mode="HTML")
    try:
        roster = get_live_roster_cached()
        names = [p["name"] for p in roster]
        await update.message.reply_text(
            f"????®¹å·²æ›´?°ï?{len(roster)} äººï?\n" + "\n".join(f"  Â· {n}" for n in names),
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
    except Exception as e:
        await update.message.reply_text(f"???´æ–°å¤±æ?ï¼š{e}", parse_mode="HTML")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ?€?€ ä¸»é¸?®è·³è½??€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
    if data == "back_main":
        await query.edit_message_text(
            "è«‹é¸?‡å??½ï?", parse_mode="HTML", reply_markup=main_menu_kb()
        )

    elif data == "menu_roster":
        await query.edit_message_text(
            "?? <b>?‘ç???®¹</b>\nè«‹é¸?‡æ??¸ï?",
            parse_mode="HTML", reply_markup=roster_menu_kb()
        )

    elif data == "menu_matchup":
        await query.edit_message_text(
            "?”ï? <b>?¬é€±å???/b>\nè«‹é¸?‡ï?",
            parse_mode="HTML", reply_markup=matchup_menu_kb()
        )

    elif data == "menu_search":
        await query.edit_message_text(
            "?? <b>?¥è©¢?ƒå“¡</b>\n\nè«‹ç›´?¥è¼¸?¥ç??¡å??ï??±æ?ï¼‰ï?\nä¾‹ï?LeBron James",
            parse_mode="HTML", reply_markup=back_kb()
        )
        context.user_data["awaiting_search"] = True

    elif data == "menu_standings":
        await query.edit_message_text("??è¼‰å…¥?’å?ä¸?..", parse_mode="HTML")
        await show_standings(update, context, edit=True)

    elif data == "menu_schedule":
        await query.edit_message_text(
            "?? <b>ä»Šæ—¥è³½ç?</b>\nè«‹é¸?‡ï?",
            parse_mode="HTML", reply_markup=schedule_menu_kb()
        )

    # ?€?€ ??®¹ ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
    elif data in ("roster_7d", "roster_14d"):
        period = "7d" if data == "roster_7d" else "14d"
        label  = "è¿?å¤©å??? if period == "7d" else "è¿?4å¤©å???
        await query.edit_message_text(
            f"?? <b>?‘ç???®¹ ??{label}</b>\n\nè«‹é¸?‡ç??¡ï?",
            parse_mode="HTML", reply_markup=player_list_kb(period)
        )

    elif data == "roster_report":
        await query.edit_message_text(
            "?? <b>ä»Šæ—¥?†æ?</b>\n\nè«‹é¸?‡ç??¡ï?",
            parse_mode="HTML", reply_markup=player_list_kb("rpt")
        )

    elif data == "roster_injuries":
        await query.edit_message_text("??è¼‰å…¥?·å…µ?€??..", parse_mode="HTML")
        await show_injuries(update, context, edit=True)

    # ?ƒå“¡?å–®ï¼ˆè??ç”¨ï¼?    elif data in ("pl_7d", "pl_14d", "pl_rpt"):
        period = data[3:]
        labels = {"7d": "è¿?å¤©å???, "14d": "è¿?4å¤©å???, "rpt": "ä»Šæ—¥?†æ?"}
        await query.edit_message_text(
            f"?? <b>?‘ç???®¹ ??{labels[period]}</b>\n\nè«‹é¸?‡ç??¡ï?",
            parse_mode="HTML", reply_markup=player_list_kb(period)
        )

    # ?‹åˆ¥?ƒå“¡è©³æ?
    elif data.startswith("pd_"):
        parts = data.split("_")
        if len(parts) == 3:
            period = parts[1]
            try:
                player_idx = int(parts[2])
            except ValueError:
                return
            await query.edit_message_text("??è¼‰å…¥ä¸?..", parse_mode="HTML")
            await show_player_detail(update, context, period, player_idx, edit=True)

    # ?€?€ å°æˆ° ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
    elif data == "matchup_stats":
        await query.edit_message_text("??è¼‰å…¥å°æˆ°?¸æ?...", parse_mode="HTML")
        await show_matchup(update, context, edit=True)

    elif data == "matchup_fa":
        await query.edit_message_text("??è¼‰å…¥ FA å»ºè­°...", parse_mode="HTML")
        await show_fa(update, context, edit=True)

    # ?€?€ è³½ç? ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
    elif data == "schedule_all":
        await query.edit_message_text("??è¼‰å…¥ä»Šæ—¥è³½ç?...", parse_mode="HTML")
        await show_schedule(update, context, mine_only=False, edit=True)

    elif data == "schedule_mine":
        await query.edit_message_text("??è¼‰å…¥?‘ç??ƒå“¡?ºè³½...", parse_mode="HTML")
        await show_schedule(update, context, mine_only=True, edit=True)

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?‡å?è¨Šæ¯ï¼šç??¡æ?å°?# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_search"):
        return
    context.user_data["awaiting_search"] = False

    query_text = update.message.text.strip()
    await update.message.reply_text(f"?? ?œå?ä¸­ï?{query_text}...", parse_mode="HTML")

    try:
        from data_loader import find_player, load_players_data
        data = load_players_data()
        row = find_player(data["season"]["players"], query_text)

        if not row:
            await update.message.reply_text(
                f"?¾ä??°ç??¡ï?<b>{query_text}</b>\n\n"
                f"è«‹è¼¸?¥è‹±?‡å…¨?ï?ä¾‹å?ï¼š\n<code>LeBron James</code>",
                parse_mode="HTML",
                reply_markup=back_kb("menu_search"),
            )
            return

        from data.nba_live import _fetch_n_game_stats, _find_player
        raw_7d = _fetch_n_game_stats(7)
        row_7d = _find_player(raw_7d, query_text)

        # ?—è©¦?–å? Yahoo ?€??        yahoo_status = None
        try:
            from yahoo_api import get_my_roster_with_keys
            roster_keys = get_my_roster_with_keys()
            for rp in roster_keys:
                if rp["name"].lower() == query_text.lower():
                    yahoo_status = rp
                    break
        except Exception:
            pass

        msg = format_player_card(row, row_7d, yahoo_status)
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=back_kb("menu_search"))

    except Exception as e:
        logger.error(f"Player search error: {e}")
        await update.message.reply_text(f"?¥è©¢å¤±æ?ï¼š{e}", parse_mode="HTML")

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?Ÿèƒ½å¯¦ä?
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

async def show_injuries(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    """?·å…µæ¦‚è¦½ï¼šå??ºæ??‰é? Active ?€?‹ç???""
    try:
        players = get_live_roster_cached()
        red, yellow, healthy = [], [], []
        for p in players:
            st = (p.get("status") or "").upper()
            inj = p.get("injury_note", "")
            name = p["name"]
            team = p.get("team", "??)
            pos  = p.get("position", "??)
            inj_suffix = f" ??{inj}" if inj else ""
            if st in ("INJ", "OUT", "NA"):
                red.append(f"?”´ <b>{name}</b>  {team} Â· {pos}{inj_suffix}")
            elif st in ("Q", "QUESTIONABLE", "DTD"):
                yellow.append(f"?Ÿ¡ <b>{name}</b>  {team} Â· {pos}{inj_suffix}")
            else:
                healthy.append(name)

        lines = ["?¥ <b>?·å…µæ¦‚è¦½</b>\n"]
        if red:
            lines.append("??ç¢ºå?ç¼ºé™£ï¼?)
            lines.extend(red)
            lines.append("")
        if yellow:
            lines.append("? ï? ?€?‹å??‘ï?")
            lines.extend(yellow)
            lines.append("")
        if not red and not yellow:
            lines.append("???®å??¡å‚·?µï??¨å“¡?¥åº·ï¼?)
        else:
            healthy_str = "??.join(healthy)
            lines.append(f"?Ÿ¢ ?¥åº·ï¼ˆ{len(healthy)}äººï?ï¼š{healthy_str}")

        txt = "\n".join(lines)
        kb = back_kb("menu_roster")
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(txt, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"show_injuries error: {e}")
        txt = f"è¼‰å…¥?·å…µè³‡æ?å¤±æ?ï¼š{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb("menu_roster"))


async def show_matchup(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    try:
        from data_loader import calculate_h2h_matchup
        m = calculate_h2h_matchup("season")
        txt = format_matchup(m)
        kb  = matchup_menu_kb()
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(txt, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"show_matchup error: {e}")
        txt = f"è¼‰å…¥å°æˆ°å¤±æ?ï¼š{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb("menu_matchup"))


async def show_fa(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    try:
        from data_loader import calculate_h2h_matchup, get_all_free_agents
        m = calculate_h2h_matchup("season")
        losing_cats = [c["label"] for c in m.get("categories", []) if c["status"] == "losing"]
        fa_data = get_all_free_agents(offset=0, limit=3, sort="rank")
        ai_notes = await analyze_fa_with_claude(fa_data.get("players", []), losing_cats)
        txt = format_fa_suggestions(fa_data, losing_cats, ai_notes)
        kb  = matchup_menu_kb()
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML",
                reply_markup=kb, disable_web_page_preview=True)
        else:
            await update.message.reply_text(txt, parse_mode="HTML",
                reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"show_fa error: {e}")
        txt = f"è¼‰å…¥ FA å»ºè­°å¤±æ?ï¼š{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb("menu_matchup"))


async def show_standings(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    try:
        from yahoo_api import get_league_standings, get_all_teams_with_rosters
        from data_loader import calculate_h2h_matchup
        standings = get_league_standings()
        teams     = get_all_teams_with_rosters()
        opp_name = None
        try:
            m = calculate_h2h_matchup("season")
            opp_name = m.get("opponent")
        except Exception:
            pass
        txt = format_standings(teams, standings, opp_name)
        kb  = back_kb()
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(txt, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"show_standings error: {e}")
        txt = f"è¼‰å…¥?’å?å¤±æ?ï¼š{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb())


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        mine_only: bool = False, edit: bool = False):
    try:
        from data.nba_live import get_today_games
        import json as _json
        games = get_today_games()

        if mine_only:
            my_teams = {p["team"] for p in get_live_roster_cached()}
            txt = format_schedule_mine(games, my_teams)
        else:
            txt = format_schedule_all(games)

        kb = schedule_menu_kb()
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(txt, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"show_schedule error: {e}")
        txt = f"è¼‰å…¥è³½ç?å¤±æ?ï¼š{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb("menu_schedule"))

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# å®šæ??¨æ’­
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

async def push_matchup_morning(context: ContextTypes.DEFAULT_TYPE):
    """æ¯æ—¥ 09:00ï¼ˆå°????¨é€å??°æ•¸??+ ?½å??…ç›®"""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
    try:
        from data_loader import calculate_h2h_matchup
        m   = calculate_h2h_matchup("season")
        cats = m.get("categories", [])
        w, l = m.get("wins", 0), m.get("losses", 0)
        ties = 9 - w - l

        losing = [c for c in cats if c["status"] == "losing"]
        opp    = m.get("opponent", "å°æ?")

        lines = [
            f"?? <b>æ¯æ—¥å°æˆ°?´æ–°ï¼?9:00ï¼?/b>",
            f"ä½?vs {opp}",
            f"?®å?: <b>{w}W ??{l}L ??{ties}T</b>",
            "",
        ]
        if losing:
            lines.append("???½å??…ç›®ï¼?)
            for c in losing:
                diff = round(abs(c["my"] - c["opp"]), 1)
                lines.append(f"  {c['label']}: {c['my']} vs {c['opp']} (?’{diff})")
        else:
            lines.append("???®å??¡è½å¾Œé??®ï?ç¹¼ç?ä¿æ?ï¼?)

        await context.bot.send_message(chat_id=int(chat_id), text="\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"push_matchup_morning error: {e}")


async def push_daily_report(context: ContextTypes.DEFAULT_TYPE):
    """æ¯æ—¥ 14:00ï¼ˆå°????¨é€ä??¥å‡ºè³½ç???+ ?ç¤º?¥ç??¥å ±"""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
    try:
        from data.nba_live import get_today_games
        import json as _json
        games = get_today_games()
        today_teams = {g["home_abbr"] for g in games} | {g["away_abbr"] for g in games}

        playing, resting = [], []
        for p in get_live_roster_cached():
            if p["team"] in today_teams:
                # ?¾æ?è³½è?è¨?                opp_game = next(
                    (g for g in games if p["team"] in (g["home_abbr"], g["away_abbr"])), None
                )
                game_str = f"{opp_game['away_abbr']} @ {opp_game['home_abbr']}" if opp_game else p["team"]
                playing.append(f"  {p['name']:20s} {game_str}")
            else:
                resting.append(p["name"])

        lines = [
            f"?? <b>ä»Šæ—¥?ƒå“¡?ºè³½ï¼?4:00ï¼?/b>",
            f"",
            f"?Ÿ¢ ä»Šæ—¥?‰è³½ï¼ˆ{len(playing)}äººï?ï¼?,
        ] + playing + [
            f"",
            f"??ä»Šæ—¥?¡è³½ï¼ˆ{len(resting)}äººï?",
            f"",
            f"?? é»é¸?Œä??¥å??ã€é¸?‡ç??¡æŸ¥?‹å‡ºè³½ç?æ³è?è¿‘æ?è¶¨å‹¢",
        ]

        await context.bot.send_message(chat_id=int(chat_id), text="\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"push_daily_report error: {e}")


async def push_weekly_summary(context: ContextTypes.DEFAULT_TYPE):
    """?±ä? 14:00ï¼ˆå°????¨é€æœ¬?±æ?çµ‚ç???+ ?’å?"""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
    try:
        from data_loader import calculate_h2h_matchup
        from yahoo_api import get_league_standings, get_all_teams_with_rosters

        m = calculate_h2h_matchup("season")
        w, l = m.get("wins", 0), m.get("losses", 0)
        ties = 9 - w - l
        result = "???? if w > l else ("è²??? if l > w else "å¹³æ? ??)

        standings = get_league_standings()
        teams     = get_all_teams_with_rosters()

        from yahoo_config import LEAGUE_KEY, USER_TEAM_ID
        my_key = f"{LEAGUE_KEY}.t.{USER_TEAM_ID}"
        my_rec = standings.get(my_key, {})

        # ?’å?
        def rank_key(t):
            rec = standings.get(t["team_key"], {})
            return (-rec.get("wins", 0), rec.get("losses", 99))
        sorted_teams = sorted(teams, key=rank_key)
        my_rank = next((i+1 for i, t in enumerate(sorted_teams) if t.get("is_my_team")), "??)

        lines = [
            f"?? <b>?¬é€±å??°ç???/b>",
            f"",
            f"?€çµ‚æ??†ï?<b>{w}W ??{l}L ??{ties}T</b> ??{result}",
            f"",
            f"?¬å­£?’å?ï¼?{my_rank}",
            f"?¬å­£?°ç¸¾ï¼š{my_rec.get('wins',0)}W ??{my_rec.get('losses',0)}L ??{my_rec.get('ties',0)}T",
        ]

        await context.bot.send_message(chat_id=int(chat_id), text="\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"push_weekly_summary error: {e}")

# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# Bot ?Ÿå??¥å£
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def run_bot():
    """?Œæ­¥?¥å£ï¼Œä? app.py ??background thread ?¼å«"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("[Bot] TELEGRAM_BOT_TOKEN ?ªè¨­å®šï?Bot ä¸å???)
        return

    application = (
        Application.builder()
        .token(token)
        .build()
    )

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("refresh", refresh_roster))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # å®šæ??¨æ’­ï¼ˆUTC ?‚é?ï¼?    jq = application.job_queue
    if jq:
        # æ¯æ—¥ 09:00 ?°ç£ = 01:00 UTC
        jq.run_daily(push_matchup_morning, time=datetime_time(1, 0, tzinfo=pytz.utc), name="daily_matchup")
        # æ¯æ—¥ 14:00 ?°ç£ = 06:00 UTC
        jq.run_daily(push_daily_report, time=datetime_time(6, 0, tzinfo=pytz.utc), name="daily_report")
        # ?±ä? 14:00 ?°ç£ = ?±ä? 06:00 UTCï¼ˆdays=(0,) = Mondayï¼?        jq.run_daily(push_weekly_summary, time=datetime_time(6, 0, tzinfo=pytz.utc),
                     days=(0,), name="weekly_summary")
        logger.info("[Bot] å®šæ??¨æ’­å·²è¨­å®šï?09:00 å°æˆ° / 14:00 ?¥å ± / ?±ä? 14:00 çµæ?ï¼?)
    else:
        logger.warning("[Bot] job_queue ä¸å¯?¨ï?è«‹ç¢ºèªå?è£?python-telegram-bot[job-queue]")

    logger.info("[Bot] Telegram Bot ?‹å??‹è?...")
    # Python 3.10+ ?€è¦æ?ç¢ºå»ºç«?event loopï¼ˆåœ¨?ä¸» thread ??asyncio.run å¤–éƒ¨?¼å«?‚ï?
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)


if __name__ == "__main__":
    # ?´æ¥?·è?ï¼špython3 telegram_bot.py
    run_bot()
