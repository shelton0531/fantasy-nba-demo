#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yahoo Fantasy API - PKCE OAuth 2.0 自動化伺服器
使用自簽名 HTTPS 伺服器自動接收授權碼並交換 Token
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
import json
import hashlib
import base64
import secrets
import webbrowser
import requests
import ssl
import time
import threading
from urllib.parse import urlencode, parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler

# 設定
CLIENT_ID = "dj0yJmk9SkpaNnQ2ZHVZOTFaJmQ9WVdrOVQzSnhPWEpIWW5vbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWM3"
REDIRECT_URI = "https://localhost:8443/callback"
LEAGUE_ID = 46147

AUTHORIZATION_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"

# 全域變數（儲存 PKCE 參數）
auth_code = None
code_verifier = None
server_instance = None

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """處理 OAuth 回調的 HTTP 請求處理器"""

    def do_GET(self):
        global auth_code

        # 解析 URL
        parsed = urlparse(self.path)

        if parsed.path == '/callback':
            params = parse_qs(parsed.query)

            if 'code' in params:
                auth_code = params['code'][0]
                print(f"\n✓ 已接收授權碼: {auth_code[:20]}...")

                # 自動儲存授權碼到檔案
                try:
                    with open('_auth_code.tmp', 'w') as f:
                        f.write(auth_code)
                except:
                    pass

                # 回傳成功頁面
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()

                response = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>授權成功</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; text-align: center; padding: 50px; }
                        .success { color: #28a745; font-size: 24px; margin-bottom: 20px; }
                        p { color: #666; }
                    </style>
                </head>
                <body>
                    <div class="success">✓ 授權成功！</div>
                    <p>授權碼已自動保存。請立即執行令牌交換指令。</p>
                </body>
                </html>
                """
                self.wfile.write(response.encode('utf-8'))

                # 停止伺服器
                if server_instance:
                    server_instance.shutdown()

            elif 'error' in params:
                error = params['error'][0]
                error_desc = params.get('error_description', ['Unknown'])[0]

                self.send_response(400)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()

                response = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>授權失敗</title>
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; text-align: center; padding: 50px; }}
                        .error {{ color: #dc3545; font-size: 24px; margin-bottom: 20px; }}
                        p {{ color: #666; }}
                    </style>
                </head>
                <body>
                    <div class="error">✗ 授權失敗</div>
                    <p>錯誤: {error}</p>
                    <p>原因: {error_desc}</p>
                </body>
                </html>
                """
                self.wfile.write(response.encode('utf-8'))

                if server_instance:
                    server_instance.shutdown()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """抑制預設日誌"""
        pass


def generate_pkce():
    """生成 PKCE code_verifier 和 code_challenge（正確實作）"""
    import string

    # 只能包含 unreserved characters: A-Z, a-z, 0-9, -, ., _, ~
    UNRESERVED_CHARS = string.ascii_letters + string.digits + '-' + '.' + '_' + '~'

    # 生成 128 字元的 code_verifier（最大長度）
    code_verifier = ''.join(secrets.choice(UNRESERVED_CHARS) for _ in range(128))

    # SHA256 hash
    code_challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()

    # Base64URL encode（不含 padding）
    code_challenge = base64.urlsafe_b64encode(code_challenge_bytes).decode('utf-8').rstrip('=')

    return code_verifier, code_challenge


def start_https_server():
    """啟動 HTTPS 伺服器（在背景 Thread 持續監聽）"""
    global server_instance

    print("[步驟 1] 啟動 HTTPS 伺服器...")

    # 檢查憑證
    if not os.path.exists('cert.pem') or not os.path.exists('key.pem'):
        print("✗ 找不到 SSL 憑證 (cert.pem, key.pem)")
        return False

    server_address = ('localhost', 8443)
    httpd = HTTPServer(server_address, OAuthCallbackHandler)

    # 設定 HTTPS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    server_instance = httpd

    # 在背景 Thread 啟動伺服器（serve_forever 持續監聽，不會超時）
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print("✓ HTTPS 伺服器已啟動於 https://localhost:8443")
    return True


def generate_auth_url():
    """生成授權 URL"""
    global code_verifier

    print("[步驟 2] 生成授權 URL...")

    code_verifier, code_challenge = generate_pkce()

    # 立即儲存 code_verifier 到檔案，確保後續交換時能讀取
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

    print("✓ 授權 URL 已生成（使用 PKCE-S256）")
    print(f"  Code Challenge: {code_challenge}")
    return auth_url


def open_browser_and_wait(auth_url):
    """打開瀏覽器並等待授權"""
    global auth_code, server_instance

    print("[步驟 3] 打開瀏覽器進行授權...")

    try:
        webbrowser.open(auth_url)
        print("✓ 瀏覽器已開啟")
    except:
        print("⚠ 無法自動打開瀏覽器，請手動訪問:")
        print(auth_url)

    print()
    print("=" * 75)
    print("  請在瀏覽器中完成授權")
    print("=" * 75)
    print()
    print("  1. 登入 Yahoo 帳號")
    print("  2. 點擊「同意授權」")
    print("  3. 瀏覽器會自動返回此應用")
    print()

    # 等待授權碼（輪詢全域變數，伺服器在背景 Thread 處理連線）
    print("[步驟 4] 等待授權碼（最多等待 5 分鐘）...")
    timeout = 300  # 5 分鐘
    elapsed = 0
    while auth_code is None and elapsed < timeout:
        time.sleep(0.5)
        elapsed += 0.5

    if auth_code is None:
        print("✗ 等待逾時")
        return None

    print("✓ 授權完成")
    return auth_code


def exchange_token():
    """交換 Access Token"""
    global auth_code, code_verifier

    print("[步驟 5] 交換 Access Token...")

    if not auth_code or not code_verifier:
        print("✗ 缺少授權碼或 code_verifier")
        return None

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
            print(f"  錯誤: {response.text[:500]}")
            return None

        token_data = response.json()

        if 'access_token' not in token_data:
            print(f"✗ 無效回應：{token_data}")
            return None

        print("✓ 成功取得 Access Token")
        print(f"  Token: {token_data['access_token'][:30]}...")
        print(f"  有效期: {token_data.get('expires_in', '3600')} 秒")

        return token_data

    except requests.exceptions.RequestException as e:
        print(f"✗ 網路錯誤: {str(e)[:100]}")
        return None
    except Exception as e:
        print(f"✗ 錯誤: {str(e)[:100]}")
        return None


def save_token(token_data):
    """保存 Token"""
    print()
    print("[步驟 6] 保存設定...")

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


def main():
    """主流程"""
    print("=" * 75)
    print("  Yahoo Fantasy API - PKCE OAuth 2.0 自動化")
    print("=" * 75)
    print()

    # 啟動 HTTPS 伺服器
    if not start_https_server():
        return False

    print()

    # 生成授權 URL
    auth_url = generate_auth_url()

    print()

    # 打開瀏覽器並等待授權
    try:
        open_browser_and_wait(auth_url)
    except KeyboardInterrupt:
        print("\n✗ 已取消")
        return False
    except Exception as e:
        print(f"✗ 錯誤: {str(e)}")
        return False

    print()

    # 交換 Token
    token_data = exchange_token()
    if token_data is None:
        return False

    # 保存 Token
    save_token(token_data)

    return True


if __name__ == "__main__":
    print()
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
