from dotenv import load_dotenv
load_dotenv('/app/../.env')
from app.db import repository
import traceback

conn = repository._connect()
cur = conn.cursor()
cur.execute("SELECT id FROM join_requests ORDER BY created_at DESC LIMIT 1")
r = cur.fetchone()
cur.close(); conn.close()
join_id = r[0]
print('Latest join id:', join_id)

try:
    repository.verify_otp(join_request_id=join_id, code_plain='000000')
except Exception as e:
    traceback.print_exc()
    print('\nEXCEPTION TYPE:', type(e))
    print('EXCEPTION STR:', str(e))
