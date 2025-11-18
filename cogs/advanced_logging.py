import discord
from discord import app_commands
from discord.ext import commands
import datetime
import aiohttp
import io
import json
import os

LOG_CONFIG_FILE = "log_config.json"


class AdvancedLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_config = self.load_config()

    def load_config(self):
        """Загрузка конфигурации логгирования"""
        if os.path.exists(LOG_CONFIG_FILE):
            with open(LOG_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_config(self):
        """Сохранение конфигурации логгирования"""
        with open(LOG_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.log_config, f, ensure_ascii=False, indent=2)

    def get_log_channel(self, guild_id):
        """Получение канала для логов из конфига"""
        config = self.log_config.get(str(guild_id), {})
        return config.get('log_channel')

    @app_commands.command(name="setlogchannel", description="Установить канал для логов")
    @app_commands.describe(channel="Канал для отправки логов")
    @app_commands.default_permissions(manage_guild=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Установить канал для логов"""
        guild_id = str(interaction.guild_id)

        if guild_id not in self.log_config:
            self.log_config[guild_id] = {}

        self.log_config[guild_id]['log_channel'] = channel.id
        self.save_config()

        embed = discord.Embed(
            title="✅ Канал логов установлен",
            description=f"Логи будут отправляться в {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="logsettings", description="Настройки логгирования")
    @app_commands.default_permissions(manage_guild=True)
    async def log_settings(self, interaction: discord.Interaction):
        """Показать текущие настройки логгирования"""
        guild_id = str(interaction.guild_id)
        config = self.log_config.get(guild_id, {})

        embed = discord.Embed(
            title="⚙️ Настройки логгирования",
            color=discord.Color.blue()
        )

        log_channel_id = config.get('log_channel')
        if log_channel_id:
            channel = interaction.guild.get_channel(log_channel_id)
            embed.add_field(
                name="Канал логов",
                value=channel.mention if channel else "❌ Канал не найден",
                inline=False
            )
        else:
            embed.add_field(
                name="Канал логов",
                value="❌ Не установлен",
                inline=False
            )

        embed.add_field(
            name="Отслеживаемые события",
            value="• Массовое удаление сообщений\n• Создание приглашений\n• Удаление приглашений",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Логирование массового удаления сообщений"""
        if not messages or not messages[0].guild:
            return

        guild = messages[0].guild
        channel = messages[0].channel

        # Получаем канал для логов из конфига
        log_channel_id = self.get_log_channel(guild.id)
        if not log_channel_id:
            return

        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return

        # Создаем текстовый файл с удаленными сообщениями
        log_content = f"Массовое удаление сообщений в #{channel.name}\n"
        log_content += f"Время: {datetime.datetime.utcnow()}\n"
        log_content += f"Количество сообщений: {len(messages)}\n"
        log_content += "=" * 50 + "\n\n"

        for msg in sorted(messages, key=lambda x: x.created_at):
            if not msg.author.bot:
                log_content += f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author.name}: {msg.content}\n"
                if msg.attachments:
                    log_content += f"📎 Вложения: {len(msg.attachments)}\n"
                log_content += "\n"

        # Создаем файл
        file = discord.File(
            io.BytesIO(log_content.encode('utf-8')),
            filename=f"bulk_delete_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        embed = discord.Embed(
            title="💥 Массовое удаление сообщений",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Канал", value=channel.mention, inline=True)
        embed.add_field(name="Количество", value=len(messages), inline=True)

        await log_channel.send(embed=embed, file=file)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Логирование создания приглашения"""
        guild = invite.guild
        log_channel_id = self.get_log_channel(guild.id)
        if not log_channel_id:
            return

        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return

        embed = discord.Embed(
            title="📨 Создано приглашение",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="Создатель", value=invite.inviter.mention, inline=True)
        embed.add_field(name="Канал", value=invite.channel.mention, inline=True)
        embed.add_field(name="Код", value=invite.code, inline=True)

        if invite.max_age > 0:
            embed.add_field(name="Истекает",
                            value=f"<t:{int((datetime.datetime.utcnow() + datetime.timedelta(seconds=invite.max_age)).timestamp())}:R>",
                            inline=True)
        else:
            embed.add_field(name="Истекает", value="Никогда", inline=True)

        if invite.max_uses > 0:
            embed.add_field(name="Макс. использований", value=invite.max_uses, inline=True)
        else:
            embed.add_field(name="Макс. использований", value="Неограничено", inline=True)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Логирование удаления приглашения"""
        guild = invite.guild
        log_channel_id = self.get_log_channel(guild.id)
        if not log_channel_id:
            return

        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ Приглашение удалено",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="Канал", value=invite.channel.mention, inline=True)
        embed.add_field(name="Код", value=invite.code, inline=True)

        await log_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AdvancedLogging(bot))