#!/bin/bash
# 部署 yahoo_token.json 到 Railway Volume (/data)
# 前置條件: 已安裝 Railway CLI 並登入 (`railway login`)

set -e

PROJECT_DIR="D:/Vibe coding/fantasy-nba-demo"
TOKEN_FILE="$PROJECT_DIR/yahoo_token.json"

echo "🚀 開始部署 token 到 Railway Volume..."
echo "📍 Token 檔案: $TOKEN_FILE"

# 檢查 token 檔案是否存在
if [ ! -f "$TOKEN_FILE" ]; then
    echo "❌ 錯誤: 找不到 $TOKEN_FILE"
    exit 1
fi

# 檢查 Railway CLI 是否已安裝
if ! command -v railway &> /dev/null; then
    echo "❌ 錯誤: Railway CLI 未安裝"
    echo "💡 請先執行: npm install -g @railway/cli"
    exit 1
fi

echo "✓ Token 檔案存在"
echo "✓ Railway CLI 已安裝"
echo ""

# 讀取 token 內容
TOKEN_CONTENT=$(cat "$TOKEN_FILE")

echo "📤 上傳到 Railway /data 目錄..."

# 使用 railway exec 執行遠端命令
# 通過 cat 和 heredoc 建立檔案，避免引號問題
cd "$PROJECT_DIR"

railway exec -- sh -c "
mkdir -p /data
cat > /data/yahoo_token.json << 'TOKENEOF'
$TOKEN_CONTENT
TOKENEOF
echo '✓ 檔案已建立: /data/yahoo_token.json'
cat /data/yahoo_token.json | wc -l
echo '行'
"

echo ""
echo "✅ 部署完成！"
echo "⚡ 下一步:"
echo "   1. Railway Dashboard → 手動 Redeploy"
echo "   2. 驗證: curl https://web-production-d742.up.railway.app/api/token-status"
