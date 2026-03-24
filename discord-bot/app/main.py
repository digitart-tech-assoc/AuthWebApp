"""役割: Bot起動エントリ"""

from __future__ import annotations

import asyncio
import logging
import os

import discord
import uvicorn
from discord.ext import commands
from fastapi import FastAPI

from app.web.internal_api import router as internal_router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
BOT_PORT = int(os.getenv("BOT_PORT", "8000"))

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

app = FastAPI(title="AuthWebApp Discord Bot", version="0.1.0")
app.include_router(internal_router)


@bot.event
async def on_ready() -> None:
	logger.info("Discord bot ready: %s", bot.user)


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
	await asyncio.gather(run_web_api(), run_bot_if_configured())


if __name__ == "__main__":
	asyncio.run(main())
