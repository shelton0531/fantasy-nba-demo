"""
Yahoo Fantasy API 配置（OAuth 2.0 PKCE）
"""

import json
import os
from pathlib import Path

# ===== 認證配置 =====
AUTH_METHOD = "oauth2"
CLIENT_ID = "dj0yJmk9SkpaNnQ2ZHVZOTFaJmQ9WVdrOVQzSnhPWEpIWW5vbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWM3"
REDIRECT_URI = "https://localhost:8443/callback"

# ===== 聯盟配置 =====
LEAGUE_ID = 46147
CURRENT_WEEK = int(os.environ.get('CURRENT_WEEK', 22))
USER_TEAM_ID = 2  # 您的隊伍 ID

# ===== API 端點 =====
YAHOO_FANTASY_API_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"
YAHOO_NBA_LEAGUE_KEY = "466"  # 2025-26 賽季
LEAGUE_KEY = f"{YAHOO_NBA_LEAGUE_KEY}.l.{LEAGUE_ID}"

# ===== Token 管理 =====
# 記憶體暫存（當環境變數模式下 refresh 後使用，避免重新讀取過期 env var）
_token_override = None


def load_token():
    """從記憶體暫存、環境變數或 yahoo_token.json 載入完整 Token 資訊

    優先順序：
    1. _token_override（refresh 後的記憶體暫存）
    2. YAHOO_TOKEN_JSON 環境變數（部署環境）
    3. yahoo_token.json 本地檔案（開發環境）
    """
    global _token_override

    # 1. 記憶體暫存（由 refresh_access_token 設定）
    if _token_override is not None:
        return _token_override

    # 2a. 分開的環境變數（最穩定，避免 JSON 格式問題）
    access_token = os.environ.get('YAHOO_ACCESS_TOKEN')
    refresh_token = os.environ.get('YAHOO_REFRESH_TOKEN')
    if access_token and refresh_token:
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': int(os.environ.get('YAHOO_TOKEN_EXPIRES_IN', 3600)),
            'created_at': int(os.environ.get('YAHOO_TOKEN_CREATED_AT', 0)),
            'token_type': 'bearer',
            'scope': None
        }

    # 2b. 單一 JSON 環境變數（備用）
    token_json = os.environ.get('YAHOO_TOKEN_JSON')
    if token_json:
        try:
            return json.loads(token_json.strip())
        except Exception as e:
            print(f"警告：YAHOO_TOKEN_JSON 環境變數格式錯誤: {e}")

    # 3. 本地檔案（開發環境 / Railway Volume）
    token_file = Path(os.environ.get('TOKEN_DIR', '.')) / 'yahoo_token.json'
    if not token_file.exists():
        return None

    try:
        with open(token_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"警告：無法讀取 yahoo_token.json: {e}")
        return None

def get_access_token():
    """取得有效的 Access Token"""
    token = load_token()
    if token:
        return token.get('access_token')
    return None

def get_refresh_token():
    """取得 Refresh Token（用於續期）"""
    token = load_token()
    if token:
        return token.get('refresh_token')
    return None

def is_token_expired(buffer_seconds=300):
    """檢查 Token 是否已過期或即將過期（預設緩衝 5 分鐘）"""
    import time
    token = load_token()
    if not token:
        return True
    created_at = token.get('created_at', 0)
    expires_in = token.get('expires_in', 3600)
    return (time.time() - created_at) >= (expires_in - buffer_seconds)

def refresh_access_token():
    """使用 refresh_token 更新 Access Token，成功回傳 True

    - 本地開發：寫入 yahoo_token.json
    - 部署環境（YAHOO_TOKEN_JSON 已設定）：更新記憶體暫存，並印出新 JSON 供手動更新
    """
    import time
    import requests

    global _token_override

    token = load_token()
    if not token or not token.get('refresh_token'):
        return False

    is_env_mode = bool(os.environ.get('YAHOO_TOKEN_JSON'))

    try:
        response = requests.post(
            'https://api.login.yahoo.com/oauth2/get_token',
            data={
                'client_id': CLIENT_ID,
                'grant_type': 'refresh_token',
                'refresh_token': token['refresh_token']
            },
            timeout=10
        )

        if response.status_code != 200:
            print(f"[Token 續期] 失敗 HTTP {response.status_code}: {response.text[:100]}")
            return False

        new_token = response.json()
        if 'access_token' not in new_token:
            return False

        updated = {
            'access_token': new_token['access_token'],
            'refresh_token': new_token.get('refresh_token', token['refresh_token']),
            'expires_in': new_token.get('expires_in', 3600),
            'token_type': new_token.get('token_type', 'Bearer'),
            'scope': new_token.get('scope'),
            'created_at': int(time.time())
        }

        if is_env_mode:
            # 部署環境：更新記憶體暫存，無法自動更新環境變數
            _token_override = updated
            print(f"[Token 續期] 成功（記憶體已更新）")
            print(f"[Token 續期] 部署環境請更新 YAHOO_TOKEN_JSON 環境變數為：")
            print(json.dumps(updated, ensure_ascii=False))
        else:
            # 本地開發 / Railway Volume：寫入檔案
            _token_override = None  # 清除暫存，以檔案為準
            with open(Path(os.environ.get('TOKEN_DIR', '.')) / 'yahoo_token.json', 'w', encoding='utf-8') as f:
                json.dump(updated, f, indent=2, ensure_ascii=False)
            print(f"[Token 續期] 成功，已寫入 yahoo_token.json")

        return True

    except Exception as e:
        print(f"[Token 續期] 例外錯誤: {e}")
        return False

def is_configured():
    """檢查是否已完成認證"""
    return CLIENT_ID is not None and load_token() is not None

if __name__ == "__main__":
    print("[Yahoo Fantasy API 配置狀態]")
    print(f"  Auth Method: {AUTH_METHOD}")
    print(f"  Client ID: {CLIENT_ID[:30]}...")
    print(f"  League ID: {LEAGUE_ID}")
    print(f"  League Key: {LEAGUE_KEY}")
    print(f"  User Team ID: {USER_TEAM_ID}")
    print(f"  Current Week: {CURRENT_WEEK}")
    print(f"  Token 狀態: {'✓ 已認證' if is_configured() else '✗ 未認證'}")
    print()
    print(f"總體狀態: {'準備就緒' if is_configured() else '缺少 Access Token'}")
