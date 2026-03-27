"""役割: PostgreSQLへの永続化処理"""

from __future__ import annotations

import os
import sys
from typing import Any

import psycopg2


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres")


def _connect():
    return psycopg2.connect(DATABASE_URL)


def init_db() -> None:
    """初期テーブルを作成する。DBに接続できない場合は警告を出して終了しない。"""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS role_categories (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        display_order INTEGER DEFAULT 0,
                        is_collapsed BOOLEAN DEFAULT FALSE,
                        permissions BIGINT DEFAULT 0
                    );
                    """
                )
                # Migration: add permissions column if it was created without it
                cur.execute(
                    """
                    ALTER TABLE role_categories ADD COLUMN IF NOT EXISTS permissions BIGINT DEFAULT 0;
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS role_manifests (
                        role_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        color TEXT DEFAULT '#000000',
                        hoist BOOLEAN DEFAULT FALSE,
                        mentionable BOOLEAN DEFAULT FALSE,
                        permissions BIGINT DEFAULT 0,
                        position INTEGER NOT NULL,
                        category_id TEXT REFERENCES role_categories(id) ON DELETE SET NULL,
                        is_managed_by_app BOOLEAN DEFAULT TRUE,
                        is_our_bot BOOLEAN DEFAULT FALSE,
                        updated_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )

                # アプリユーザー RBAC（Supabase auth UUID をキーとして使用）
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        user_id TEXT UNIQUE NOT NULL,
                        discord_id TEXT UNIQUE,
                        app_role TEXT NOT NULL DEFAULT 'none'
                            CHECK (app_role IN ('member', 'admin', 'obog', 'pre_member', 'none')),
                        created_at TIMESTAMPTZ DEFAULT now(),
                        updated_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )

                # 入会費支払い済みリスト（adminが管理、discord_idで照合）
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS paid_invitations ( 
                        id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        discord_id TEXT UNIQUE NOT NULL,
                        note TEXT,
                        expires_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )



                # member / admin / pre_member リスト（Discord IDベース）
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS member_list (
                        id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        discord_id TEXT UNIQUE NOT NULL,
                        user_id TEXT,
                        assigned_by TEXT,
                        assigned_at TIMESTAMPTZ DEFAULT now(),
                        created_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_list (
                        id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        discord_id TEXT UNIQUE NOT NULL,
                        user_id TEXT,
                        assigned_by TEXT,
                        assigned_at TIMESTAMPTZ DEFAULT now(),
                        created_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pre_member_list (
                        id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        discord_id TEXT UNIQUE NOT NULL,
                        user_id TEXT,
                        assigned_by TEXT,
                        assigned_at TIMESTAMPTZ DEFAULT now(),
                        created_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )
                conn.commit()
    except Exception as e:
        # If DB is unreachable during development, log and continue without exiting
        # This allows the backend to start in degraded mode for local frontend debugging.
        print(f"WARNING: init_db failed: {e}", file=sys.stderr)
        return

def fetch_manifest() -> dict[str, list[dict[str, Any]]]:
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, name, display_order, is_collapsed, COALESCE(permissions, 0)
				FROM role_categories
				ORDER BY display_order ASC, name ASC
				"""
			)
			categories = [
				{
					"id": row[0],
					"name": row[1],
					"display_order": row[2],
					"is_collapsed": row[3],
					"permissions": int(row[4]),
				}
				for row in cur.fetchall()
			]

			cur.execute(
				"""
				SELECT role_id, name, color, hoist, mentionable, permissions, position, category_id, is_our_bot
				FROM role_manifests
				ORDER BY position DESC, name ASC
				"""
			)
			roles = [
				{
					"role_id": row[0],
					"name": row[1],
					"color": row[2],
					"hoist": row[3],
					"mentionable": row[4],
					"permissions": int(row[5]),
					"position": row[6],
					"category_id": row[7],
					"is_our_bot": bool(row[8]),
				}
				for row in cur.fetchall()
			]
	return {"categories": categories, "roles": roles}


def save_manifest(categories: list[dict[str, Any]], roles: list[dict[str, Any]]) -> None:
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("DELETE FROM role_manifests")
			cur.execute("DELETE FROM role_categories")

			for c in categories:
				cur.execute(
					"""
					INSERT INTO role_categories (id, name, display_order, is_collapsed, permissions)
					VALUES (%s, %s, %s, %s, %s)
					""",
					(
						c["id"],
						c["name"],
						c.get("display_order", 0),
						c.get("is_collapsed", False),
						int(c.get("permissions", 0)),
					),
				)

			for r in roles:
				cur.execute(
					"""
					INSERT INTO role_manifests
					(role_id, name, color, hoist, mentionable, permissions, position, category_id, is_our_bot)
					VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
					""",
					(
						r["role_id"],
						r["name"],
						r.get("color", "#000000"),
						r.get("hoist", False),
						r.get("mentionable", False),
						int(r.get("permissions", 0)),
						r["position"],
						r.get("category_id"),
						r.get("is_our_bot", False),
					),
				)


def replace_roles_from_discord(roles: list[dict[str, Any]]) -> int:
	with _connect() as conn:
		with conn.cursor() as cur:
			existing_ids = tuple(role["role_id"] for role in roles)
			if existing_ids:
				cur.execute("DELETE FROM role_manifests WHERE role_id NOT IN %s", (existing_ids,))
			else:
				cur.execute("DELETE FROM role_manifests")

			for role in roles:
				cur.execute(
					"""
					INSERT INTO role_manifests
					(role_id, name, color, hoist, mentionable, permissions, position, is_our_bot)
					VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
					ON CONFLICT (role_id) DO UPDATE SET
						name = EXCLUDED.name,
						color = EXCLUDED.color,
						hoist = EXCLUDED.hoist,
						mentionable = EXCLUDED.mentionable,
						permissions = EXCLUDED.permissions,
						position = EXCLUDED.position,
						is_our_bot = EXCLUDED.is_our_bot
					""",
					(
						role["role_id"],
						role["name"],
						role["color"],
						role["hoist"],
						role["mentionable"],
						role["permissions"],
						role["position"],
						role.get("is_our_bot", False),
					),
				)
	return len(roles)


def update_role_id(old_id: str, new_id: str) -> None:
	"""PushでDiscord側に作成されたロールの、DB上の仮IDを正規のDiscord IDに更新する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("UPDATE role_manifests SET role_id = %s WHERE role_id = %s", (new_id, old_id))


def sync_member_lists(
	member_role_ids: list[str],
	obog_role_ids: list[str],
	admin_role_ids: list[str],
	pre_member_role_id: str | None,
	members: dict[str, list[dict[str, Any]]]
) -> dict[str, int]:
	"""
	Discord ロール情報から member_list / admin_list / pre_member_list を同期。
	
	Parameters:
	- member_role_ids: member ロール ID のリスト（member または OBOG ロール）
	- obog_role_ids: OBOG ロール ID のリスト
	- admin_role_ids: admin ロール ID のリスト
	- pre_member_role_id: pre-member ロール ID（持っている場合）
	- members: role_id -> [members] のマッピング（fetch_guild_members_with_role から取得）
	
	Returns:
	- {'member_list': count, 'admin_list': count, 'pre_member_list': count}
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			# member_list の同期（member または OBOG ロール）
			member_discord_ids = set()
			for role_id in member_role_ids + obog_role_ids:
				for member in members.get(role_id, []):
					member_discord_ids.add(member["user_id"])
			
			cur.execute("DELETE FROM member_list")
			member_count = 0
			for discord_id in member_discord_ids:
				cur.execute(
					"""
					INSERT INTO member_list (discord_id)
					VALUES (%s)
					ON CONFLICT (discord_id) DO NOTHING
					""",
					(discord_id,)
				)
				member_count += 1
			
			# admin_list の同期
			admin_discord_ids = set()
			for role_id in admin_role_ids:
				for member in members.get(role_id, []):
					admin_discord_ids.add(member["user_id"])
			
			cur.execute("DELETE FROM admin_list")
			admin_count = 0
			for discord_id in admin_discord_ids:
				cur.execute(
					"""
					INSERT INTO admin_list (discord_id)
					VALUES (%s)
					ON CONFLICT (discord_id) DO NOTHING
					""",
					(discord_id,)
				)
				admin_count += 1
			
			# pre_member_list の同期
			pre_member_count = 0
			if pre_member_role_id:
				pre_member_discord_ids = set()
				for member in members.get(pre_member_role_id, []):
					pre_member_discord_ids.add(member["user_id"])
				
				cur.execute("DELETE FROM pre_member_list")
				for discord_id in pre_member_discord_ids:
					cur.execute(
						"""
						INSERT INTO pre_member_list (discord_id)
						VALUES (%s)
						ON CONFLICT (discord_id) DO NOTHING
						""",
						(discord_id,)
					)
					pre_member_count += 1
			
			conn.commit()
			
			return {
				"member_list": member_count,
				"admin_list": admin_count,
				"pre_member_list": pre_member_count
			}


def get_member_lists() -> dict[str, list[dict[str, Any]]]:
	"""member_list, admin_list, pre_member_list を取得."""
	with _connect() as conn:
		with conn.cursor() as cur:
			# member_list
			cur.execute(
				"SELECT discord_id, user_id, assigned_at FROM member_list ORDER BY assigned_at DESC"
			)
			members = [
				{"discord_id": row[0], "user_id": row[1], "assigned_at": row[2].isoformat() if row[2] else None}
				for row in cur.fetchall()
			]
			
			# admin_list
			cur.execute(
				"SELECT discord_id, user_id, assigned_at FROM admin_list ORDER BY assigned_at DESC"
			)
			admins = [
				{"discord_id": row[0], "user_id": row[1], "assigned_at": row[2].isoformat() if row[2] else None}
				for row in cur.fetchall()
			]
			
			# pre_member_list
			cur.execute(
				"SELECT discord_id, user_id, assigned_at FROM pre_member_list ORDER BY assigned_at DESC"
			)
			pre_members = [
				{"discord_id": row[0], "user_id": row[1], "assigned_at": row[2].isoformat() if row[2] else None}
				for row in cur.fetchall()
			]
	
	return {
		"member_list": members,
		"admin_list": admins,
		"pre_member_list": pre_members,
	}


def register_pre_member(discord_id: str) -> dict[str, Any]:
	"""新しい参加者を pre_member_list に登録.
	
	Args:
		discord_id: Discord user ID
		
	Returns:
		{"discord_id": "...", "created": True/False}
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO pre_member_list (discord_id)
				VALUES (%s)
				ON CONFLICT (discord_id) DO NOTHING
				RETURNING id, created_at, assigned_at
				""",
				(discord_id,)
			)
			result = cur.fetchone()
			conn.commit()
			
			if result is None:
				return {"discord_id": discord_id, "created": False, "message": "Already in pre_member_list"}
			
			return {
				"discord_id": discord_id,
				"created": True,
				"assigned_at": result[2].isoformat() if result[2] else result[1].isoformat() if result[1] else None
			}


def get_pre_member_list_with_users(search: str | None = None) -> list[dict[str, Any]]:
	"""Pre-member list をユーザー情報とともに取得。
	
	Args:
		search: user_id または discord_id で検索（部分一致）
		
	Returns:
		[{"discord_id": "...", "user_id": "...", "assigned_at": "..."}, ...]
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			if search:
				# user_id または discord_id で部分検索
				cur.execute(
					"""
					SELECT p.discord_id, p.user_id, p.assigned_at, u.user_id as supabase_user_id
					FROM pre_member_list p
					LEFT JOIN users u ON p.discord_id = u.discord_id
					WHERE p.discord_id ILIKE %s OR p.user_id ILIKE %s OR u.user_id ILIKE %s
					ORDER BY p.assigned_at DESC
					""",
					(f"%{search}%", f"%{search}%", f"%{search}%")
				)
			else:
				cur.execute(
					"""
					SELECT p.discord_id, p.user_id, p.assigned_at, u.user_id as supabase_user_id
					FROM pre_member_list p
					LEFT JOIN users u ON p.discord_id = u.discord_id
					ORDER BY p.assigned_at DESC
					"""
				)
			
			results = []
			for row in cur.fetchall():
				results.append({
					"discord_id": row[0],
					"user_id": row[1],
					"assigned_at": row[2].isoformat() if row[2] else None,
					"supabase_user_id": row[3],
				})
			return results


def add_to_member_list(
	discord_id: str,
	assigned_by: str,
	note: str | None = None,
) -> dict[str, Any]:
	"""Pre-member を member_list に追加。
	同時に paid_invitations にも登録する。
	
	Args:
		discord_id: Discord user ID
		assigned_by: admin's discord_id or user_id
		note: Optional note for paid_invitations
		
	Returns:
		{"discord_id": "...", "added_to_member_list": True/False}
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			# Check if already in member_list
			cur.execute(
				"SELECT discord_id FROM member_list WHERE discord_id = %s",
				(discord_id,)
			)
			if cur.fetchone() is not None:
				return {"discord_id": discord_id, "added_to_member_list": False, "message": "Already in member_list"}
			
			# Add to member_list
			cur.execute(
				"""
				INSERT INTO member_list (discord_id, assigned_by)
				VALUES (%s, %s)
				RETURNING id, created_at
				""",
				(discord_id, assigned_by)
			)
			result = cur.fetchone()
			
			# Also register in paid_invitations if not already there
			cur.execute(
				"SELECT discord_id FROM paid_invitations WHERE discord_id = %s",
				(discord_id,)
			)
			if cur.fetchone() is None:
				cur.execute(
					"""
					INSERT INTO paid_invitations (discord_id, note)
					VALUES (%s, %s)
					""",
					(discord_id, note)
				)
			
			# Remove from pre_member_list if present
			cur.execute(
				"DELETE FROM pre_member_list WHERE discord_id = %s",
				(discord_id,)
			)
			
			conn.commit()
			
			return {
				"discord_id": discord_id,
				"added_to_member_list": True,
				"created_at": result[1].isoformat() if result[1] else None
			}


def register_paid_invitation(
	discord_id: str,
	note: str | None = None,
) -> dict[str, Any]:
	"""入会費支払い済みユーザーを paid_invitations に登録。
	
	Args:
		discord_id: Discord user ID
		note: Payment method or note
		
	Returns:
		{"discord_id": "...", "created": True/False}
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO paid_invitations (discord_id, note)
				VALUES (%s, %s)
				ON CONFLICT (discord_id) DO UPDATE SET note = EXCLUDED.note, created_at = now()
				RETURNING id, created_at
				""",
				(discord_id, note)
			)
			result = cur.fetchone()
			conn.commit()
			
			return {
				"discord_id": discord_id,
				"created": True,
				"created_at": result[1].isoformat() if result[1] else None
			}


# ==================== OTP・Join Requests 関連 ====================

def create_join_request(
	email: str,
	name: str,
	form_type: str,
	metadata: dict | None = None,
) -> dict[str, Any]:
	"""Create a join request entry

	Args:
		email: applicant email
		name: applicant name
		form_type: "prospective-student" or "contact"
		metadata: form-specific data (year, etc.)

	Returns:
		{"id": "...", "email": "...", "status": "pending", ...}

	Raises:
		ValueError: if email already exists
	"""
	from uuid import uuid4
	import json

	request_id = str(uuid4())
	with _connect() as conn:
		with conn.cursor() as cur:
			try:
				# まず既存レコードを確認する
				cur.execute(
					"SELECT id, status, name, form_type, metadata, created_at, updated_at FROM join_requests WHERE email = %s",
					(email,)
				)
				existing = cur.fetchone()
				if existing:
					existing_id, existing_status = existing[0], existing[1]
					# pending/failed の場合は既存レコードを更新して再利用する
					if existing_status in ("pending", "failed"):
						cur.execute(
							"""
							UPDATE join_requests
							SET name = %s, form_type = %s, metadata = %s, status = 'pending', updated_at = now()
							WHERE id = %s
							RETURNING id, email, name, form_type, status, metadata, created_at, updated_at
							""",
							(name, form_type, json.dumps(metadata or {}), existing_id),
						)
						row = cur.fetchone()
						if row is None:
							raise RuntimeError("Failed to update existing join request")
						conn.commit()
						return {
							"id": row[0],
							"email": row[1],
							"name": row[2],
							"form_type": row[3],
							"status": row[4],
							"metadata": row[5],
							"created_at": row[6].isoformat() if row[6] else None,
							"updated_at": row[7].isoformat() if row[7] else None,
						}
					# verified/completed 等は既存登録として扱いエラーを返す
					raise ValueError(f"Email {email} already registered")

				# 存在しなければ新規挿入
				cur.execute(
					"""
					INSERT INTO join_requests (id, email, name, form_type, metadata, status)
					VALUES (%s, %s, %s, %s, %s, 'pending')
					RETURNING id, email, name, form_type, status, metadata, created_at, updated_at
					""",
					(request_id, email, name, form_type, json.dumps(metadata or {})),
				)
				row = cur.fetchone()
				if row is None:
					raise RuntimeError("Failed to create join request")
				conn.commit()
				return {
					"id": row[0],
					"email": row[1],
					"name": row[2],
					"form_type": row[3],
					"status": row[4],
					"metadata": row[5],
					"created_at": row[6].isoformat() if row[6] else None,
					"updated_at": row[7].isoformat() if row[7] else None,
				}
			except Exception as e:
				conn.rollback()
				if "unique" in str(e).lower():
					raise ValueError(f"Email {email} already registered") from e
				raise


def create_otp_code(
	join_request_id: str,
	code_hash: str,
	expires_in_minutes: int = 15,
) -> dict[str, Any]:
	"""Create an OTP code entry

	Args:
		join_request_id: FK to join_requests.id
		code_hash: bcrypt hash of OTP
		expires_in_minutes: OTP validity (default 15)

	Returns:
		{"id": "...", "join_request_id": "...", "expires_at": ...}
	"""
	from uuid import uuid4
	from datetime import datetime, timedelta, timezone

	otp_id = str(uuid4())
	# Use timezone-aware UTC datetime for expires_at
	expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)

	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO otp_codes (id, join_request_id, code_hash, expires_at)
				VALUES (%s, %s, %s, %s)
				RETURNING id, join_request_id, expires_at, created_at
				""",
				(otp_id, join_request_id, code_hash, expires_at),
			)
			row = cur.fetchone()
			conn.commit()
			return {
				"id": row[0],
				"join_request_id": row[1],
				"expires_at": row[2].isoformat() if row[2] else None,
				"created_at": row[3].isoformat() if row[3] else None,
			}


def verify_otp(join_request_id: str, code_plain: str) -> bool:
	"""Verify OTP code against stored hash

	Args:
		join_request_id: join request ID
		code_plain: plaintext 6-digit code entered by user

	Returns:
		True if valid and not expired/max attempts exceeded

	Raises:
		ValueError: if expired or max attempts exceeded
	"""
	from app.utils.otp import verify_otp_code
	from datetime import datetime, timezone

	with _connect() as conn:
		with conn.cursor() as cur:
			# Get latest unverified OTP for this join request
			cur.execute(
				"""
				SELECT id, code_hash, expires_at, attempt_count, verified_at
				FROM otp_codes
				WHERE join_request_id = %s AND verified_at IS NULL
				ORDER BY created_at DESC
				LIMIT 1
				""",
				(join_request_id,),
			)
			row = cur.fetchone()
			if row is None:
				raise ValueError("No active OTP found")

			otp_id, code_hash, expires_at, attempt_count, verified_at = row

			# Normalize expires_at to timezone-aware UTC if needed, then check expiry
			if getattr(expires_at, 'tzinfo', None) is None:
				expires_at = expires_at.replace(tzinfo=timezone.utc)

			if datetime.now(timezone.utc) > expires_at:
				raise ValueError("OTP has expired")

			# Check max attempts
			if attempt_count >= 5:
				raise ValueError("Maximum OTP attempts exceeded")

			# Check code
			if not verify_otp_code(code_plain, code_hash):
				# Increment attempt count
				cur.execute(
					"""
					UPDATE otp_codes SET attempt_count = attempt_count + 1
					WHERE id = %s
					""",
					(otp_id,),
				)
				conn.commit()
				raise ValueError("Invalid OTP code")

			# Mark as verified
			cur.execute(
				"""
				UPDATE otp_codes SET verified_at = now()
				WHERE id = %s
				RETURNING id
				""",
				(otp_id,),
			)
			conn.commit()
			return True


def get_join_request(join_request_id: str) -> dict[str, Any] | None:
	"""Get join request by ID"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, email, name, form_type, status, metadata, created_at, updated_at
				FROM join_requests
				WHERE id = %s
				""",
				(join_request_id,),
			)
			row = cur.fetchone()
			if row is None:
				return None
			return {
				"id": row[0],
				"email": row[1],
				"name": row[2],
				"form_type": row[3],
				"status": row[4],
				"metadata": row[5],
				"created_at": row[6].isoformat() if row[6] else None,
				"updated_at": row[7].isoformat() if row[7] else None,
			}
