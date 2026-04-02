#!/bin/bash

# AuthWebApp デプロイスクリプト
# 使用方法: ./deploy.sh [version]
# 例: ./deploy.sh v0.1.0

set -e

VERSION=${1:-v0.1.0}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Deploying AuthWebApp - Version: $VERSION"
echo "=========================================="

# .env ファイルから環境変数を読み込む
if [ -f .env ]; then
  echo "Loading environment variables from .env..."
  export $(grep '^NEXT_PUBLIC_' .env | xargs)
else
  echo "⚠ Warning: .env file not found"
fi

# Frontend ビルドに必要な環境変数を確認
if [ -z "$NEXT_PUBLIC_SUPABASE_URL" ] || [ -z "$NEXT_PUBLIC_SUPABASE_ANON_KEY" ]; then
  echo "❌ Error: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are required"
  exit 1
fi

# 1. Docker イメージをビルド
echo ""
echo "[1/6] Building Docker images..."
echo "  - Building frontend with NEXT_PUBLIC_* build args..."
docker build -t authwebapp-frontend:$VERSION \
  -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_SUPABASE_URL="$NEXT_PUBLIC_SUPABASE_URL" \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY="$NEXT_PUBLIC_SUPABASE_ANON_KEY" \
  frontend/

echo "  - Building backend..."
docker build -t authwebapp-backend:$VERSION -f backend/Dockerfile backend/

echo "  - Building discord-bot..."
docker build -t authwebapp-discord-bot:$VERSION -f discord-bot/Dockerfile discord-bot/

# 2. ディスク容量チェック
echo ""
echo "[2/6] Checking disk space..."
AVAILABLE_SPACE=$(df /var/lib/docker | awk 'NR==2 {print $4}')
REQUIRED_SPACE=$((3 * 1024 * 1024))  # 3GB in KB

if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
  echo "⚠ Warning: Low disk space available ($(($AVAILABLE_SPACE / 1024 / 1024))GB)"
  echo "  Cleaning up old Docker resources..."
  docker image prune -af --filter "until=72h" 2>/dev/null || true
  docker container prune -f 2>/dev/null || true
fi

# 3. MicroK8s にイメージをインポート（パイプで直接ロード）
echo ""
echo "[3/6] Importing images to MicroK8s..."
echo "  - Loading frontend image..."
docker save authwebapp-frontend:$VERSION | microk8s ctr images import -

echo "  - Loading backend image..."
docker save authwebapp-backend:$VERSION | microk8s ctr images import -

echo "  - Loading discord-bot image..."
docker save authwebapp-discord-bot:$VERSION | microk8s ctr images import -

# 4. TLS Secret を確認・再作成
echo ""
echo "[4/6] Ensuring TLS Secret is properly configured..."

# 既存の Secret を削除（古いハッシュ付きの Secret も削除）
echo "  - Cleaning up old TLS Secrets..."
microk8s kubectl delete secret authwebapp-tls 2>/dev/null || true
microk8s kubectl delete secret -l app=authwebapp,type=tls 2>/dev/null || true

# TLS ファイルが存在することを確認
if [ ! -f k8s/secrets/tls.crt ] || [ ! -f k8s/secrets/tls.key ]; then
  echo "  ❌ Error: k8s/secrets/tls.crt or k8s/secrets/tls.key not found"
  exit 1
fi

# Secret が確実に削除されるまで待つ
sleep 2

echo "  ✓ TLS Secret cleanup complete"

# 5. Kubernetes にデプロイ
echo ""
echo "[5/6] Deploying to Kubernetes..."
microk8s kubectl apply -k k8s/

# 6. Pod の再起動と確認
echo ""
echo "[6/6] Restarting deployments..."
for deployment in authwebapp-backend-deployment authwebapp-frontend-deployment authwebapp-discord-bot-deployment; do
  echo "  - Restarting $deployment..."
  microk8s kubectl rollout restart deployment/$deployment
done

# Ingress コントローラーを再起動して新しい Secret をロード
echo "  - Restarting Ingress controller..."
microk8s kubectl rollout restart deployment -n ingress -l app.kubernetes.io/name=nginx-ingress 2>/dev/null || true

echo ""
echo "Waiting for rollouts to complete..."
for deployment in authwebapp-backend-deployment authwebapp-frontend-deployment authwebapp-discord-bot-deployment; do
  microk8s kubectl rollout status deployment/$deployment --timeout=5m || {
    echo "⚠ Timeout waiting for $deployment"
  }
done

# TLS Secret が正しく作成されたか確認
echo ""
echo "Verifying TLS Secret..."
sleep 3
TLS_SECRET=$(microk8s kubectl get secret authwebapp-tls -o jsonpath='{.metadata.name}' 2>/dev/null || echo "")
if [ -z "$TLS_SECRET" ]; then
  echo "⚠ Warning: TLS Secret not found. Checking k8s/secrets files..."
  ls -lh k8s/secrets/tls.*
else
  echo "✓ TLS Secret verified: $TLS_SECRET"
  CERT_SUBJECT=$(microk8s kubectl get secret authwebapp-tls -o jsonpath='{.data.tls\.crt}' 2>/dev/null | base64 -d | openssl x509 -noout -subject 2>/dev/null || echo "N/A")
  echo "  Certificate Subject: $CERT_SUBJECT"
fi

echo ""
echo "=========================================="
echo "✅ Deployment completed successfully!"
echo "=========================================="
echo ""
echo "Deployed images (Version: $VERSION):"
echo "  - authwebapp-frontend:$VERSION"
echo "  - authwebapp-backend:$VERSION"
echo "  - authwebapp-discord-bot:$VERSION"
echo ""
echo "Next steps:"
echo "  1. Check deployment status:"
echo "     microk8s kubectl get pods"
echo "     microk8s kubectl get services"
echo ""
echo "  2. Verify TLS configuration:"
echo "     microk8s kubectl get ingress authwebapp-ingress -o wide"
echo ""
echo "  3. View deployment logs:"
echo "     microk8s kubectl logs -f deployment/authwebapp-frontend-deployment"
echo "     microk8s kubectl logs -f deployment/authwebapp-backend-deployment"
echo "     microk8s kubectl logs -f deployment/authwebapp-discord-bot-deployment"
echo ""
echo "Access the application: https://auth.digitart.jp"
echo "=========================================="
