"""役割: Bot起動エントリ"""

from __future__ import annotations

import asyncio
import logging
import os

import discord
import httpx
import uvicorn
from discord.ext import commands, tasks
from fastapi import FastAPI

from app.web.internal_api import router as internal_router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
BOT_PORT = int(os.getenv("BOT_PORT", "8000"))
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")
PRE_MEMBER_ROLE_ID = os.getenv("PRE_MEMBER_ROLE_ID", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

app = FastAPI(title="AuthWebApp Discord Bot", version="0.1.0")
app.include_router(internal_router)


@bot.event
async def on_ready() -> None:
	logger.info("Discord bot ready: %s", bot.user)


@bot.event
async def on_member_join(member: discord.Member) -> None:
	"""Automatically assign pre-member role when a user joins the server."""
	if not DISCORD_GUILD_ID or not PRE_MEMBER_ROLE_ID:
		logger.warning("DISCORD_GUILD_ID or PRE_MEMBER_ROLE_ID is not configured")
		return
	
	# Only process members joining our configured guild
	if str(member.guild.id) != DISCORD_GUILD_ID:
		logger.info(f"Member {member.id} joined guild {member.guild.id}, not our guild {DISCORD_GUILD_ID}")
		return
	
	try:
		# Get the pre-member role
		role = member.guild.get_role(int(PRE_MEMBER_ROLE_ID))
		if not role:
			logger.error(f"Pre-member role {PRE_MEMBER_ROLE_ID} not found in guild {DISCORD_GUILD_ID}")
			return
		
		# Assign the role to the new member
		await member.add_roles(role)
		logger.info(f"Assigned pre-member role to {member} ({member.id})")
		
		# Register in pre_member_list via backend API
		await _register_pre_member(member.id)
		
	except Exception as e:
		logger.error(f"Failed to process member join for {member.id}: {e}")


async def _register_pre_member(discord_id: int) -> None:
	"""Register user in pre_member_list via backend API."""
	try:
		async with httpx.AsyncClient(timeout=5.0) as client:
			response = await client.post(
				f"{BACKEND_URL}/api/v1/members/pre_member/register",
				json={"discord_id": str(discord_id), "source": "P"},
				headers={"Authorization": f"Bearer {SHARED_SECRET}"},
			)
			if response.status_code == 200:
				logger.info(f"Registered {discord_id} in pre_member_list")
			else:
				logger.error(f"Failed to register {discord_id} in pre_member_list: {response.status_code}")
	except Exception as e:
		logger.error(f"Failed to register {discord_id} in pre_member_list: {e}")


async def run_bot_if_configured() -> None:
	if not DISCORD_TOKEN:
		logger.warning("DISCORD_TOKEN is not set. Run API-only mode.")
		while True:
			await asyncio.sleep(3600)
	await bot.start(DISCORD_TOKEN)


async def run_web_api() -> None:
	config = uvicorn.Config(app, host="0.0.0.0", port=BOT_PORT, log_level="info")
	server = uvicorn.Server(config)
	await server.serve()


async def main() -> None:
	# Start daily cleanup loop when bot is ready
	try:
		daily_cleanup.start()
	except Exception:
		# If tasks cannot be started (no bot), ignore
		pass

	await asyncio.gather(run_web_api(), run_bot_if_configured())


@tasks.loop(hours=24)
async def daily_cleanup():
	"""Call backend cleanup endpoint once a day to remove expired prospective pre-members."""
	import httpx
	if not BACKEND_URL or not SHARED_SECRET:
		logger.debug("Skipping daily cleanup: BACKEND_URL or SHARED_SECRET not configured")
		return
	try:
		async with httpx.AsyncClient(timeout=10.0) as client:
			resp = await client.post(
				f"{BACKEND_URL}/api/v1/members/pre_member/cleanup",
				headers={"Authorization": f"Bearer {SHARED_SECRET}"},
			)
			if resp.status_code == 200:
				logger.info("Daily cleanup executed: %s", resp.json())
			else:
				logger.error("Daily cleanup failed: %s", resp.status_code)
	except Exception as e:
		logger.exception("Error while running daily cleanup: %s", e)


if __name__ == "__main__":
	asyncio.run(main())
