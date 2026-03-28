#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署 yahoo_token.json 到 Railway Volume (/data)
前置條件: 已安裝 Railway CLI (`npm install -g @railway/cli`)
        已登入 Railway (`railway login`)
"""

import json
import subprocess
import sys
import io
from pathlib import Path

# Windows UTF-8 支援
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_railway_cli():
    """檢查 Railway CLI 是否已安裝"""
    try:
        subprocess.run(['railway', '--version'], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def read_token():
    """讀取本地 yahoo_token.json"""
    token_file = Path('yahoo_token.json')
    if not token_file.exists():
        print(f"❌ 錯誤: 找不到 {token_file}")
        return None

    try:
        with open(token_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 錯誤: 無法讀取 token 檔案: {e}")
        return None

def deploy_to_railway(token_json):
    """通過 railway exec 部署 token 到 /data/yahoo_token.json"""
    token_content = json.dumps(token_json, indent=2, ensure_ascii=False)

    # 建立遠端命令
    cmd = f"""
mkdir -p /data
cat > /data/yahoo_token.json << 'TOKENEOF'
{token_content}
TOKENEOF
echo '✓ 檔案已建立: /data/yahoo_token.json'
ls -lh /data/yahoo_token.json
"""

    try:
        result = subprocess.run(
            ['railway', 'exec', '--', 'sh', '-c', cmd],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✅ 部署成功！")
            print("\n📋 遠端輸出:")
            print(result.stdout)
            return True
        else:
            print(f"❌ 部署失敗 (exit code: {result.returncode})")
            print("\n📋 錯誤輸出:")
            print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("❌ 命令執行超時")
        return False
    except Exception as e:
        print(f"❌ 執行失敗: {e}")
        return False

def main():
    print("🚀 部署 yahoo_token.json 到 Railway Volume (/data)")
    print("=" * 60)
    print()

    # 檢查 Railway CLI
    print("🔍 檢查 Railway CLI...")
    if not check_railway_cli():
        print("❌ 錯誤: Railway CLI 未安裝")
        print("💡 請先執行: npm install -g @railway/cli")
        print("💡 然後登入: railway login")
        sys.exit(1)
    print("✓ Railway CLI 已安裝")
    print()

    # 讀取 token
    print("📖 讀取本地 yahoo_token.json...")
    token = read_token()
    if token is None:
        sys.exit(1)
    print(f"✓ Token 讀取成功 (created_at: {token.get('created_at')})")
    print()

    # 確認部署
    print("⚠️  確認部署到 Railway Volume?")
    response = input("輸入 'yes' 確認: ").strip().lower()
    if response != 'yes':
        print("❌ 已取消")
        sys.exit(1)
    print()

    # 部署
    print("📤 上傳到 Railway /data 目錄...")
    if deploy_to_railway(token):
        print()
        print("=" * 60)
        print("✅ 部署完成！")
        print()
        print("⚡ 後續步驟:")
        print("   1. Railway Dashboard → web service → Redeploy")
        print("   2. 等待 ~1-2 分鐘部署完成")
        print("   3. 驗證:")
        print("      curl https://web-production-d742.up.railway.app/api/token-status")
        print()
        print("💡 預期結果: {\"status\": \"ok\", \"source\": \"file\", ...}")
    else:
        print()
        print("❌ 部署失敗，請檢查:")
        print("   1. 已執行 railway login?")
        print("   2. 在正確的專案目錄?")
        print("   3. Railway 有 Volume 掛載到 /data?")
        sys.exit(1)

if __name__ == '__main__':
    main()
