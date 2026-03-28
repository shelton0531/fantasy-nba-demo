#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用已保存的 code_verifier 完成 OAuth Token 交換
（當 oauth_pkce_login.py 取得授權碼後，立即執行此腳本）
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
import json
import requests
import time
from urllib.parse import parse_qs, urlparse

# 設定
CLIENT_ID = "dj0yJmk9SkpaNnQ2ZHVZOTFaJmQ9WVdrOVQzSnhPWEpIWW5vbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWM3"
REDIRECT_URI = "https://localhost"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"

def main():
    print("=" * 75)
    print("  Yahoo OAuth Token 交換")
    print("=" * 75)
    print()

    # 讀取已保存的 code_verifier
    print("[步驟 1] 讀取已保存的 code_verifier...")
    try:
        with open('_pkce_verifier.tmp', 'r') as f:
            code_verifier = f.read().strip()
        print("✓ 已讀取 code_verifier")
    except FileNotFoundError:
        print("✗ 找不到 _pkce_verifier.tmp")
        print("   請先執行 python3 oauth_pkce_login.py 並貼上授權碼網址")
        return False

    print()
    print("[步驟 2] 取得授權碼...")

    # 從使用者輸入取得授權網址
    print("請貼上瀏覽器網址列中的完整 URL（以 https://localhost 開頭）:")
    redirect_url = input("URL: ").strip()
    print()

    # 解析授權碼
    try:
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        if 'code' not in params:
            print("✗ 網址中找不到授權碼")
            return False

        auth_code = params['code'][0]
        print(f"✓ 已提取授權碼: {auth_code[:20]}...")
    except Exception as e:
        print(f"✗ 無法解析網址: {str(e)}")
        return False

    print()
    print("[步驟 3] 交換 Access Token...")

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
            print(f"  錯誤: {response.text[:300]}")
            return False

        token_data = response.json()

        if 'access_token' not in token_data:
            print(f"✗ 無效回應：{token_data}")
            return False

        print("✓ 成功取得 Access Token")
        print(f"  Token: {token_data['access_token'][:30]}...")
        print(f"  有效期: {token_data.get('expires_in', '3600')} 秒")

    except requests.exceptions.RequestException as e:
        print(f"✗ 網路錯誤: {str(e)[:100]}")
        return False
    except Exception as e:
        print(f"✗ 錯誤: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        return False

    # 保存 Token
    print()
    print("[步驟 4] 保存設定...")
    try:
        token_config = {
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in'),
            'token_type': token_data.get('token_type', 'Bearer'),
            'scope': token_data.get('scope'),
            'created_at': int(time.time())
        }

        with open('yahoo_token.json', 'w', encoding='utf-8') as f:
            json.dump(token_config, f, indent=2, ensure_ascii=False)
        print("✓ Token 已保存至 yahoo_token.json")

        # 清理暫時檔案
        if os.path.exists('_pkce_verifier.tmp'):
            os.remove('_pkce_verifier.tmp')
            print("✓ 已清理暫時檔案")

        return True

    except Exception as e:
        print(f"✗ 保存失敗: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()

    print()
    print("=" * 75)
    if success:
        print("  ✓ OAuth 認證成功！")
        print("=" * 75)
        print()
        print("Token 已保存到 yahoo_token.json")
        print("下一步：整合 Yahoo API 到 data_loader.py")
        sys.exit(0)
    else:
        print("  ✗ OAuth 認證失敗")
        print("=" * 75)
        sys.exit(1)
