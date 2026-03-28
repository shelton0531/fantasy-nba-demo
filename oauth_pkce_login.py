#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yahoo Fantasy API - PKCE OAuth 2.0 認證（手動 URL 方式）
適用於 Public Client（無 Client Secret）

流程：
1. 生成 PKCE code_challenge
2. 打開瀏覽器進行授權
3. 用戶授權後複製瀏覽器地址栏的完整 URL
4. 貼回終端機（腳本自動提取 code）
5. 交換 Access Token
6. 保存到 yahoo_token.json
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
import json
import webbrowser
import requests
import hashlib
import base64
import secrets
from urllib.parse import urlencode, parse_qs, urlparse

# ===== 配置 =====
CLIENT_ID = "dj0yJmk9SkpaNnQ2ZHVZOTFaJmQ9WVdrOVQzSnhPWEpIWW5vbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWM3"
REDIRECT_URI = "https://localhost"
LEAGUE_ID = 46147

AUTHORIZATION_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"

def generate_pkce():
    """生成 PKCE code_verifier 和 code_challenge"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
    code_verifier = code_verifier.rstrip('=')

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8')
    code_challenge = code_challenge.rstrip('=')

    return code_verifier, code_challenge

def step1_generate_auth_url():
    """步驟 1：生成授權 URL"""
    print("=" * 75)
    print("  Yahoo Fantasy API - PKCE OAuth 2.0 認證")
    print("=" * 75)
    print()
    print("[步驟 1] 生成授權 URL...")

    code_verifier, code_challenge = generate_pkce()

    # 暫時保存 code_verifier 以備後用
    with open('_pkce_verifier.tmp', 'w') as f:
        f.write(code_verifier)

    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }

    auth_url = AUTHORIZATION_URL + '?' + urlencode(params)

    print("✓ 授權 URL 已生成")
    print()
    return auth_url, code_verifier

def step2_open_browser(auth_url):
    """步驟 2：打開瀏覽器"""
    print("[步驟 2] 打開瀏覽器進行授權...")
    print()

    try:
        webbrowser.open(auth_url)
        print("✓ 瀏覽器已打開")
    except:
        print("⚠ 無法自動打開瀏覽器，請手動訪問下面的 URL:")
        print(auth_url)

    print()
    print("=" * 75)
    print("  請在瀏覽器中完成以下步驟：")
    print("=" * 75)
    print()
    print("  1. 登入你的 Yahoo 帳號")
    print("  2. 點擊「同意授權」按鈕")
    print("  3. 瀏覽器會顯示「無法連接」（這是正常的）")
    print("  4. 複製瀏覽器地址栏的完整 URL（https://localhost?code=...）")
    print()

def extract_code_from_url(redirect_url):
    """從重定向 URL 中提取 authorization code"""
    try:
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        if 'code' in params:
            return params['code'][0]
        elif 'error' in params:
            error = params['error'][0]
            error_desc = params.get('error_description', ['Unknown'])[0]
            print(f"✗ 授權被拒絕")
            print(f"  錯誤: {error}")
            print(f"  原因: {error_desc}")
            return None
        else:
            print("✗ URL 中未找到 code 參數")
            return None
    except Exception as e:
        print(f"✗ 無法解析 URL: {str(e)}")
        return None

def step3_get_redirect_url():
    """步驟 3：獲取重定向 URL"""
    print("[步驟 3] 輸入重定向 URL...")
    print()
    print("貼上從瀏覽器複製的完整 URL（以 https://localhost 開頭）:")
    print()

    while True:
        redirect_url = input("請貼上 URL: ").strip()

        if redirect_url.startswith('https://localhost'):
            code = extract_code_from_url(redirect_url)
            if code:
                print()
                print(f"✓ 成功提取 Authorization Code")
                print(f"  立即開始交換 Token（授權碼有效期很短）...")
                return code
            else:
                print("✗ 無法從 URL 中提取有效的 code，請重試")
                print()
        else:
            print("✗ URL 應以 'https://localhost' 開頭，請重試")
            print()

def step4_exchange_token(auth_code, code_verifier):
    """步驟 4：交換 Access Token"""
    print()
    print("[步驟 4] 交換 Access Token...")

    try:
        data = {
            'client_id': CLIENT_ID,
            'grant_type': 'authorization_code',
            'code': auth_code,
            'code_verifier': code_verifier,
            'redirect_uri': REDIRECT_URI
        }

        response = requests.post(TOKEN_URL, data=data, timeout=10)

        if response.status_code != 200:
            print(f"✗ HTTP {response.status_code}")
            print(f"  錯誤: {response.text[:200]}")
            return None

        token_data = response.json()

        if 'access_token' not in token_data:
            print(f"✗ 無效回應：{token_data}")
            return None

        print("✓ 成功獲得 Access Token")
        print(f"  Token: {token_data['access_token'][:30]}...")
        print(f"  有效期: {token_data.get('expires_in', '3600')} 秒")

        return token_data

    except requests.exceptions.RequestException as e:
        print(f"✗ 網路錯誤: {str(e)[:100]}")
        return None
    except Exception as e:
        print(f"✗ 錯誤: {str(e)[:100]}")
        return None

def step5_save_token(token_data):
    """步驟 5：保存 Token"""
    print()
    print("[步驟 5] 保存配置...")

    token_config = {
        'access_token': token_data.get('access_token'),
        'refresh_token': token_data.get('refresh_token'),
        'expires_in': token_data.get('expires_in'),
        'token_type': token_data.get('token_type', 'Bearer'),
        'scope': token_data.get('scope'),
        'created_at': int(__import__('time').time())
    }

    token_file = 'yahoo_token.json'
    with open(token_file, 'w', encoding='utf-8') as f:
        json.dump(token_config, f, indent=2, ensure_ascii=False)
    print(f"✓ Token 已保存到 {token_file}")

def run_oauth_flow():
    """完整的 OAuth PKCE 流程"""
    try:
        # 步驟 1：生成授權 URL
        auth_url, code_verifier = step1_generate_auth_url()

        # 步驟 2：打開瀏覽器
        step2_open_browser(auth_url)

        # 步驟 3：獲取重定向 URL 並提取 code
        auth_code = step3_get_redirect_url()

        # 步驟 4：交換 Token
        token_data = step4_exchange_token(auth_code, code_verifier)

        if token_data is None:
            return False

        # 步驟 5：保存配置
        step5_save_token(token_data)

        return True

    except KeyboardInterrupt:
        print("\n\n✗ 已取消")
        return False
    except Exception as e:
        print(f"\n✗ 發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def complete_token_exchange_with_saved_verifier(auth_code):
    """使用已保存的 code_verifier 完成 token 交換"""
    try:
        # 讀取已保存的 code_verifier
        with open('_pkce_verifier.tmp', 'r') as f:
            code_verifier = f.read().strip()
    except FileNotFoundError:
        print("✗ 找不到已保存的 code_verifier，請重新執行 oauth_pkce_login.py")
        return False

    print("\n[步驟 4] 交換 Access Token...")

    try:
        data = {
            'client_id': CLIENT_ID,
            'grant_type': 'authorization_code',
            'code': auth_code,
            'code_verifier': code_verifier,
            'redirect_uri': REDIRECT_URI
        }

        response = requests.post(TOKEN_URL, data=data, timeout=10)

        if response.status_code != 200:
            print(f"✗ HTTP {response.status_code}")
            print(f"  錯誤: {response.text[:200]}")
            return False

        token_data = response.json()

        if 'access_token' not in token_data:
            print(f"✗ 無效回應：{token_data}")
            return False

        print("✓ 成功獲得 Access Token")
        print(f"  Token: {token_data['access_token'][:30]}...")
        print(f"  有效期: {token_data.get('expires_in', '3600')} 秒")

        # 保存 Token
        print("\n[步驟 5] 保存配置...")
        token_config = {
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in'),
            'token_type': token_data.get('token_type', 'Bearer'),
            'scope': token_data.get('scope'),
            'created_at': int(__import__('time').time())
        }

        token_file = 'yahoo_token.json'
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(token_config, f, indent=2, ensure_ascii=False)
        print(f"✓ Token 已保存到 {token_file}")

        # 清理臨時文件
        os.remove('_pkce_verifier.tmp')

        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ 網路錯誤: {str(e)[:100]}")
        return False
    except Exception as e:
        print(f"✗ 錯誤: {str(e)[:100]}")
        return False

if __name__ == "__main__":
    success = run_oauth_flow()

    print()
    print("=" * 75)
    if success:
        print("  ✓ OAuth 認證成功！")
        print("=" * 75)
        print()
        print("Token 已保存到 yahoo_token.json")
        print("你現在可以使用 Yahoo Fantasy API")
        print()
        print("下一步：執行 Flask 應用")
        print("  python3 -m flask run --port 5000")
        sys.exit(0)
    else:
        print("  ✗ OAuth 認證失敗")
        print("=" * 75)
        sys.exit(1)
