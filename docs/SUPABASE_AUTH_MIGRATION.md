# Supabase Auth（Discord OAuth）への移行 - 実装ガイド

**更新日**: 2026-03-27  
**対象**: Backend API の JWT 検証ロジック

---

## Keycloak から Supabase への変更点

### 1. 認証フロー変更

#### 変更前（Keycloak）
```
NextAuth + Keycloak OAuth2
  ↓
Frontend: Keycloak JWT token
  ↓
Backend: Bearer token で Keycloak JWT を検証
```

#### 変更後（Supabase）
```
Supabase Auth + Discord OAuth provider
  ↓
Frontend: Supabase JWT token（user_metadata に Discord ID 含む）
  ↓
Backend: Bearer token で Supabase JWT を検証
```

---

## Backend 修正項目

### 2.1 JWT 検証の更新（`backend/app/core/auth.py`）

Supabase JWT を検証するよう `get_current_principal()` を更新する必要があります。

#### 変更予定の環境変数

```bash
# KEYCLOAK 関連の削除
- `KEYCLOAK_ISSUER_URL`, `KEYCLOAK_AUDIENCE`, `KEYCLOAK_JWKS_URL` は廃止されました。

# 追加（Supabase）
SUPABASE_ISSUER_URL=https://<PROJECT-ID>.supabase.co
SUPABASE_JWKS_URL=https://<PROJECT-ID>.supabase.co/.well-known/jwks.json
SUPABASE_JWT_SECRET=<JWT-SECRET-from-supabase-dashboard>
```

#### JWT クレーム から Discord ID 取得

Supabase JWT には以下のような user_metadata が含まれます：

```json
{
  "sub": "00000000-0000-0000-0000-000000000000",
  "aud": "authenticated",
  "iss": "https://xxx.supabase.co",
  "user_metadata": {
    "discord_id": "123456789123456789",
    "discord_username": "user#1234",
    "email": "user@discord.com",
    "...": "..."
  }
}
```

**修正コード例**:
```python
def get_current_principal(token: str = Depends(HTTPBearer())) -> dict:
    # JWT 検証
    claims = verify_jwt_token(token.credentials)
    
    # Discord ID 抽出（Supabase user_metadata から）
    discord_id = claims.get("user_metadata", {}).get("discord_id")
    
    # User upsert (既存と同じロジック)
    user = upsert_user(
        user_id=claims.get("sub"),
        discord_id=discord_id
    )
    
    return {
        "sub": claims.get("sub"),
        "discord_id": discord_id,
        "app_role": user["app_role"],
    }
```

### 2.2 Frontend Server Actions 修正（`frontend/src/actions/student-registration.ts`）

**現在のコード** (`getBackendAuthorizationHeader()`):
```typescript
// NextAuth session から Keycloak token 取得
const session = await getSession();
return `Bearer ${session.accessToken}`;
```

**修正後** (`getBackendAuthorizationHeader()`):
```typescript
// Supabase session から JWT token 取得
const { data: { session } } = await supabase.auth.getSession();
return `Bearer ${session?.access_token}`;
```

---

## 必要なテーブル

### 既に実装済み
- ✅ `student_profiles` (0003_add_student_registration.py)
- ✅ `otp_records` (0003_add_student_registration.py)

### 追加で必要（未実装）
- ❌ `users` - Supabase user ID と Discord ID のマッピング

#### `users` テーブル作成マイグレーション

```python
# backend/alembic/versions/0004_add_users_table.py

"""add users table for supabase auth mapping

Revision ID: 0004_add_users_table
Revises: 0003_add_student_registration
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_add_users_table"
down_revision = "0003_add_student_registration"

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Text(), primary_key=True),  # Supabase user ID (UUID)
        sa.Column("discord_id", sa.Text(), unique=True, nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("is_alumni", sa.Boolean(), server_default=sa.false()),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted", sa.Boolean(), server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_users_discord_id", "users", ["discord_id"])

def downgrade() -> None:
    op.drop_index("idx_users_discord_id")
    op.drop_table("users")
```

---

## 実装優先度

### Phase 1: Backend修正 ⏳
- [ ] `backend/app/core/auth.py` を Supabase JWT 検証に更新
- [ ] `backend/alembic/versions/0004_add_users_table.py` を作成
- [ ] マイグレーション実行: `alembic upgrade head`
- [ ] 環境変数設定（SUPABASE_*）

### Phase 2: Frontend修正 ⏳
- [ ] `frontend/src/lib/backendFetch.ts` を Supabase session 対応に更新
- [ ] `frontend/src/actions/student-registration.ts` の `getBackendAuthorizationHeader()` を修正
- [ ] `frontend/src/auth.ts` を確認（NextAuth → Supabase への完全移行）

### Phase 3: テスト実行
- [ ] ローカルテスト環境でエンドツーエンドテスト
- [ ] 本番 Supabase プロジェクトへのデプロイ

---

## 環境変数設定例（.env.local）

```bash
# Supabase
SUPABASE_ISSUER_URL=https://project-id.supabase.co
SUPABASE_JWKS_URL=https://project-id.supabase.co/.well-known/jwks.json
SUPABASE_JWT_SECRET=<取得方法: Supabase Dashboard > Settings > API > Secret Key>

# Brevo Email
BREVO_API_KEY=<your-key>
BREVO_SENDER_EMAIL=noreply@aoyama-digitart.jp
BREVO_SENDER_NAME=Digitart Technology Society

# OTP
OTP_LENGTH=6
OTP_EXPIRY_SECONDS=600
OTP_MAX_ATTEMPTS=3
```

---

## 参考: Discord ID 取得確認方法

Supabase Auth の設定が完了したら、以下で Discord ID を確認できます：

```bash
# Supabase CLI を使用
supabase auth users --project-ref <PROJECT_ID>

# または Supabase Dashboard:
# Authentication > Users > 特定ユーザーを選択 > Metadata タブで確認
```

---

## 次のステップ

1. Backend の JWT 検証ロジックを更新
2. `users` テーブル作成マイグレーション
3. Frontend の Supabase session 対応
4. 全テストケース再実行
5. 本番環境へのデプロイ
