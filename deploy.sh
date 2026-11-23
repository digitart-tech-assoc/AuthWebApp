#!/bin/bash

# AuthWebApp デプロイスクリプト
# 使用方法: ./deploy.sh [version]
# 例: ./deploy.sh v0.1.0
#
# 環境変数:
#   SKIP_DB_INIT: "true" に設定すると、DB スキーマ初期化をスキップ（本番環境推奨）
#               デフォルト: "true"（初期化をスキップ）
#               初期化を強制実行するには環境変数を unset してください
#
# 例: SKIP_DB_INIT=false ./deploy.sh v0.1.0  # DB初期化を実行
#    ./deploy.sh v0.1.0                      # DB初期化をスキップ（デフォルト）

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
if [ -z "$NEXT_PUBLIC_SUPABASE_URL" ] || [ -z "$NEXT_PUBLIC_SUPABASE_ANON_KEY" ] || [ -z "$NEXT_PUBLIC_BACKEND_URL" ] || [ -z "$NEXT_PUBLIC_SITE_URL" ]; then
  echo "❌ Error: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_BACKEND_URL, and NEXT_PUBLIC_SITE_URL are required"
  exit 1
fi

# 1. Docker イメージをビルド
echo ""
echo "[1/6] Building Docker images..."
echo "  - Building frontend with NEXT_PUBLIC_* build args..."
docker build -t authwebapp-frontend:$VERSION -t authwebapp-frontend:latest \
  -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_SUPABASE_URL="$NEXT_PUBLIC_SUPABASE_URL" \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY="$NEXT_PUBLIC_SUPABASE_ANON_KEY" \
  --build-arg NEXT_PUBLIC_BACKEND_URL="$NEXT_PUBLIC_BACKEND_URL" \
  --build-arg NEXT_PUBLIC_SITE_URL="$NEXT_PUBLIC_SITE_URL" \
  frontend/

echo "  - Building backend..."
docker build -t authwebapp-backend:$VERSION -t authwebapp-backend:latest -f backend/Dockerfile backend/

echo "  - Building discord-bot..."
docker build -t authwebapp-discord-bot:$VERSION -t authwebapp-discord-bot:latest -f discord-bot/Dockerfile discord-bot/

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
docker save authwebapp-frontend:$VERSION authwebapp-frontend:latest | microk8s ctr images import -

echo "  - Loading backend image..."
docker save authwebapp-backend:$VERSION authwebapp-backend:latest | microk8s ctr images import -

echo "  - Loading discord-bot image..."
docker save authwebapp-discord-bot:$VERSION authwebapp-discord-bot:latest | microk8s ctr images import -

# 4. TLS 証明書を確認
# 証明書は cert-manager が管理する（k8s-certs リポジトリの Certificate auth-digitart-jp）。
# Secret auth-digitart-jp-tls は cert-manager が作成・更新するため、ここでは作成・削除しない。
echo ""
echo "[4/6] Checking TLS certificate managed by cert-manager..."
if ! microk8s kubectl wait --for=condition=Ready certificate/auth-digitart-jp --timeout=60s >/dev/null 2>&1; then
  echo "  ❌ Error: Certificate auth-digitart-jp is not Ready (k8s-certs リポジトリを適用済みか確認してください)"
  exit 1
fi
echo "  ✓ Certificate auth-digitart-jp is Ready"

# 4.5 Secret の生成
echo ""
echo "[4.5/6] Generating k8s secret from .env..."
mkdir -p k8s/secrets
if [ -f .env ]; then
  microk8s kubectl create secret generic authwebapp-secret --from-env-file=.env --dry-run=client -o yaml > k8s/secrets/authwebapp-secret.yaml
  echo "  ✓ k8s/secrets/authwebapp-secret.yaml generated successfully"
else
  echo "  ❌ Error: .env file is required for generating secrets"
  exit 1
fi

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

echo ""
echo "Waiting for rollouts to complete..."
for deployment in authwebapp-backend-deployment authwebapp-frontend-deployment authwebapp-discord-bot-deployment; do
  microk8s kubectl rollout status deployment/$deployment --timeout=5m || {
    echo "⚠ Timeout waiting for $deployment"
  }
done

# TLS 証明書の確認
echo ""
echo "Verifying TLS certificate..."
CERT_INFO=$(microk8s kubectl get secret auth-digitart-jp-tls -o jsonpath='{.data.tls\.crt}' 2>/dev/null | base64 -d | openssl x509 -noout -subject -enddate 2>/dev/null || echo "N/A")
echo "  Certificate: $CERT_INFO"

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
echo "Database configuration:"
echo "  SKIP_DB_INIT: ${SKIP_DB_INIT:-true} (set in k8s/deployment.yaml)"
echo "  - true : DB schema initialization is SKIPPED (default for production)"
echo "  - false: DB schema initialization RUNS"
echo ""
echo "Access the application: https://auth.digitart.jp"
echo "=========================================="
