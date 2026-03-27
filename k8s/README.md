# k8s デプロイ手順

このディレクトリには `auth-app` アプリケーション向けの Kubernetes マニフェストの例が含まれます。

重要: 本番では Secrets を直接ファイルに置かず、SealedSecrets / ExternalSecrets / Vault 等を利用してください。

主なファイル:
- `namespace.yaml` - Namespace を作成します。
- `backend-deployment.yaml` - バックエンド Deployment（イメージを自分のレジストリに変更してください）。
- `backend-service.yaml` - ClusterIP Service。
- `ingress.yaml` - `auth.digitart.jp` で公開する Ingress（cert-manager 注釈あり）。
- `configmap.yaml` - 非機密な設定。
- `secret-example.yaml` - 機密環境変数の例（本番は別の仕組みを推奨）。

基本デプロイ手順（例）:

1. イメージをビルドしてレジストリへ push

```bash
# 例: backend ディレクトリで Docker ビルド
docker build -t registry.example.com/authwebapp/backend:latest -f backend/Dockerfile backend
docker push registry.example.com/authwebapp/backend:latest
```

2. レジストリ認証情報を Kubernetes に登録（必要な場合）

```bash
# Docker レジストリ用の secret を作成
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=YOUR_USER \
  --docker-password=YOUR_PASS \
  --docker-email=you@example.com \
  --namespace auth-app
```

3. Namespace と ConfigMap を作成

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
```

4. Secret を作成（.env ファイルから作る例）

```bash
# .env に機密値を入れた上で
kubectl create secret generic auth-secret --from-env-file=.env --namespace auth-app

# もしくは個別に
kubectl create secret generic auth-secret \
  --from-literal=DATABASE_URL='postgresql://user:pass@host:5432/db' \
  --from-literal=SECRET_KEY='your-secret' \
  --namespace auth-app
```

5. Deployment と Service と Ingress を適用

```bash
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/ingress.yaml
```

6. ロールアウトの確認

```bash
kubectl -n auth-app get pods
kubectl -n auth-app rollout status deployment/auth-backend
kubectl -n auth-app describe ingress auth-ingress
```

TLS と cert-manager:
- `ingress.yaml` では `cert-manager.io/cluster-issuer: letsencrypt-prod` を使う想定です。CertManager と ClusterIssuer をクラスタに用意しておいてください。

環境変数の扱い方まとめ:
- 機密値（DB パスワード、API キー等）は Kubernetes `Secret` に入れて、`envFrom: secretRef` で Pod に注入します。
- 非機密設定（環境名、BASE_URL 等）は `ConfigMap` に入れて `envFrom: configMapRef` で注入します。
- 本番運用では `SealedSecrets` / `ExternalSecrets` / Vault 等で安全に管理してください。

デプロイ先 URL は `https://auth.digitart.jp`（Ingress の `host` を変更済み）です。
