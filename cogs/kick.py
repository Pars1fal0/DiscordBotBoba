import discord
from discord import app_commands
from discord.ext import commands
import asyncio


class Moderation2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Кикнуть пользователя с сервера")
    @app_commands.describe(
        member="Пользователь для кика",
        reason="Причина кика"
    )
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        """Кикнуть пользователя с сервера"""
        await interaction.response.defer(ephemeral=True)

        # Проверка на само-кик
        if member == interaction.user:
            await interaction.followup.send("❌ Нельзя кикнуть самого себя!", ephemeral=True)
            return

        # Проверка на кик бота
        if member.bot:
            await interaction.followup.send("❌ Нельзя кикнуть бота!", ephemeral=True)
            return

        # Проверка иерархии ролей
        if interaction.user.top_role.position <= member.top_role.position:
            await interaction.followup.send("❌ Нельзя кикнуть пользователя с ролью выше или равной вашей!",
                                            ephemeral=True)
            return

        # Проверка прав бота
        if not interaction.guild.me.guild_permissions.kick_members:
            await interaction.followup.send("❌ У бота нет прав для кика пользователей!", ephemeral=True)
            return

        if interaction.guild.me.top_role.position <= member.top_role.position:
            await interaction.followup.send("❌ Роль бота ниже роли пользователя, кик невозможен!", ephemeral=True)
            return

        # Отправляем сообщение пользователю
        try:
            await member.send(f"Вы были кикнуты с сервера {interaction.guild.name}. Причина: {reason}")
        except:
            pass  # Не удалось отправить ЛС - продолжаем

        # Кикаем пользователя
        await member.kick(reason=reason)

        # Создаем embed для публичного уведомления
        embed = discord.Embed(
            title="🔨 Пользователь кикнут",
            description=f"{member.mention} был кикнут с сервера",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Причина", value=reason or "Не указана", inline=True)
        embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"ID: {member.id}")

        # Отправляем подтверждение модератору
        await interaction.followup.send(f"✅ Пользователь {member.mention} был успешно кикнут!", ephemeral=True)

        # Отправляем публичное уведомление
        await interaction.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation2(bot))