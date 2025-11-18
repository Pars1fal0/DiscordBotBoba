import discord
from discord import app_commands
from discord.ext import commands


class HelpInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Показать список доступных команд")
    async def help_command(self, interaction: discord.Interaction):
        """Показать список доступных команд"""
        em = discord.Embed(
            title="**📘 Команды для пользователей**",
            description="Доступные команды, которые не требуют прав администратора.",
            color=discord.Color.blurple()
        )

        general_commands = [
            "`/help` — показать этот список",
            "`/sinfo` — информация о сервере",
            "`/uinfo` — информация о себе"
        ]

        em.add_field(
            name="Основные команды:",
            value="\n".join(general_commands),
            inline=False
        )

        is_admin = False
        if interaction.guild and isinstance(interaction.user, discord.Member):
            is_admin = interaction.user.guild_permissions.administrator

        if not is_admin:
            stream_commands = [
                "`/stream` — список стрим-команд",
                "`/stream linktwitch <логин>` — привязать Twitch",
                "`/stream linkyoutube <channel_id>` — привязать YouTube",
                "`/stream show [участник]` — посмотреть привязанные аккаунты",
                "`/stream unlink <twitch|youtube>` — отвязать платформу"
            ]

            em.add_field(
                name="Стрим-инструменты:",
                value="\n".join(stream_commands),
                inline=False
            )

        # Добавляем информацию о администраторских командах для админов
        if is_admin:
            admin_commands = [
                "`/ban` — забанить пользователя",
                "`/unban` — разбанить пользователя",
                "`/setwelcome` — установить канал приветствий",
                "`/setlogchannel` — установить канал для логов",
                "`/logsettings` — настройки логгирования",
                "`/commands` — полный список команд",
                "`/giveaway` — запустить розыгрыш"
            ]

            em.add_field(
                name="👑 Команды для администраторов:",
                value="\n".join(admin_commands),
                inline=False
            )

        em.set_footer(text="Для получения помощи обратитесь к администраторам сервера")

        await interaction.response.send_message(embed=em, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpInfo(bot))