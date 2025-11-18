import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from typing import Optional, List
import re


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Забанить пользователя")
    @app_commands.describe(
        member="Пользователь для бана",
        reason="Причина бана"
    )
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        """Забанить пользователя"""
        await interaction.response.defer(ephemeral=True)

        # Нельзя забанить себя
        if member == interaction.user:
            await interaction.followup.send("❌ Нельзя забанить самого себя!", ephemeral=True)
            return

        # Нельзя забанить бота
        if member.bot:
            await interaction.followup.send("❌ Нельзя забанить бота!", ephemeral=True)
            return

        # Проверка иерархии ролей
        if interaction.user.top_role.position <= member.top_role.position:
            await interaction.followup.send("❌ Нельзя забанить пользователя с ролью выше или равной вашей!",
                                            ephemeral=True)
            return

        try:
            await member.send(f"Вы были забанены на сервере {interaction.guild.name}. Причина: {reason}")
        except:
            pass

        await member.ban(reason=reason)

        embed = discord.Embed(
            title="Пользователь забанен",
            description=f"{member.mention} был забанен.",
            color=discord.Color.red()
        )
        embed.add_field(name="Причина", value=reason or "Не указана")
        embed.add_field(name="Модератор", value=interaction.user.mention)

        await interaction.followup.send("Пользователь успешно забанен!", ephemeral=True)
        await interaction.channel.send(embed=embed)

    async def unban_autocomplete(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:
        """Autocomplete для разбана - показывает список забаненных пользователей"""
        try:
            bans = [ban async for ban in interaction.guild.bans(limit=25)]
            choices = []

            for ban_entry in bans:
                user = ban_entry.user
                # Создаем отображаемое имя
                display_name = f"{user.name}#{user.discriminator}"
                if user.global_name:
                    display_name = f"{user.global_name} ({user.name}#{user.discriminator})"

                # Добавляем ID для точного поиска
                choice_value = f"{user.id}|{user.name}"
                choice_name = f"{display_name} (ID: {user.id})"

                # Фильтруем по текущему вводу
                if current.lower() in choice_name.lower():
                    choices.append(app_commands.Choice(name=choice_name[:100], value=choice_value))

            return choices[:25]
        except Exception:
            return []

    @app_commands.command(name="unban", description="Разбанить пользователя")
    @app_commands.describe(
        target="Пользователь для разбана (используйте автодополнение)",
        reason="Причина разбана"
    )
    @app_commands.autocomplete(target=unban_autocomplete)
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, target: str, reason: Optional[str] = None):
        """
        Разбанить пользователя по ID или через автодополнение
        """
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild

        # Обрабатываем выбор из autocomplete (формат: "ID|username")
        if "|" in target:
            user_id = target.split("|")[0]
            try:
                user_id = int(user_id)
                user = await self.bot.fetch_user(user_id)
            except (ValueError, discord.NotFound):
                await interaction.followup.send("❌ Пользователь не найден.", ephemeral=True)
                return
        else:
            # Пытаемся обработать как ID
            try:
                user_id = int(target)
                user = await self.bot.fetch_user(user_id)
            except (ValueError, discord.NotFound):
                await interaction.followup.send("❌ Укажите корректный ID пользователя или выберите из списка.",
                                                ephemeral=True)
                return

        # Пытаемся разбанить
        try:
            await guild.unban(user, reason=f"Unban by {interaction.user} ({interaction.user.id}) - {reason}")
        except discord.NotFound:
            await interaction.followup.send("❌ Этот пользователь не в бан-листе.", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send("❌ У бота нет прав для разбанивания.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка при разбане: `{e}`", ephemeral=True)
            return

        # Успешный разбан
        embed = discord.Embed(
            title="Пользователь разбанен",
            description=f"**{user.name}#{user.discriminator}** был разбанен.",
            color=discord.Color.green()
        )
        embed.add_field(name="ID пользователя", value=str(user.id), inline=True)
        if reason:
            embed.add_field(name="Причина", value=reason, inline=True)
        embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)

        await interaction.followup.send("Пользователь успешно разбанен!", ephemeral=True)
        await interaction.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))