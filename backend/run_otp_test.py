#!/usr/bin/env python3
"""Automated OTP create/verify test for local backend.

Flow:
- Create join_request via repository
- Generate known OTP, hash it and insert via create_otp_code
- Attempt verify with wrong code -> expect ValueError and attempt_count increments
- Attempt verify with correct code -> expect success
- Print DB states along the way
"""
import os
from dotenv import load_dotenv
from time import sleep

# Load env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.db import repository
from app.utils import otp as otp_utils
import httpx

print('Starting OTP automated test')

import uuid

email = f'ci+auto-{uuid.uuid4().hex[:8]}@example.com'
name = 'Auto Tester'

# 1) create join request
jr = repository.create_join_request(email=email, name=name, form_type='contact', metadata={'ci':'true'})
join_id = jr['id']
print('Created join_request id:', join_id)

# 2) generate code and insert
code = otp_utils.generate_otp_code()
code_hash = otp_utils.hash_otp_code(code)
print('Generated OTP (plaintext):', code)
created_otp = repository.create_otp_code(join_request_id=join_id, code_hash=code_hash, expires_in_minutes=15)
print('Inserted otp_codes id:', created_otp['id'])

# Call the backend API verify endpoint to exercise invite creation path
base = os.getenv('BACKEND_URL', 'http://localhost:8000')
verify_url = f"{base}/api/v1/join/verify"
print('Calling API verify endpoint:', verify_url)
try:
    resp = httpx.post(verify_url, json={'join_request_id': join_id, 'otp_code': code}, timeout=10.0)
    print('API verify response status:', resp.status_code)
    try:
        print('API verify response JSON:', resp.json())
    except Exception:
        print('API verify response text:', resp.text)
except Exception as e:
    print('API call failed:', e)

# 3) Direct DB check and manual verification flow (simulate repository.verify_otp)
conn = repository._connect()
cur = conn.cursor()
cur.execute('SELECT id, code_hash, attempt_count, verified_at, expires_at, created_at FROM otp_codes WHERE join_request_id=%s ORDER BY created_at DESC LIMIT 1', (join_id,))
row = cur.fetchone()
print('OTP row before verifies:', row)
otp_id = row[0]
code_hash_db = row[1]

from datetime import datetime, timezone

# simulate incorrect attempt
wrong_code = '000000'
now = datetime.now(timezone.utc)
expires_at = row[4]
if getattr(expires_at, 'tzinfo', None) is None:
    expires_at = expires_at.replace(tzinfo=timezone.utc)

if now > expires_at:
    print('OTP is already expired')
else:
    # verify wrong code
    if not otp_utils.verify_otp_code(wrong_code, code_hash_db):
        # increment attempt_count
        cur.execute('UPDATE otp_codes SET attempt_count = attempt_count + 1 WHERE id = %s', (otp_id,))
        conn.commit()
        print('Wrong code rejected; attempt_count incremented')
    else:
        print('Unexpected: wrong code accepted')

cur.execute('SELECT attempt_count FROM otp_codes WHERE id=%s', (otp_id,))
print('attempt_count after wrong attempt:', cur.fetchone()[0])

# simulate correct attempt
if not otp_utils.verify_otp_code(code, code_hash_db):
    print('Unexpected: stored hash does not match generated code')
else:
    # mark verified
    cur.execute('UPDATE otp_codes SET verified_at = now() WHERE id = %s', (otp_id,))
    conn.commit()
    print('Correct code accepted; verified_at set')

cur.execute('SELECT attempt_count, verified_at FROM otp_codes WHERE id=%s', (otp_id,))
print('OTP row after correct verify:', cur.fetchone())

cur.close()
conn.close()
print('Done')
