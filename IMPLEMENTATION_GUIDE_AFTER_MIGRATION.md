# DB 移行後のコード実装ガイド

**作成日**: 2026年4月14日  
**対象**: user_memberships 統合後のコード修正

---

## 📝 コード修正ロードマップ

### **フェーズ A: user_repository.py の app_role 計算ロジック追加**

#### 修正内容

現在: `users.app_role` を SELECT して使用

```python
# 現在の実装（削除予定）
def get_user_app_role(user_id: str) -> str:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT app_role FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else 'none'
```

修正後: `user_memberships` から計算

```python
# 新しい実装（推奨）
def get_user_app_role(user_id: str) -> str:
    """
    user_memberships から membership_type を取得し、app_role に変換。
    優先順位: admin > member > pre_member > obog > none
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            # users から discord_id を取得
            cur.execute("SELECT discord_id FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                return 'none'
            
            discord_id = row[0]
            if not discord_id:
                return 'none'
            
            # user_memberships から membership_type を取得
            cur.execute(
                "SELECT membership_type FROM user_memberships WHERE discord_id = %s ORDER BY CASE membership_type WHEN 'admin' THEN 1 WHEN 'member' THEN 2 WHEN 'pre_member' THEN 3 WHEN 'obog' THEN 4 END LIMIT 1",
                (discord_id,)
            )
            row = cur.fetchone()
            return row[0] if row else 'none'
```

**または SQL VIEW で簡潔に**:

```sql
-- SQL VIEW を作成（推奨：パフォーマンスが良い）
CREATE VIEW v_users_with_app_role AS
SELECT 
    u.id,
    u.user_id,
    u.discord_id,
    COALESCE(
        (SELECT membership_type FROM user_memberships 
         WHERE discord_id = u.discord_id 
         ORDER BY CASE membership_type 
           WHEN 'admin' THEN 1
           WHEN 'member' THEN 2
           WHEN 'pre_member' THEN 3
           WHEN 'obog' THEN 4
         END LIMIT 1),
        'none'
    ) as app_role,
    u.created_at,
    u.updated_at
FROM users u;
```

**Python から VIEW を参照**:

```python
def get_user_app_role(user_id: str) -> str:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT app_role FROM v_users_with_app_role WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else 'none'
```

#### 影響を受けるファイル

- `backend/app/db/user_repository.py` - `get_user_app_role()`, `find_user_by_sub()` 内の app_role 使用
- `backend/app/core/auth.py` - ユーザー認証時の app_role 取得

---

### **フェーズ B: repository.py の sync_member_lists() 修正**

#### 現在の実装

```python
def sync_member_lists(
    member_role_ids: list[str],
    obog_role_ids: list[str],
    admin_role_ids: list[str],
    pre_member_role_id: str | None,
    members: dict[str, list[dict[str, Any]]]
) -> dict[str, int]:
    """
    Discord ロール情報から member_list / admin_list / pre_member_list を同期。
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            # member_list の同期（全置換）
            cur.execute("DELETE FROM member_list")
            member_count = 0
            for discord_id in member_discord_ids:
                cur.execute(
                    "INSERT INTO member_list (discord_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (discord_id,)
                )
                member_count += 1
            
            # admin_list, pre_member_list も同様...
            conn.commit()
            return {'member_list': member_count, ...}
```

#### 修正後の実装

```python
def sync_member_lists(
    member_role_ids: list[str],
    obog_role_ids: list[str],
    admin_role_ids: list[str],
    pre_member_role_id: str | None,
    members: dict[str, list[dict[str, Any]]]
) -> dict[str, int]:
    """
    Discord ロール情報から user_memberships を同期（統合テーブル）。
    
    処理:
    1. member role → user_memberships (membership_type='member') に INSERT
    2. admin role → user_memberships (membership_type='admin') に INSERT
    3. pre_member role → user_memberships (membership_type='pre_member') に INSERT
    4. obog role → user_memberships (membership_type='obog') に INSERT
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            counts = {}
            
            # 既存データをクリア（全置換方式）
            cur.execute("DELETE FROM user_memberships")
            
            # 1. Member ロール + OB-OG ロール → membership_type = 'member'
            member_discord_ids = set()
            for role_id in member_role_ids + obog_role_ids:
                for member in members.get(role_id, []):
                    member_discord_ids.add(member["user_id"])
            
            for discord_id in member_discord_ids:
                cur.execute(
                    """
                    INSERT INTO user_memberships 
                    (discord_id, membership_type, assigned_at, created_at)
                    VALUES (%s, 'member', now(), now())
                    ON CONFLICT (discord_id, membership_type) DO NOTHING
                    """,
                    (discord_id,)
                )
            counts['member'] = len(member_discord_ids)
            
            # 2. Admin ロール → membership_type = 'admin'
            admin_discord_ids = set()
            for role_id in admin_role_ids:
                for member in members.get(role_id, []):
                    admin_discord_ids.add(member["user_id"])
            
            for discord_id in admin_discord_ids:
                cur.execute(
                    """
                    INSERT INTO user_memberships 
                    (discord_id, membership_type, assigned_at, created_at)
                    VALUES (%s, 'admin', now(), now())
                    ON CONFLICT (discord_id, membership_type) DO NOTHING
                    """,
                    (discord_id,)
                )
            counts['admin'] = len(admin_discord_ids)
            
            # 3. Pre-member ロール → membership_type = 'pre_member'
            pre_member_discord_ids = set()
            if pre_member_role_id:
                for member in members.get(pre_member_role_id, []):
                    pre_member_discord_ids.add(member["user_id"])
            
            for discord_id in pre_member_discord_ids:
                cur.execute(
                    """
                    INSERT INTO user_memberships 
                    (discord_id, membership_type, assigned_at, created_at)
                    VALUES (%s, 'pre_member', now(), now())
                    ON CONFLICT (discord_id, membership_type) DO NOTHING
                    """,
                    (discord_id,)
                )
            counts['pre_member'] = len(pre_member_discord_ids)
            
            conn.commit()
            return counts
```

#### 影響を受けるファイル

- `backend/app/db/repository.py` - `sync_member_lists()` 関数
- `backend/app/api/v1/roles.py` - `refresh_roles_from_discord()` エンドポイント（呼び出し側）

---

### **フェーズ C: repository.py の get_member_lists() 修正**

#### 現在の実装

```python
def get_member_lists() -> dict[str, list[dict[str, Any]]]:
    """member_list, admin_list, pre_member_list を取得."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT discord_id, user_id, assigned_at FROM member_list ...")
            members = [...]
            
            cur.execute("SELECT discord_id, user_id, assigned_at FROM admin_list ...")
            admins = [...]
            
            # ...
            return {'member_list': members, 'admin_list': admins, ...}
```

#### 修正後の実装

```python
def get_member_lists() -> dict[str, list[dict[str, Any]]]:
    """user_memberships から membership_type 別にリストを取得."""
    with _connect() as conn:
        with conn.cursor() as cur:
            result = {}
            
            # membership_type ごとにクエリ
            for mem_type in ['member', 'admin', 'pre_member', 'obog']:
                cur.execute(
                    """
                    SELECT discord_id, assigned_by, assigned_at
                    FROM user_memberships
                    WHERE membership_type = %s
                    ORDER BY assigned_at DESC
                    """,
                    (mem_type,)
                )
                result[f'{mem_type}_list'] = [
                    {
                        'discord_id': row[0],
                        'assigned_by': row[1],
                        'assigned_at': row[2].isoformat() if row[2] else None
                    }
                    for row in cur.fetchall()
                ]
            
            return result  # {'member_list': [...], 'admin_list': [...], ...}
```

#### 影響を受けるファイル

- `backend/app/db/repository.py` - `get_member_lists()` 関数
- `backend/app/api/v1/members.py` - 呼び出し側

---

### **フェーズ D: reconcile.py の修正**

#### 現在の実装

```python
async def run_reconcile() -> dict:
    """Discord Bot reconciliation."""
    # pre_member_list から guild メンバーを取得
    pre_members = db_get_pre_member_list()  # SELECT FROM pre_member_list
    
    # 各ユーザーから pre-member ロールを削除
    for discord_id in pre_members:
        await _remove_role(client, discord_id, PRE_MEMBER_ROLE_ID)
```

#### 修正後の実装

```python
async def run_reconcile() -> dict:
    """Discord Bot reconciliation."""
    # user_memberships から pre_member を取得
    pre_members = db_get_pre_member_list_v2()  # SELECT FROM user_memberships WHERE membership_type='pre_member'
    
    # 各ユーザーから pre-member ロールを削除
    for discord_id in pre_members:
        await _remove_role(client, discord_id, PRE_MEMBER_ROLE_ID)
```

**Repository 関数:**

```python
# discord-bot/app/services/db_helper.py または repository 経由
def get_pre_member_list() -> list[str]:
    """user_memberships から pre_member の discord_id リストを取得."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT discord_id FROM user_memberships WHERE membership_type = 'pre_member'"
            )
            return [row[0] for row in cur.fetchall()]
```

#### 影響を受けるファイル

- `discord-bot/app/services/reconcile.py` - reconciliation ロジック
- `backend/app/db/repository.py` - helper 関数（discord-bot 側で参照）

---

### **フェーズ E: API エンドポイントの修正**

#### members.py - get_members エンドポイント

**現在:**

```python
@router.get("/members", response_model=dict)
async def get_members(_principal: dict = Depends(require_member)):
    members = fetch_member_lists()  # member_list, admin_list, pre_member_list
    return members
```

**修正後:**

```python
@router.get("/members", response_model=dict)
async def get_members(_principal: dict = Depends(require_member)):
    members = fetch_member_lists()  # user_memberships から membership_type 別
    return members  # {'member_list': [...], 'admin_list': [...], ...}
```

**変更点**: SQL クエリのみ、API signature 不変

---

#### members.py - add_to_member_list エンドポイント

**現在:**

```python
def add_to_member_list(discord_id: str) -> None:
    """pre_member_list から member_list に昇格."""
    with _connect() as conn:
        with conn.cursor() as cur:
            # pre_member_list から削除
            cur.execute("DELETE FROM pre_member_list WHERE discord_id = %s", (discord_id,))
            
            # member_list に追加
            cur.execute(
                "INSERT INTO member_list (discord_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (discord_id,)
            )
            conn.commit()
```

**修正後:**

```python
def add_to_member_list(discord_id: str) -> None:
    """user_memberships の membership_type を pre_member から member に変更."""
    with _connect() as conn:
        with conn.cursor() as cur:
            # pre_member を削除
            cur.execute(
                "DELETE FROM user_memberships WHERE discord_id = %s AND membership_type = 'pre_member'",
                (discord_id,)
            )
            
            # member を追加
            cur.execute(
                """
                INSERT INTO user_memberships (discord_id, membership_type, assigned_at, created_at)
                VALUES (%s, 'member', now(), now())
                ON CONFLICT (discord_id, membership_type) DO NOTHING
                """,
                (discord_id,)
            )
            conn.commit()
```

#### 影響を受けるファイル

- `backend/app/api/v1/members.py` - API エンドポイント
- `backend/app/db/repository.py` - helper 関数

---

### **フェーズ F: student.py の修正**

#### verify_otp エンドポイント

**現在:**

```python
@router.post("/otp/verify")
async def verify_otp(req: VerifyOTPRequest, principal: dict = Depends(get_current_principal)):
    # ... OTP 検証処理 ...
    
    # role_member_assignments を更新
    add_user_to_role(discord_id, MEMBER_ROLE_ID)
    remove_user_from_role(discord_id, PRE_MEMBER_ROLE_ID)
    
    return VerifyOTPResponse(verified=True)
```

**修正後:** （変更不要、既に実装済み）

- role_member_assignments は依然として使用
- user_memberships は role_member_assignments から sync_member_lists() で更新

---

### **フェーズ G: ユーティリティ関数の統合**

#### 新しい helper 関数

```python
# backend/app/db/repository.py に追加

def get_user_membership_type(discord_id: str) -> str:
    """user_memberships から membership_type を取得."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT membership_type FROM user_memberships 
                WHERE discord_id = %s
                ORDER BY CASE membership_type 
                  WHEN 'admin' THEN 1
                  WHEN 'member' THEN 2
                  WHEN 'pre_member' THEN 3
                  WHEN 'obog' THEN 4
                END LIMIT 1
                """,
                (discord_id,)
            )
            row = cur.fetchone()
            return row[0] if row else 'none'


def is_member(discord_id: str) -> bool:
    """user_memberships で member か確認."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM user_memberships WHERE discord_id = %s AND membership_type = 'member' LIMIT 1",
                (discord_id,)
            )
            return cur.fetchone() is not None


def is_admin(discord_id: str) -> bool:
    """user_memberships で admin か確認."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM user_memberships WHERE discord_id = %s AND membership_type = 'admin' LIMIT 1",
                (discord_id,)
            )
            return cur.fetchone() is not None


def is_pre_member(discord_id: str) -> bool:
    """user_memberships で pre_member か確認."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM user_memberships WHERE discord_id = %s AND membership_type = 'pre_member' LIMIT 1",
                (discord_id,)
            )
            return cur.fetchone() is not None
```

---

## 🎯 実装タイムライン

### **Week 1: 準備 & テスト**

- [ ] フェーズ A 実装: user_repository.py app_role 計算ロジック
- [ ] SQL VIEW v_users_with_app_role 作成・テスト
- [ ] ローカルで staging DB でマイグレーション dry-run

### **Week 2: 本体実装**

- [ ] フェーズ B 実装: sync_member_lists() 修正
- [ ] フェーズ C 実装: get_member_lists() 修正
- [ ] 新ユーティリティ関数追加
- [ ] Unit テスト追加

### **Week 3: 整合性テスト**

- [ ] フェーズ D 実装: reconcile.py 修正
- [ ] フェーズ E, F 実装: API エンドポイント修正
- [ ] Integration テスト（ローカル + staging）

### **Week 4: デプロイ準備**

- [ ] マイグレーション SQL スクリプト最終確認
- [ ] ロールバック手順確認
- [ ] 本番環境でのドライラン
- [ ] デプロイ実行

---

## 📋 修正ファイル一覧

| ファイル | 修正内容 | 難度 |
|---------|---------|------|
| `backend/app/db/user_repository.py` | app_role 計算ロジック | 🟡 中 |
| `backend/app/db/repository.py` | sync_member_lists(), get_member_lists(), 新ユーティリティ | 🟡 中 |
| `backend/app/core/auth.py` | app_role 取得ロジック（VIEW 使用） | ✅ 小 |
| `backend/app/api/v1/members.py` | 呼び出し元の修正 | ✅ 小 |
| `backend/app/api/v1/roles.py` | 呼び出し元の修正 | ✅ 小 |
| `discord-bot/app/services/reconcile.py` | pre_member 読込元の変更 | ✅ 小 |
| `backend/app/api/v1/student.py` | 変更不要（既に実装済み）| ✅ 不要 |

---

## ✅ テストチェックリスト

### Unit テスト

- [ ] `get_user_app_role()` で admin/member/pre_member/none を正しく返す
- [ ] `sync_member_lists()` で 93 members + admins + pre_members を正しく user_memberships に insert
- [ ] `is_member()`, `is_admin()`, `is_pre_member()` が正しく判定

### Integration テスト

- [ ] OTP verify 後に role_member_assignments + user_memberships が同期される
- [ ] reconcile 実行で pre_member ユーザーから pre-member role が削除される
- [ ] API /members, /members/sync が user_memberships をベースに動作

### 本番事前テスト

- [ ] staging DB でマイグレーション実行 → 整合性確認
- [ ] ローカルコピーで ロールバック動作確認
- [ ] パフォーマンス テスト（新 VIEW または クエリのスピード）

