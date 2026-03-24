# サンプルコード集

このファイルには Frontend（Server Action）と Discord Bot（discord.py）の最小サンプルを示す。動作させるには環境変数や依存のインストールが必要。

## Frontend: Server Action（TypeScript, Next.js）

```ts
// app/actions/roleActions.ts
"use server"

export async function saveManifestAndTriggerSync(manifest: any) {
  const res = await fetch(process.env.BACKEND_URL + "/api/v1/manifest", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(manifest),
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to save manifest");
  // Optional: call sync endpoint
  await fetch(process.env.BACKEND_URL + "/api/v1/sync", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "sync_roles" }) });
}
```

## Frontend: React コンポーネント（呼び出し例）

```tsx
// app/(admin)/roles/page.tsx
import { saveManifestAndTriggerSync } from "../actions/roleActions";

export default function Page() {
  async function onSave(manifest: any) {
    await saveManifestAndTriggerSync(manifest);
    // revalidate or show toast
  }
  return (
    <form action={onSave}>
      {/* DnD UI ここに実装 */}
    </form>
  );
}
```

## Discord Bot: サンプル（discord.py + FastAPI 受信用）

```py
# discord-bot/main.py
import os
import asyncio
import httpx
import discord
from discord.ext import commands
from fastapi import FastAPI, Request, HTTPException
import uvicorn

BOT_TOKEN = os.getenv("DISCORD_TOKEN")
SHARED_SECRET = os.getenv("SHARED_SECRET")
BACKEND_URL = os.getenv("BACKEND_URL")  # e.g. http://backend:8000

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
app = FastAPI()

@app.post('/internal/sync')
async def internal_sync(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {SHARED_SECRET}":
        raise HTTPException(status_code=401)
    data = await request.json()
    # enqueue task into bot loop
    asyncio.create_task(run_sync())
    return {"status": "enqueued"}

async def run_sync():
    # 1) Backend から manifest を取得
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BACKEND_URL}/api/v1/manifest")
        manifest = r.json()
    # 2) guild と roles を取得して差分を計算
    # （実運用では target guild id を明示的に指定する）
    guild = bot.guilds[0]
    desired = {r['role_id']: r for r in manifest['roles']}
    actual = {str(role.id): role for role in guild.roles}

    # 3) 作成/更新/削除/並び替えの最小差分を実行
    # ここでは更新（名前・色）を例示
    for rid, d in desired.items():
        if rid in actual:
            role = actual[rid]
            # 比較して更新
            changes = {}
            if role.name != d['name']:
                changes['name'] = d['name']
            # color handling omitted for brevity
            if changes:
                try:
                    await role.edit(**changes, reason='Sync from app')
                except Exception as e:
                    print('Failed to edit role', role.id, e)
        else:
            # create role
            try:
                await guild.create_role(name=d['name'], hoist=d.get('hoist', False), mentionable=d.get('mentionable', False))
            except Exception as e:
                print('Failed to create role', d['name'], e)

    # 4) 並び替え（position）を一括で適用するには Discord API の制約に注意

@bot.event
async def on_ready():
    print('Bot ready', bot.user)

async def start():
    config = uvicorn.Config(app, host='0.0.0.0', port=8000, log_level='info')
    server = uvicorn.Server(config)
    await asyncio.gather(bot.start(BOT_TOKEN), server.serve())

if __name__ == '__main__':
    asyncio.run(start())
```

### Requirements (discord-bot/requirements.txt)
```
discord.py>=2.3
fastapi>=0.95
uvicorn[standard]
httpx
```
