# cogs/stream_notifier.py
import json
import os
from typing import Dict, Any, Optional

import aiohttp
import discord
from discord.ext import commands, tasks

# ID канала, куда слать уведомления о стримах
STREAM_ANNOUNCE_CHANNEL_ID = 1411074449087922186  # <-- ПОМЕНЯЙ

# Ключи для API (задай в .env или прямо в коде)
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

LINKS_FILE = "stream_links.json"


class StreamNotifier(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.links: Dict[str, Dict[str, str]] = self.load_links()
        # cache, чтобы не спамить, если стрим уже объявлен
        self.currently_live = set()
        self.check_streams.start()

    # ---------- Работа с файлом ----------

    def load_links(self) -> Dict[str, Dict[str, str]]:
        if not os.path.exists(LINKS_FILE):
            return {}
        try:
            with open(LINKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_links(self):
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.links, f, ensure_ascii=False, indent=2)

    # ---------- Команды ----------

    @commands.group(name="stream", invoke_without_command=True)
    async def stream_group(self, ctx: commands.Context):
        """Команды управления уведомлениями о стримах."""
        await ctx.send(
            "Команды:\n"
            "`!stream linktwitch <логин>` — привязать Twitch\n"
            "`!stream linkyoutube <channel_id>` — привязать YouTube\n"
            "`!stream show` — показать привязки\n"
            "`!stream unlink <twitch|youtube>` — отвязать"
        )

    @stream_group.command(name="linktwitch")
    async def link_twitch(self, ctx: commands.Context, twitch_login: str):
        """Привязать Twitch логин к вашему профилю."""
        uid = str(ctx.author.id)
        self.links.setdefault(uid, {})
        self.links[uid]["twitch"] = twitch_login.lower()
        self.save_links()
        await ctx.send(f"✅ {ctx.author.mention}, Twitch-логин `{twitch_login}` привязан.")

    @stream_group.command(name="linkyoutube")
    async def link_youtube(self, ctx: commands.Context, youtube_channel_id: str):
        """Привязать YouTube channel ID к вашему профилю."""
        uid = str(ctx.author.id)
        self.links.setdefault(uid, {})
        self.links[uid]["youtube"] = youtube_channel_id
        self.save_links()
        await ctx.send(
            f"✅ {ctx.author.mention}, YouTube-канал `{youtube_channel_id}` привязан.\n"
            "ID можно взять в URL канала (например, `UCxxxx...`)."
        )

    @stream_group.command(name="show")
    async def show_links(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Показать привязанные аккаунты (по умолчанию — свои)."""
        member = member or ctx.author
        uid = str(member.id)
        data = self.links.get(uid)
        if not data:
            await ctx.send(f"ℹ️ У {member.mention} нет привязанных аккаунтов.")
            return
        twitch = data.get("twitch", "—")
        yt = data.get("youtube", "—")
        await ctx.send(
            f"👤 Аккаунты {member.mention}:\n"
            f"• Twitch: `{twitch}`\n"
            f"• YouTube: `{yt}`"
        )

    @stream_group.command(name="unlink")
    async def unlink(self, ctx: commands.Context, platform: str):
        """Отвязать Twitch или YouTube: !stream unlink twitch / youtube."""
        uid = str(ctx.author.id)
        if uid not in self.links:
            await ctx.send("У тебя нет привязок.")
            return

        platform = platform.lower()
        if platform not in ("twitch", "youtube"):
            await ctx.send("Нужно указать `twitch` или `youtube`.")
            return

        if platform in self.links[uid]:
            del self.links[uid][platform]
            if not self.links[uid]:
                del self.links[uid]
            self.save_links()
            await ctx.send(f"✅ {platform.capitalize()} отвязан.")
        else:
            await ctx.send(f"У тебя нет привязки для {platform}.")

    # ---------- Проверка стримов ----------

    @tasks.loop(minutes=2)
    async def check_streams(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(STREAM_ANNOUNCE_CHANNEL_ID)
        if channel is None:
            return

        async with aiohttp.ClientSession() as session:
            for uid, accs in list(self.links.items()):
                user_mention = f"<@{uid}>"

                # Twitch
                twitch_login = accs.get("twitch")
                if twitch_login:
                    key = f"twitch:{twitch_login}"
                    is_live, info = await self.check_twitch_live(session, twitch_login)
                    if is_live and key not in self.currently_live:
                        self.currently_live.add(key)
                        title = info.get("title", "Без названия")
                        url = f"https://twitch.tv/{twitch_login}"
                        emb = discord.Embed(
                            title=f"{user_mention} начал стрим на Twitch!",
                            description=f"**{title}**\n{url}",
                            color=discord.Color.purple(),
                        )
                        await channel.send(content=user_mention, embed=emb)
                    elif not is_live and key in self.currently_live:
                        self.currently_live.remove(key)

                # YouTube
                yt_id = accs.get("youtube")
                if yt_id:
                    key = f"yt:{yt_id}"
                    is_live, info = await self.check_youtube_live(session, yt_id)
                    if is_live and key not in self.currently_live:
                        self.currently_live.add(key)
                        title = info.get("title", "Без названия")
                        url = info.get("url", "https://youtube.com/")
                        emb = discord.Embed(
                            title=f"{user_mention} запустил стрим на YouTube!",
                            description=f"**{title}**\n{url}",
                            color=discord.Color.red(),
                        )
                        await channel.send(content=user_mention, embed=emb)
                    elif not is_live and key in self.currently_live:
                        self.currently_live.remove(key)

    @check_streams.before_loop
    async def before_check_streams(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.check_streams.cancel()

    # ---------- Twitch API ----------

    async def check_twitch_live(self, session: aiohttp.ClientSession, login: str):
        """
        Возвращает (is_live: bool, info: dict)
        info: {title: str}
        """
        if not TWITCH_CLIENT_ID or not TWITCH_TOKEN:
            return False, {}

        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {TWITCH_TOKEN}",
        }
        params = {"user_login": login}

        url = "https://api.twitch.tv/helix/streams"
        try:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    return False, {}
                data = await resp.json()
        except Exception:
            return False, {}

        streams = data.get("data", [])
        if not streams:
            return False, {}

        stream = streams[0]
        return True, {"title": stream.get("title", "")}

    # ---------- YouTube API ----------

    async def check_youtube_live(self, session: aiohttp.ClientSession, channel_id: str):
        """
        Возвращает (is_live: bool, info: dict)
        info: {title: str, url: str}
        """
        if not YOUTUBE_API_KEY:
            return False, {}

        # Ищем live-видео на канале
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "eventType": "live",
            "type": "video",
            "key": YOUTUBE_API_KEY,
            "maxResults": 1,
        }
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return False, {}
                data = await resp.json()
        except Exception:
            return False, {}

        items = data.get("items", [])
        if not items:
            return False, {}

        video = items[0]
        vid_id = video["id"]["videoId"]
        title = video["snippet"]["title"]
        url = f"https://www.youtube.com/watch?v={vid_id}"
        return True, {"title": title, "url": url}


async def setup(bot: commands.Bot):
    await bot.add_cog(StreamNotifier(bot))
