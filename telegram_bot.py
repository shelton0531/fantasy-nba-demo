"""
Fantasy NBA Telegram Bot
主選單：我的陣容 / 本週對戰 / 查詢球員 / 聯盟排名 / 今日賽程
定時推播：09:00 對戰更新 / 14:00 球員日報 / 週一 14:00 本週結果

球員日報資料來源：
  1. Yahoo Fantasy 官方球員消息（get_player_news）
  2. Google News RSS（免 API key，抓近期新聞標題）
"""

import os
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, time as datetime_time, date
from pathlib import Path
from urllib.parse import quote_plus

import requests
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

# ─────────────────────────────────────────────
# Inline Keyboard 工廠
# ─────────────────────────────────────────────

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏀 我的陣容", callback_data="menu_roster"),
         InlineKeyboardButton("⚔️ 本週對戰", callback_data="menu_matchup")],
        [InlineKeyboardButton("🔍 查詢球員", callback_data="menu_search"),
         InlineKeyboardButton("🏆 聯盟排名", callback_data="menu_standings")],
        [InlineKeyboardButton("📅 今日賽程", callback_data="menu_schedule")],
    ])

def roster_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("7天均值", callback_data="roster_7d"),
         InlineKeyboardButton("14天均值", callback_data="roster_14d")],
        [InlineKeyboardButton("📋 球員表現日報", callback_data="roster_report")],
        [InlineKeyboardButton("⬅️ 返回主選單", callback_data="back_main")],
    ])

def matchup_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 當前對戰數據", callback_data="matchup_stats")],
        [InlineKeyboardButton("💡 FA 替換建議", callback_data="matchup_fa")],
        [InlineKeyboardButton("⬅️ 返回主選單", callback_data="back_main")],
    ])

def schedule_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("我的球員今日出賽", callback_data="schedule_mine")],
        [InlineKeyboardButton("全部今日賽程", callback_data="schedule_all")],
        [InlineKeyboardButton("⬅️ 返回主選單", callback_data="back_main")],
    ])

def back_kb(target="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data=target)]])

# ─────────────────────────────────────────────
# 工具：狀態 emoji
# ─────────────────────────────────────────────

def status_emoji(status: str) -> str:
    s = (status or "").upper()
    if s in ("INJ", "OUT", "NA"):
        return "🔴"
    if s in ("Q", "QUESTIONABLE", "DTD"):
        return "🟡"
    return "🟢"

# ─────────────────────────────────────────────
# 工具：Google News RSS 抓取（免 API key）
# ─────────────────────────────────────────────

def get_google_news(player_name: str, max_items: int = 3) -> list[dict]:
    """
    透過 Google News RSS 取得球員近期新聞標題
    回傳: [{'title': str, 'source': str, 'link': str}, ...]
    失敗回傳: []
    """
    query = quote_plus(f"{player_name} NBA")
    url   = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        items = []
        for item in root.iter("item"):
            title_el  = item.find("title")
            link_el   = item.find("link")
            source_el = item.find("source")
            if title_el is None:
                continue
            title = title_el.text or ""
            # 過濾掉非 NBA 相關（Google News 有時混入同名的非體育新聞）
            if not any(kw in title.lower() for kw in ["nba", "lakers", "warriors", player_name.split()[-1].lower()]):
                continue
            items.append({
                "title":  title,
                "source": source_el.text if source_el is not None else "",
                "link":   link_el.text if link_el is not None else "",
            })
            if len(items) >= max_items:
                break
        return items
    except Exception as e:
        logger.warning(f"Google News fetch failed for {player_name}: {e}")
        return []


# ─────────────────────────────────────────────
# 工具：球員日報快取（每日，不含 LLM）
# ─────────────────────────────────────────────

def _report_cache_path() -> Path:
    return CACHE_DIR / f"daily_report_{date.today().isoformat()}.json"

def load_report_cache() -> dict:
    p = _report_cache_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_report_cache(cache: dict):
    CACHE_DIR.mkdir(exist_ok=True)
    _report_cache_path().write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )

# ─────────────────────────────────────────────
# 格式化：陣容卡片
# ─────────────────────────────────────────────

def format_roster_cards(players: list, period_label: str, today_teams: set) -> list[str]:
    """
    回傳 list of str，每則訊息最多 4096 字元
    today_teams: 今日有賽的 NBA 球隊縮寫 set
    """
    header = f"🏀 <b>我的陣容 — {period_label}</b>\n\n"
    lines = []
    for p in players:
        s = p.get("stats") or {}
        if not s:
            lines.append(f"❓ {p['name']} — 無數據\n")
            continue
        team = p.get("team", "—")
        pos  = p.get("position", "—")
        gp   = p.get("gp", 0)
        has_game = "🟢" if team in today_teams else "⚫"
        lines.append(
            f"{has_game} <b>{p['name']}</b>  {team} · {pos} · {gp}場\n"
            f"   PTS {s.get('pts',0)} | REB {s.get('reb',0)} | AST {s.get('ast',0)}\n"
            f"   STL {s.get('stl',0)} | 3PM {s.get('3pm',0)} | FG {s.get('fg_pct',0)}%\n"
        )

    # 切分成多則訊息（每則上限 4000 字）
    messages = []
    chunk = header
    for line in lines:
        if len(chunk) + len(line) > 3900:
            messages.append(chunk.rstrip())
            chunk = ""
        chunk += line
    if chunk.strip():
        messages.append(chunk.rstrip())
    return messages or [header + "（無數據）"]

# ─────────────────────────────────────────────
# 格式化：對戰數據
# ─────────────────────────────────────────────

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
            sign = "−" if c["lower_is_better"] else "−"
            losing.append(f"{label}({sign}{diff})")
        else:
            tied.append(label)

    opp_name = m.get("opponent", "對手")
    real = "📡 Yahoo 真實數據" if m.get("is_real_data") else "⚠️ 模擬數據"

    lines = [
        f"⚔️ <b>本週對戰</b>",
        f"你 vs <b>{opp_name}</b>",
        f"目前: <b>{wins}W – {losses}L – {ties}T</b>  {real}",
        "",
    ]
    if winning:
        lines.append(f"✅ 領先: {' '.join(winning)}")
    if losing:
        lines.append(f"❌ 落後: {' '.join(losing)}")
    if tied:
        lines.append(f"➖ 平手: {' '.join(tied)}")

    lines += ["", "<b>詳細數據：</b>"]
    for c in cats:
        icon = "✅" if c["status"] == "winning" else ("❌" if c["status"] == "losing" else "➖")
        lines.append(f"{icon} {c['label']:4s}: {c['my']} vs {c['opp']}")

    return "\n".join(lines)

# ─────────────────────────────────────────────
# 格式化：FA 替換建議
# ─────────────────────────────────────────────

def format_fa_suggestions(fa_data: dict, losing_cats: list) -> str:
    players = fa_data.get("players", [])[:3]
    cats_str = " / ".join(losing_cats[:3]) if losing_cats else "整體補強"
    lines = [
        f"💡 <b>FA 替換建議</b>",
        f"補強重點：{cats_str}",
        "",
    ]
    for i, p in enumerate(players, 1):
        a = p.get("avg", {})
        rec = " <b>★推薦</b>" if p.get("recommended") else ""
        lines += [
            f"{i}. <b>{p['name']}</b>{rec}  {p.get('team','—')} · {p.get('position','—')}",
            f"   Fantasy #{p.get('rank_fantasy','—')}",
            f"   PTS {a.get('pts',0)} | AST {a.get('ast',0)} | 3PM {a.get('threes',0)} | FG {a.get('fg_pct',0)}%",
            "",
        ]
    lines += [
        "🔗 <a href=\"https://basketball.fantasysports.yahoo.com/nba/46147/players?status=FA\">Yahoo FA 市場</a>",
    ]
    return "\n".join(lines)

# ─────────────────────────────────────────────
# 格式化：排名
# ─────────────────────────────────────────────

def format_standings(teams: list, standings: dict) -> str:
    # 按勝場排序
    def sort_key(t):
        rec = standings.get(t["team_key"], {})
        return (-rec.get("wins", 0), rec.get("losses", 99))

    sorted_teams = sorted(teams, key=sort_key)

    lines = ["🏆 <b>聯盟排名</b>\n"]
    for rank, t in enumerate(sorted_teams, 1):
        rec = standings.get(t["team_key"], {})
        w, l, tie = rec.get("wins", 0), rec.get("losses", 0), rec.get("ties", 0)
        marker = " ◀ 你" if t.get("is_my_team") else ""
        lines.append(f"#{rank:2d} {t['name'][:14]:14s} {w}W-{l}L-{tie}T{marker}")

    return "\n".join(lines)

# ─────────────────────────────────────────────
# 格式化：今日賽程
# ─────────────────────────────────────────────

def format_schedule_all(games: list) -> str:
    if not games:
        return "📅 <b>今日賽程</b>\n\n今日無 NBA 比賽"
    lines = [f"📅 <b>今日賽程</b>（共 {len(games)} 場）\n"]
    for g in games:
        lines.append(f"🏀 {g['away_abbr']} @ {g['home_abbr']}  {g['status']}")
    return "\n".join(lines)

def format_schedule_mine(games: list, my_teams: set) -> str:
    my_games = [g for g in games if g["home_abbr"] in my_teams or g["away_abbr"] in my_teams]
    lines = [f"🏀 <b>我的球員今日出賽</b>\n"]
    if not my_games:
        lines.append("今日你的球員均無比賽")
    else:
        for g in my_games:
            lines.append(f"🟢 {g['away_abbr']} @ {g['home_abbr']}  {g['status']}")
    return "\n".join(lines)

# ─────────────────────────────────────────────
# 球員搜尋格式化
# ─────────────────────────────────────────────

def format_player_card(season_row: dict, row_7d: dict | None, yahoo_status: dict | None) -> str:
    name  = season_row.get("PLAYER_NAME", "Unknown")
    team  = season_row.get("TEAM_ABBREVIATION", "—")

    status_txt = ""
    inj_txt = ""
    if yahoo_status:
        st = yahoo_status.get("status", "Active")
        inj = yahoo_status.get("injury_note", "")
        status_txt = f"\n狀態: {status_emoji(st)} {st}"
        if inj:
            status_txt += f" — {inj}"

    lines = [f"🔍 <b>{name}</b>  {team}{status_txt}", ""]

    if row_7d:
        from data.nba_live import _f
        lines += [
            "<b>近7天均值：</b>",
            f"PTS {_f(row_7d,'PTS')} | REB {_f(row_7d,'REB')} | AST {_f(row_7d,'AST')}",
            f"STL {_f(row_7d,'STL')} | BLK {_f(row_7d,'BLK')} | 3PM {_f(row_7d,'FG3M')}",
            f"FG {_f(row_7d,'FG_PCT',scale=100)}% | FT {_f(row_7d,'FT_PCT',scale=100)}% | TO {_f(row_7d,'TOV')}",
        ]
    else:
        pts = round(season_row.get("PTS", 0), 1)
        reb = round(season_row.get("REB", 0), 1)
        ast = round(season_row.get("AST", 0), 1)
        lines += [
            "<b>賽季均值：</b>",
            f"PTS {pts} | REB {reb} | AST {ast}",
        ]

    return "\n".join(lines)

# ─────────────────────────────────────────────
# Handlers：/start 與主選單
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Fantasy NBA Bot</b>\n\n請選擇功能：",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── 主選單跳轉 ──────────────────────────────
    if data == "back_main":
        await query.edit_message_text(
            "請選擇功能：", parse_mode="HTML", reply_markup=main_menu_kb()
        )

    elif data == "menu_roster":
        await query.edit_message_text(
            "🏀 <b>我的陣容</b>\n請選擇期數：",
            parse_mode="HTML", reply_markup=roster_menu_kb()
        )

    elif data == "menu_matchup":
        await query.edit_message_text(
            "⚔️ <b>本週對戰</b>\n請選擇：",
            parse_mode="HTML", reply_markup=matchup_menu_kb()
        )

    elif data == "menu_search":
        await query.edit_message_text(
            "🔍 <b>查詢球員</b>\n\n請直接輸入球員姓名（英文）：\n例：LeBron James",
            parse_mode="HTML", reply_markup=back_kb()
        )
        context.user_data["awaiting_search"] = True

    elif data == "menu_standings":
        await query.edit_message_text("⏳ 載入排名中...", parse_mode="HTML")
        await show_standings(update, context, edit=True)

    elif data == "menu_schedule":
        await query.edit_message_text(
            "📅 <b>今日賽程</b>\n請選擇：",
            parse_mode="HTML", reply_markup=schedule_menu_kb()
        )

    # ── 陣容 ───────────────────────────────────
    elif data in ("roster_7d", "roster_14d"):
        period = "7d" if data == "roster_7d" else "14d"
        label  = "近7天" if period == "7d" else "近14天"
        await query.edit_message_text(f"⏳ 載入陣容{label}數據...", parse_mode="HTML")
        await show_roster(update, context, period, label, edit=True)

    elif data == "roster_report":
        await query.edit_message_text("⏳ 載入球員日報（首次從 Yahoo 抓取，約 30 秒）...", parse_mode="HTML")
        await show_daily_report(update, context, edit=True)

    # ── 對戰 ───────────────────────────────────
    elif data == "matchup_stats":
        await query.edit_message_text("⏳ 載入對戰數據...", parse_mode="HTML")
        await show_matchup(update, context, edit=True)

    elif data == "matchup_fa":
        await query.edit_message_text("⏳ 載入 FA 建議...", parse_mode="HTML")
        await show_fa(update, context, edit=True)

    # ── 賽程 ───────────────────────────────────
    elif data == "schedule_all":
        await query.edit_message_text("⏳ 載入今日賽程...", parse_mode="HTML")
        await show_schedule(update, context, mine_only=False, edit=True)

    elif data == "schedule_mine":
        await query.edit_message_text("⏳ 載入我的球員出賽...", parse_mode="HTML")
        await show_schedule(update, context, mine_only=True, edit=True)

# ─────────────────────────────────────────────
# 文字訊息：球員搜尋
# ─────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_search"):
        return
    context.user_data["awaiting_search"] = False

    query_text = update.message.text.strip()
    await update.message.reply_text(f"🔍 搜尋中：{query_text}...", parse_mode="HTML")

    try:
        from data_loader import find_player, load_players_data
        data = load_players_data()
        row = find_player(data["season"]["players"], query_text)

        if not row:
            await update.message.reply_text(
                f"找不到球員：<b>{query_text}</b>\n請確認英文姓名拼寫",
                parse_mode="HTML",
                reply_markup=back_kb("menu_search"),
            )
            return

        from data.nba_live import _fetch_n_game_stats, _find_player
        raw_7d = _fetch_n_game_stats(7)
        row_7d = _find_player(raw_7d, query_text)

        # 嘗試取得 Yahoo 狀態
        yahoo_status = None
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
        await update.message.reply_text(f"查詢失敗：{e}", parse_mode="HTML")

# ─────────────────────────────────────────────
# 功能實作
# ─────────────────────────────────────────────

async def show_roster(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      period: str, label: str, edit: bool = False):
    try:
        from data_loader import get_roster_with_stats
        from data.nba_live import get_today_games

        roster_data = get_roster_with_stats(period)
        players = roster_data.get("players", [])

        games = []
        try:
            games = get_today_games()
        except Exception:
            pass
        today_teams = {g["home_abbr"] for g in games} | {g["away_abbr"] for g in games}

        msgs = format_roster_cards(players, label, today_teams)
        kb = roster_menu_kb()

        if edit:
            await update.callback_query.edit_message_text(msgs[0], parse_mode="HTML", reply_markup=kb if len(msgs) == 1 else None)
            for i, m in enumerate(msgs[1:], 1):
                await update.callback_query.message.reply_text(m, parse_mode="HTML",
                    reply_markup=kb if i == len(msgs) - 1 else None)
        else:
            for i, m in enumerate(msgs):
                await update.message.reply_text(m, parse_mode="HTML",
                    reply_markup=kb if i == len(msgs) - 1 else None)
    except Exception as e:
        logger.error(f"show_roster error: {e}")
        txt = f"載入陣容失敗：{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb("menu_roster"))
        else:
            await update.message.reply_text(txt, parse_mode="HTML")


async def show_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    """
    球員日報：Yahoo Fantasy 官方消息 + Google News 近期標題
    每天快取，同一天再次點擊直接讀快取（不重複抓網路）
    """
    try:
        from data_loader import get_roster_with_stats
        from yahoo_api import get_my_roster_with_keys, get_player_news

        # 先送一則「載入中」訊息
        loading_msg = "⏳ 載入球員日報（首次需從 Yahoo 抓取，約 30 秒）..."
        if edit:
            await update.callback_query.edit_message_text(loading_msg, parse_mode="HTML")
        else:
            await update.message.reply_text(loading_msg, parse_mode="HTML")

        roster_7d  = get_roster_with_stats("7d")
        roster_14d = get_roster_with_stats("14d")
        p14_map = {p["name"]: p for p in roster_14d.get("players", [])}

        # 取 Yahoo 球員 key + 狀態（含傷兵）
        try:
            yahoo_players = {p["name"]: p for p in get_my_roster_with_keys()}
        except Exception as e:
            logger.warning(f"get_my_roster_with_keys failed: {e}")
            yahoo_players = {}

        cache = load_report_cache()
        send = update.callback_query.message.reply_text

        for p in roster_7d.get("players", []):
            name    = p["name"]
            stats7  = p.get("stats") or {}
            stats14 = (p14_map.get(name, {}).get("stats") or {})
            team    = p.get("team", "—")
            pos     = p.get("position", "—")

            yp          = yahoo_players.get(name, {})
            status      = yp.get("status", "Active")
            injury_note = yp.get("injury_note", "")
            player_key  = yp.get("player_key", "")

            # 優先讀快取
            if name in cache:
                news_block = cache[name]
            else:
                # 1) Yahoo Fantasy 官方消息
                yahoo_lines = []
                if player_key:
                    try:
                        yahoo_news = get_player_news(player_key, max_items=2)
                        for n in yahoo_news:
                            if n.get("headline"):
                                yahoo_lines.append(f"📋 <b>{n['headline']}</b>")
                            if n.get("body"):
                                # 截短，最多 120 字
                                body = n["body"].strip().replace("\n", " ")
                                yahoo_lines.append(f"   {body[:120]}{'…' if len(body)>120 else ''}")
                    except Exception as e:
                        logger.warning(f"Yahoo news failed for {name}: {e}")

                # 2) Google News RSS（補充近期媒體報導）
                google_lines = []
                gnews = get_google_news(name, max_items=2)
                for g in gnews:
                    src   = f" [{g['source']}]" if g.get("source") else ""
                    google_lines.append(f"🌐 {g['title']}{src}")

                # 組合新聞區塊
                if yahoo_lines:
                    news_block = "\n".join(yahoo_lines)
                    if google_lines:
                        news_block += "\n" + "\n".join(google_lines)
                elif google_lines:
                    news_block = "\n".join(google_lines)
                else:
                    news_block = "（目前無 Yahoo 消息或近期報導）"

                cache[name] = news_block

            se       = status_emoji(status)
            inj_line = f"\n⚠️ {injury_note}" if injury_note else ""
            msg = (
                f"{se} <b>{name}</b>  {team} · {pos}{inj_line}\n"
                f"近7天: PTS {stats7.get('pts',0)} | REB {stats7.get('reb',0)} "
                f"| AST {stats7.get('ast',0)} | 3PM {stats7.get('3pm',0)} "
                f"| FG {stats7.get('fg_pct',0)}%\n"
                f"近14天: PTS {stats14.get('pts',0)} | REB {stats14.get('reb',0)} "
                f"| AST {stats14.get('ast',0)}\n\n"
                f"{news_block}"
            )
            await send(msg, parse_mode="HTML", disable_web_page_preview=True)

        save_report_cache(cache)
        await send("📋 日報完成", parse_mode="HTML", reply_markup=roster_menu_kb())

    except Exception as e:
        logger.error(f"show_daily_report error: {e}")
        txt = f"生成日報失敗：{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb("menu_roster"))
        else:
            await update.message.reply_text(txt, parse_mode="HTML")


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
        txt = f"載入對戰失敗：{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb("menu_matchup"))


async def show_fa(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    try:
        from data_loader import calculate_h2h_matchup, get_all_free_agents
        m = calculate_h2h_matchup("season")
        losing_cats = [c["label"] for c in m.get("categories", []) if c["status"] == "losing"]
        fa_data = get_all_free_agents(offset=0, limit=3, sort="rank")
        txt = format_fa_suggestions(fa_data, losing_cats)
        kb  = matchup_menu_kb()
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML",
                reply_markup=kb, disable_web_page_preview=True)
        else:
            await update.message.reply_text(txt, parse_mode="HTML",
                reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"show_fa error: {e}")
        txt = f"載入 FA 建議失敗：{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb("menu_matchup"))


async def show_standings(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    try:
        from yahoo_api import get_league_standings, get_all_teams_with_rosters
        standings = get_league_standings()
        teams     = get_all_teams_with_rosters()
        txt = format_standings(teams, standings)
        kb  = back_kb()
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(txt, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"show_standings error: {e}")
        txt = f"載入排名失敗：{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb())


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        mine_only: bool = False, edit: bool = False):
    try:
        from data.nba_live import get_today_games
        import json as _json
        games = get_today_games()

        if mine_only:
            with open("my_roster.json", encoding="utf-8") as f:
                roster = _json.load(f)
            my_teams = {p["team"] for p in roster.get("roster", [])}
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
        txt = f"載入賽程失敗：{e}"
        if edit:
            await update.callback_query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_kb("menu_schedule"))

# ─────────────────────────────────────────────
# 定時推播
# ─────────────────────────────────────────────

async def push_matchup_morning(context: ContextTypes.DEFAULT_TYPE):
    """每日 09:00（台灣）推送對戰數據 + 落後項目"""
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
        opp    = m.get("opponent", "對手")

        lines = [
            f"📊 <b>每日對戰更新（09:00）</b>",
            f"你 vs {opp}",
            f"目前: <b>{w}W – {l}L – {ties}T</b>",
            "",
        ]
        if losing:
            lines.append("❌ 落後項目：")
            for c in losing:
                diff = round(abs(c["my"] - c["opp"]), 1)
                lines.append(f"  {c['label']}: {c['my']} vs {c['opp']} (−{diff})")
        else:
            lines.append("✅ 目前無落後項目，繼續保持！")

        await context.bot.send_message(chat_id=int(chat_id), text="\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"push_matchup_morning error: {e}")


async def push_daily_report(context: ContextTypes.DEFAULT_TYPE):
    """每日 14:00（台灣）推送今日出賽球員 + 提示查看日報"""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
    try:
        from data.nba_live import get_today_games
        import json as _json
        games = get_today_games()
        today_teams = {g["home_abbr"] for g in games} | {g["away_abbr"] for g in games}

        with open("my_roster.json", encoding="utf-8") as f:
            roster = _json.load(f)

        playing, resting = [], []
        for p in roster.get("roster", []):
            if p["team"] in today_teams:
                # 找比賽資訊
                opp_game = next(
                    (g for g in games if p["team"] in (g["home_abbr"], g["away_abbr"])), None
                )
                game_str = f"{opp_game['away_abbr']} @ {opp_game['home_abbr']}" if opp_game else p["team"]
                playing.append(f"  {p['name']:20s} {game_str}")
            else:
                resting.append(p["name"])

        lines = [
            f"🏀 <b>今日球員出賽（14:00）</b>",
            f"",
            f"🟢 今日有賽（{len(playing)}人）：",
        ] + playing + [
            f"",
            f"⚫ 今日無賽（{len(resting)}人）",
            f"",
            f"📋 點選「球員表現日報」查看 Yahoo 消息 + 近期新聞",
        ]

        await context.bot.send_message(chat_id=int(chat_id), text="\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"push_daily_report error: {e}")


async def push_weekly_summary(context: ContextTypes.DEFAULT_TYPE):
    """週一 14:00（台灣）推送本週最終結果 + 排名"""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
    try:
        from data_loader import calculate_h2h_matchup
        from yahoo_api import get_league_standings, get_all_teams_with_rosters

        m = calculate_h2h_matchup("season")
        w, l = m.get("wins", 0), m.get("losses", 0)
        ties = 9 - w - l
        result = "勝 ✅" if w > l else ("負 ❌" if l > w else "平手 ➖")

        standings = get_league_standings()
        teams     = get_all_teams_with_rosters()

        from yahoo_config import LEAGUE_KEY, USER_TEAM_ID
        my_key = f"{LEAGUE_KEY}.t.{USER_TEAM_ID}"
        my_rec = standings.get(my_key, {})

        # 排名
        def rank_key(t):
            rec = standings.get(t["team_key"], {})
            return (-rec.get("wins", 0), rec.get("losses", 99))
        sorted_teams = sorted(teams, key=rank_key)
        my_rank = next((i+1 for i, t in enumerate(sorted_teams) if t.get("is_my_team")), "—")

        lines = [
            f"🏆 <b>本週對戰結果</b>",
            f"",
            f"最終比分：<b>{w}W – {l}L – {ties}T</b> — {result}",
            f"",
            f"本季排名：#{my_rank}",
            f"本季戰績：{my_rec.get('wins',0)}W – {my_rec.get('losses',0)}L – {my_rec.get('ties',0)}T",
        ]

        await context.bot.send_message(chat_id=int(chat_id), text="\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"push_weekly_summary error: {e}")

# ─────────────────────────────────────────────
# Bot 啟動入口
# ─────────────────────────────────────────────

def run_bot():
    """同步入口，供 app.py 的 background thread 呼叫"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("[Bot] TELEGRAM_BOT_TOKEN 未設定，Bot 不啟動")
        return

    application = (
        Application.builder()
        .token(token)
        .build()
    )

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # 定時推播（UTC 時間）
    jq = application.job_queue
    if jq:
        # 每日 09:00 台灣 = 01:00 UTC
        jq.run_daily(push_matchup_morning, time=datetime_time(1, 0, tzinfo=pytz.utc), name="daily_matchup")
        # 每日 14:00 台灣 = 06:00 UTC
        jq.run_daily(push_daily_report, time=datetime_time(6, 0, tzinfo=pytz.utc), name="daily_report")
        # 週一 14:00 台灣 = 週一 06:00 UTC（days=(0,) = Monday）
        jq.run_daily(push_weekly_summary, time=datetime_time(6, 0, tzinfo=pytz.utc),
                     days=(0,), name="weekly_summary")
        logger.info("[Bot] 定時推播已設定（09:00 對戰 / 14:00 日報 / 週一 14:00 結果）")
    else:
        logger.warning("[Bot] job_queue 不可用，請確認安裝 python-telegram-bot[job-queue]")

    logger.info("[Bot] Telegram Bot 開始運行...")
    # Python 3.10+ 需要明確建立 event loop（在非主 thread 或 asyncio.run 外部呼叫時）
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # 直接執行：python3 telegram_bot.py
    run_bot()
