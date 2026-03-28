#!/usr/bin/env python3
"""
Fetch 2025-26 NBA season data and save to JSON files.
Creates:
  - players_data.json (full season stats, all 570 players, 67 fields)
  - players_recent.json (last 15 games, 493 players)
"""

import json
import os
from datetime import datetime
from nba_api.stats.endpoints import leaguedashplayerstats

SEASON = "2025-26"
OUTPUT_DIR = os.path.dirname(__file__)

def fetch_season_data():
    """Fetch full 2025-26 season per-game statistics."""
    print("[1/2] Fetching 2025-26 season stats...")
    endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        per_mode_detailed="PerGame",
        timeout=60,
    )
    df = endpoint.get_data_frames()[0]

    # Convert to clean records
    records = []
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            val = row[col]
            # Round floats to 3 decimals, keep integers and strings as-is
            if isinstance(val, float):
                record[col] = round(val, 3)
            else:
                record[col] = val
        records.append(record)

    return records, df.columns.tolist()


def fetch_recent_data():
    """Fetch last 15 games per-game statistics."""
    print("[2/2] Fetching last 15 games stats...")
    endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        per_mode_detailed="PerGame",
        last_n_games=15,
        timeout=60,
    )
    df = endpoint.get_data_frames()[0]

    records = []
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            val = row[col]
            if isinstance(val, float):
                record[col] = round(val, 3)
            else:
                record[col] = val
        records.append(record)

    return records, df.columns.tolist()


def main():
    print("\n" + "="*60)
    print(" NBA Data Fetcher — 2025-26 Season")
    print("="*60 + "\n")

    # Fetch data
    season_data, columns = fetch_season_data()
    recent_data, _ = fetch_recent_data()

    # Create output structure
    output = {
        "metadata": {
            "season": SEASON,
            "fetched_at": datetime.now().isoformat(),
            "season_players": len(season_data),
            "recent_players": len(recent_data),
            "fields": columns,
            "field_count": len(columns),
        },
        "season": {
            "players": season_data,
        },
        "recent": {
            "window": "Last 15 Games",
            "players": recent_data,
        }
    }

    # Save to JSON
    output_file = os.path.join(OUTPUT_DIR, "players_data.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    file_size = os.path.getsize(output_file) / 1024 / 1024

    print(f"\n[OK] Data saved to: {output_file}")
    print(f"  File size: {file_size:.1f} MB")
    print(f"  Season players: {len(season_data)}")
    print(f"  Recent players: {len(recent_data)}")
    print(f"  Fields per player: {len(columns)}")
    print("\n" + "="*60)
    print("Sample Player (Top Fantasy):")
    print("="*60)

    # Find top fantasy player
    top = max(season_data, key=lambda x: x.get("NBA_FANTASY_PTS", 0))

    print(f"\nName: {top['PLAYER_NAME']}")
    print(f"Team: {top['TEAM_ABBREVIATION']}")
    print(f"GP: {top['GP']}")
    print(f"\nScoring:")
    print(f"  PTS: {top['PTS']:.1f}  FG: {top['FGM']:.1f}/{top['FGA']:.1f} ({top['FG_PCT']*100:.1f}%)")
    print(f"  3P:  {top['FG3M']:.1f}/{top['FG3A']:.1f} ({top['FG3_PCT']*100:.1f}%)")
    print(f"  FT:  {top['FTM']:.1f}/{top['FTA']:.1f} ({top['FT_PCT']*100:.1f}%)")
    print(f"\nRebounds:")
    print(f"  Total: {top['REB']:.1f}  Offensive: {top['OREB']:.1f}  Defensive: {top['DREB']:.1f}")
    print(f"\nAssists/Turnovers:")
    print(f"  AST: {top['AST']:.1f}  TOV: {top['TOV']:.1f}")
    print(f"\nDefense:")
    print(f"  STL: {top['STL']:.1f}  BLK: {top['BLK']:.1f}")
    print(f"\nAdvanced:")
    print(f"  Fantasy Pts: {top['NBA_FANTASY_PTS']:.1f}")
    print(f"  +/-: {top['PLUS_MINUS']:.1f}")
    print(f"  DD2: {int(top['DD2'])}  TD3: {int(top['TD3'])}")
    print(f"  Fantasy Rank: #{int(top['NBA_FANTASY_PTS_RANK'])}")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
