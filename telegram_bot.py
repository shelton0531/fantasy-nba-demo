"""
Fantasy NBA Telegram Bot
主選單：我的陣容 / 本週對戰 / 查詢球員 / 聯盟排名 / 今日賽程
定時推播：09:00 對戰更新 / 14:00 球員日報 / 週一 14:00 本週結果
"""

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

# ─────────────────────────────────────────────
# 即時陣容（Yahoo API + 每日快取）
# ─────────────────────────────────────────────

def get_live_roster_cached() -> list[dict]:
    """
    取得即時陣容，優先讀今日快取，否則從 Yahoo API 抓取。
    每位球員回傳：{name, position, status, injury_note, player_key, team}
    失敗時 fallback 到 my_roster.json。
    """
    cache_path = CACHE_DIR / f"roster_{date.today().isoformat()}.json"

    # 讀今日快取
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 從 Yahoo API 抓取
    try:
        from yahoo_api import get_my_roster_with_keys
        from data_loader import load_players_data

        yahoo_players = get_my_roster_with_keys()
        if not yahoo_players:
            raise ValueError("Yahoo 回傳空陣容")

        # 從 players_data.json 補充球隊縮寫
        season_players = load_players_data().get("season", {}).get("players", [])
        team_map = {p["PLAYER_NAME"].lower(): p["TEAM_ABBREVIATION"] for p in season_players}

        roster = [
            {
                "name":         p["name"],
                "position":     p["position"],
                "status":       p["status"],
                "injury_note":  p["injury_note"],
                "player_key":   p["player_key"],
                "team":         team_map.get(p["name"].lower(), "—"),
            }
            for p in yahoo_players
        ]

        CACHE_DIR.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(roster, ensure_ascii=False), encoding="utf-8")
        logger.info(f"[Roster] 即時陣容已更新：{len(roster)} 位球員")
        return roster

    except Exception as e:
        logger.warning(f"[Roster] Yahoo 抓取失敗，改用 my_roster.json：{e}")
        try:
            with open("my_roster.json", encoding="utf-8") as f:
                roster_data = json.load(f)
            return [
                {
                    "name":        p["name"],
                    "position":    p.get("position", "—"),
                    "status":      p.get("status", "Active"),
                    "injury_note": "",
                    "player_key":  "",
                    "team":        p.get("team", "—"),
                }
                for p in roster_data.get("roster", [])
            ]
        except Exception:
            return []


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
        [InlineKeyboardButton("📅 今日分析", callback_data="roster_report")],
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

def player_list_kb(period: str) -> InlineKeyboardMarkup:
    """球員選擇鍵盤（2人一排）。period: '7d' | '14d' | 'rpt'"""
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
    buttons.append([InlineKeyboardButton("⬅️ 返回陣容選單", callback_data="menu_roster")])
    return InlineKeyboardMarkup(buttons)

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
            f"\n{has_game} <b>{p['name']}</b>  {team} · {pos} · {gp}場\n"
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
# Claude AI 分析（需 ANTHROPIC_API_KEY）
# ─────────────────────────────────────────────

async def analyze_player_with_claude(name: str, stats_7d: dict, stats_14d: dict,
                                     status: str, gp_7d: int) -> str:
    """呼叫 Claude claude-haiku-4-5 分析單一球員近期表現。無 API Key 時回傳空字串。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""
    try:
        import anthropic
        import asyncio
        client = anthropic.Anthropic(api_key=api_key)
        stats_text = (
            f"球員：{name}  狀態：{status}\n"
            f"近7天（{gp_7d}場）：PTS {stats_7d.get('pts',0)} | REB {stats_7d.get('reb',0)} "
            f"| AST {stats_7d.get('ast',0)} | STL {stats_7d.get('stl',0)} "
            f"| 3PM {stats_7d.get('3pm',0)} | FG {stats_7d.get('fg_pct',0)}%"
        )
        if stats_14d:
            stats_text += (
                f"\n近14天：PTS {stats_14d.get('pts',0)} | REB {stats_14d.get('reb',0)} "
                f"| AST {stats_14d.get('ast',0)}"
            )

        def _call():
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": (
                        "你是 Fantasy NBA 分析師。請用2-3句繁體中文簡評此球員近期 Fantasy 表現，"
                        "並在最後給出建議（持有 / 觀察 / 考慮放棄）。\n\n" + stats_text
                    )
                }]
            )
            return msg.content[0].text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)
    except Exception as e:
        logger.warning(f"Claude analysis failed for {name}: {e}")
        return ""


async def show_player_detail(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             period: str, player_idx: int, edit: bool = True):
    """顯示單一球員詳細數據，period: '7d' | '14d' | 'rpt'"""
    try:
        from data_loader import get_roster_with_stats

        all_players = get_live_roster_cached()
        if player_idx >= len(all_players):
            return

        cached_player = all_players[player_idx]
        player_name = cached_player["name"]

        # 狀態直接從 live roster cache 取得，不再重複呼叫 Yahoo API
        status = cached_player.get("status", "Active")
        inj    = cached_player.get("injury_note", "")
        se       = status_emoji(status)
        inj_line = f"\n⚠️ {inj}" if inj else ""

        if period in ("7d", "14d"):
            roster_data = get_roster_with_stats(period)
            p_data = next((p for p in roster_data.get("players", []) if p["name"] == player_name), {})
            s    = p_data.get("stats") or {}
            gp   = p_data.get("gp", 0)
            team = p_data.get("team", cached_player.get("team", "—"))
            pos  = p_data.get("position", cached_player.get("position", "—"))
            label = "近7天" if period == "7d" else "近14天"
            msg = (
                f"{se} <b>{player_name}</b>  {team} · {pos}{inj_line}\n"
                f"{label}（{gp}場）\n"
                f"   PTS {s.get('pts',0)} | REB {s.get('reb',0)} | AST {s.get('ast',0)}\n"
                f"   STL {s.get('stl',0)} | 3PM {s.get('3pm',0)} | FG {s.get('fg_pct',0)}%"
            )
            analysis = await analyze_player_with_claude(player_name, s, {}, status, gp)

        else:  # rpt — 今日分析：今日出賽 + 7天趨勢 + 規則建議
            from data.nba_live import get_today_games
            games = []
            try:
                games = get_today_games()
            except Exception:
                pass
            today_teams = {g["home_abbr"] for g in games} | {g["away_abbr"] for g in games}

            r7   = get_roster_with_stats("7d")
            p7   = next((p for p in r7.get("players", []) if p["name"] == player_name), {})
            s7   = p7.get("stats") or {}
            gp7  = p7.get("gp", 0)
            team = p7.get("team", cached_player.get("team", "—"))
            pos  = p7.get("position", cached_player.get("position", "—"))

            # 今日出賽資訊
            if team in today_teams:
                opp_game = next((g for g in games if team in (g["home_abbr"], g["away_abbr"])), None)
                game_str = f"{opp_game['away_abbr']} @ {opp_game['home_abbr']}" if opp_game else team
                game_line = f"🟢 今日出賽：{game_str}"
            else:
                game_line = "⚫ 今日無比賽"

            # 規則建議
            pts = float(s7.get("pts", 0) or 0)
            reb = float(s7.get("reb", 0) or 0)
            ast = float(s7.get("ast", 0) or 0)
            status_upper = (status or "").upper()
            if status_upper in ("INJ", "OUT", "NA"):
                advice = "⛔ 建議：觀察（傷兵）"
            elif pts >= 15 or (pts >= 12 and (reb >= 6 or ast >= 5)):
                advice = "✅ 建議：持有"
            elif gp7 < 3:
                advice = "🟡 建議：觀察（出賽場數少）"
            else:
                advice = "🟡 建議：持有觀察"

            msg = (
                f"{se} <b>{player_name}</b>  {team} · {pos}{inj_line}\n\n"
                f"{game_line}\n\n"
                f"近7天（{gp7}場）\n"
                f"   PTS {s7.get('pts',0)} | REB {s7.get('reb',0)} | AST {s7.get('ast',0)}\n"
                f"   STL {s7.get('stl',0)} | 3PM {s7.get('3pm',0)} | FG {s7.get('fg_pct',0)}%\n\n"
                f"{advice}"
            )
            analysis = await analyze_player_with_claude(player_name, s7, {}, status, gp7)

        if analysis:
            msg += f"\n\n📊 <b>近期分析</b>\n{analysis}"

        kb = back_kb(f"pl_{period}")
        if edit:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)

    except Exception as e:
        logger.error(f"show_player_detail error: {e}")
        err = f"載入球員數據失敗：{e}"
        if edit:
            await update.callback_query.edit_message_text(err, parse_mode="HTML",
                reply_markup=back_kb("menu_roster"))
        else:
            await update.message.reply_text(err, parse_mode="HTML")


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
        label  = "近7天均值" if period == "7d" else "近14天均值"
        await query.edit_message_text(
            f"🏀 <b>我的陣容 — {label}</b>\n\n請選擇球員：",
            parse_mode="HTML", reply_markup=player_list_kb(period)
        )

    elif data == "roster_report":
        await query.edit_message_text(
            "📅 <b>今日分析</b>\n\n請選擇球員：",
            parse_mode="HTML", reply_markup=player_list_kb("rpt")
        )

    # 球員名單（返回用）
    elif data in ("pl_7d", "pl_14d", "pl_rpt"):
        period = data[3:]
        labels = {"7d": "近7天均值", "14d": "近14天均值", "rpt": "今日分析"}
        await query.edit_message_text(
            f"🏀 <b>我的陣容 — {labels[period]}</b>\n\n請選擇球員：",
            parse_mode="HTML", reply_markup=player_list_kb(period)
        )

    # 個別球員詳情
    elif data.startswith("pd_"):
        parts = data.split("_")
        if len(parts) == 3:
            period = parts[1]
            try:
                player_idx = int(parts[2])
            except ValueError:
                return
            await query.edit_message_text("⏳ 載入中...", parse_mode="HTML")
            await show_player_detail(update, context, period, player_idx, edit=True)

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

        playing, resting = [], []
        for p in get_live_roster_cached():
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
            f"📅 點選「今日分析」選擇球員查看出賽狀況與近期趨勢",
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
