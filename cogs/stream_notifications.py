import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
from typing import Optional

class StreamNotifications(commands.Cog):
    """Система уведомлений о начале стримов на Twitch/YouTube"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "stream_config.json"
        self.config = self._load_config()
        self.cooldown_minutes = 10  # Не спамить уведомлениями
        
    def _load_config(self) -> dict:
        """Загрузка конфигурации из JSON"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_config(self):
        """Сохранение конфигурации"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def _get_guild_config(self, guild_id: str) -> dict:
        """Получить конфигурацию сервера"""
        if guild_id not in self.config:
            self.config[guild_id] = {
                "enabled": False,
                "announce_channel": None,
                "ping_role": None,
                "active_streams": {}
            }
            self._save_config()
        return self.config[guild_id]
    
    def _is_streaming_activity(self, activity: discord.Activity) -> bool:
        """Проверка является ли активность стримом на Twitch/YouTube"""
        if activity.type != discord.ActivityType.streaming:
            return False
        
        # Проверяем URL на Twitch/YouTube
        if hasattr(activity, 'url') and activity.url:
            url = activity.url.lower()
            return 'twitch.tv' in url or 'youtube.com' in url or 'youtu.be' in url
        
        return False
    
    def _can_notify(self, guild_id: str, user_id: str) -> bool:
        """Проверка можно ли отправить уведомление (cooldown)"""
        guild_config = self._get_guild_config(guild_id)
        active_streams = guild_config.get("active_streams", {})
        
        if user_id in active_streams:
            last_notify = active_streams[user_id].get("started_at")
            if last_notify:
                try:
                    last_time = datetime.fromisoformat(last_notify)
                    if datetime.now() - last_time < timedelta(minutes=self.cooldown_minutes):
                        return False
                except:
                    pass
        
        return True
    
    def _mark_notified(self, guild_id: str, user_id: str):
        """Отметить что уведомление отправлено"""
        guild_config = self._get_guild_config(guild_id)
        if "active_streams" not in guild_config:
            guild_config["active_streams"] = {}
        
        guild_config["active_streams"][user_id] = {
            "started_at": datetime.now().isoformat(),
            "notified": True
        }
        self._save_config()
    
    def _clear_stream(self, guild_id: str, user_id: str):
        """Очистить статус стрима"""
        guild_config = self._get_guild_config(guild_id)
        if "active_streams" in guild_config and user_id in guild_config["active_streams"]:
            del guild_config["active_streams"][user_id]
            self._save_config()
    
    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        """Отслеживание начала стрима"""
        guild_id = str(after.guild.id)
        user_id = str(after.id)
        guild_config = self._get_guild_config(guild_id)
        
        # Проверяем что уведомления включены
        if not guild_config.get("enabled", False):
            return
        
        # Проверяем что канал настроен
        announce_channel_id = guild_config.get("announce_channel")
        if not announce_channel_id:
            return
        
        # Ищем стримящую активность
        streaming_activity = None
        for activity in after.activities:
            if self._is_streaming_activity(activity):
                streaming_activity = activity
                break
        
        # Проверяем статус до и после
        was_streaming = any(self._is_streaming_activity(act) for act in before.activities)
        is_streaming = streaming_activity is not None
        
        # Если начал стримить
        if is_streaming and not was_streaming:
            # Проверяем cooldown
            if not self._can_notify(guild_id, user_id):
                return
            
            # Отправляем уведомление
            channel = self.bot.get_channel(int(announce_channel_id))
            if channel:
                await self._send_stream_notification(channel, after, streaming_activity, guild_config)
                self._mark_notified(guild_id, user_id)
        
        # Если перестал стримить
        elif was_streaming and not is_streaming:
            self._clear_stream(guild_id, user_id)
    
    async def _send_stream_notification(self, channel: discord.TextChannel, member: discord.Member, 
                                       activity: discord.Activity, guild_config: dict):
        """Отправить уведомление о стриме"""
        # Определяем платформу
        platform = "Twitch" if "twitch.tv" in activity.url.lower() else "YouTube"
        platform_emoji = "🟣" if platform == "Twitch" else "🔴"
        
        # Создаём embed
        embed = discord.Embed(
            title=f"{platform_emoji} {member.display_name} начал стрим!",
            description=f"**{activity.name}**" if activity.name else "Без названия",
            color=discord.Color.purple() if platform == "Twitch" else discord.Color.red(),
            timestamp=datetime.now()
        )
        
        if activity.url:
            embed.add_field(name="🔗 Ссылка", value=f"[Смотреть стрим]({activity.url})", inline=False)
        
        embed.add_field(name="📺 Платформа", value=platform, inline=True)
        embed.add_field(name="👤 Стример", value=member.mention, inline=True)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        embed.set_footer(text=f"Стрим начался")
        
        # Упоминание роли
        ping_role_id = guild_config.get("ping_role")
        content = None
        if ping_role_id:
            role = member.guild.get_role(int(ping_role_id))
            if role:
                content = f"{role.mention} Присоединяйтесь к стриму!"
        
        await channel.send(content=content, embed=embed)
    
    # ==================== КОМАНДЫ ====================
    
    @app_commands.command(name="stream-setup", description="⚙️ [ADMIN] Настроить канал для анонсов стримов")
    @app_commands.describe(channel="Канал для уведомлений о стримах")
    @app_commands.checks.has_permissions(administrator=True)
    async def stream_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Настройка канала для анонсов"""
        guild_id = str(interaction.guild.id)
        guild_config = self._get_guild_config(guild_id)
        
        guild_config["announce_channel"] = str(channel.id)
        guild_config["enabled"] = True
        self._save_config()
        
        embed = discord.Embed(
            title="✅ Канал настроен",
            description=f"Анонсы стримов будут отправляться в {channel.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="stream-role", description="⚙️ [ADMIN] Настроить роль для пинга")
    @app_commands.describe(role="Роль которую нужно упоминать при стримах")
    @app_commands.checks.has_permissions(administrator=True)
    async def stream_role(self, interaction: discord.Interaction, role: discord.Role):
        """Настройка роли для пинга"""
        guild_id = str(interaction.guild.id)
        guild_config = self._get_guild_config(guild_id)
        
        guild_config["ping_role"] = str(role.id)
        self._save_config()
        
        embed = discord.Embed(
            title="✅ Роль настроена",
            description=f"При начале стрима будет упоминаться {role.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="stream-toggle", description="⚙️ [ADMIN] Включить/выключить уведомления")
    @app_commands.checks.has_permissions(administrator=True)
    async def stream_toggle(self, interaction: discord.Interaction):
        """Переключение уведомлений"""
        guild_id = str(interaction.guild.id)
        guild_config = self._get_guild_config(guild_id)
        
        current = guild_config.get("enabled", False)
        guild_config["enabled"] = not current
        self._save_config()
        
        status = "включены ✅" if guild_config["enabled"] else "выключены ❌"
        
        embed = discord.Embed(
            title="🔄 Статус изменён",
            description=f"Уведомления о стримах {status}",
            color=discord.Color.green() if guild_config["enabled"] else discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="stream-status", description="📊 Показать текущие настройки стримов")
    async def stream_status(self, interaction: discord.Interaction):
        """Показать настройки"""
        guild_id = str(interaction.guild.id)
        guild_config = self._get_guild_config(guild_id)
        
        enabled = guild_config.get("enabled", False)
        channel_id = guild_config.get("announce_channel")
        role_id = guild_config.get("ping_role")
        
        embed = discord.Embed(
            title="📊 Настройки уведомлений о стримах",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Статус",
            value="✅ Включено" if enabled else "❌ Выключено",
            inline=False
        )
        
        if channel_id:
            channel = interaction.guild.get_channel(int(channel_id))
            embed.add_field(
                name="📺 Канал анонсов",
                value=channel.mention if channel else "❌ Не найден",
                inline=False
            )
        else:
            embed.add_field(name="📺 Канал анонсов", value="❌ Не настроен", inline=False)
        
        if role_id:
            role = interaction.guild.get_role(int(role_id))
            embed.add_field(
                name="🔔 Роль для пинга",
                value=role.mention if role else "❌ Не найдена",
                inline=False
            )
        else:
            embed.add_field(name="🔔 Роль для пинга", value="❌ Не настроена", inline=False)
        
        # Активные стримы
        active_count = len(guild_config.get("active_streams", {}))
        embed.add_field(name="🔴 Активных стримов", value=str(active_count), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="stream-test", description="🧪 [ADMIN] Отправить тестовое уведомление")
    @app_commands.checks.has_permissions(administrator=True)
    async def stream_test(self, interaction: discord.Interaction):
        """Тестовое уведомление"""
        guild_id = str(interaction.guild.id)
        guild_config = self._get_guild_config(guild_id)
        
        channel_id = guild_config.get("announce_channel")
        if not channel_id:
            await interaction.response.send_message(
                "❌ Сначала настройте канал командой `/stream-setup`",
                ephemeral=True
            )
            return
        
        channel = interaction.guild.get_channel(int(channel_id))
        if not channel:
            await interaction.response.send_message(
                "❌ Канал для анонсов не найден",
                ephemeral=True
            )
            return
        
        # Создаём тестовый embed
        embed = discord.Embed(
            title="🟣 Тестовое уведомление о стриме",
            description="**Это тестовый стрим для проверки**",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🔗 Ссылка", value="[Пример ссылки](https://twitch.tv)", inline=False)
        embed.add_field(name="📺 Платформа", value="Twitch (тест)", inline=True)
        embed.add_field(name="👤 Стример", value=interaction.user.mention, inline=True)
        
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        embed.set_footer(text="Тестовое уведомление")
        
        # Упоминание роли
        ping_role_id = guild_config.get("ping_role")
        content = None
        if ping_role_id:
            role = interaction.guild.get_role(int(ping_role_id))
            if role:
                content = f"{role.mention} Это тест!"
        
        await channel.send(content=content, embed=embed)
        await interaction.response.send_message("✅ Тестовое уведомление отправлено!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(StreamNotifications(bot))
