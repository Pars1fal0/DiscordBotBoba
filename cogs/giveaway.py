import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import re
from datetime import timedelta
from discord.utils import utcnow
from typing import Optional


class GiveawayCog(commands.Cog):
    """Ког с логикой розыгрышей по реакции."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="giveaway", description="Запустить розыгрыш")
    @app_commands.describe(
        duration="Длительность розыгрыша (например: 10s, 5m, 2h, 1d)",
        winners="Количество победителей",
        prize="Приз для розыгрыша"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def start_giveaway(self, interaction: discord.Interaction, duration: str, winners: int, prize: str):
        """
        Запуск розыгрыша.
        Пример: /giveaway duration:10m winners:3 prize:Нитро на месяц
        duration формата: 10s / 5m / 2h / 1d
        winners — количество победителей (целое число >= 1)
        """
        await interaction.response.defer(ephemeral=True)

        if winners < 1:
            await interaction.followup.send("❌ Количество победителей должно быть **минимум 1**.", ephemeral=True)
            return

        seconds = self.parse_duration(duration)
        if seconds is None:
            await interaction.followup.send("❌ Неверный формат времени. Используй, например: `10s`, `5m`, `2h`, `1d`.",
                                            ephemeral=True)
            return

        end_time = utcnow() + timedelta(seconds=seconds)
        emoji = "🎉"

        embed = discord.Embed(
            title="🎁 Розыгрыш!",
            description=(
                f"Приз: **{prize}**\n"
                f"Количество победителей: **{winners}**\n"
                f"Реагируй {emoji}, чтобы участвовать!\n\n"
                f"⏰ Закончится: <t:{int(end_time.timestamp())}:R>"
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Создано: {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send("Розыгрыш создан!", ephemeral=True)
        message = await interaction.channel.send(embed=embed)
        await message.add_reaction(emoji)

        # ждём завершения розыгрыша
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            return

        # пробуем снова получить сообщение
        try:
            message = await interaction.channel.fetch_message(message.id)
        except discord.NotFound:
            await interaction.channel.send("❌ Сообщение розыгрыша было удалено, итоги провести нельзя.")
            return

        # ищем нужную реакцию
        reaction = discord.utils.get(message.reactions, emoji=emoji)
        if reaction is None:
            await interaction.channel.send("❌ Никто не успел отреагировать на розыгрыш.")
            return

        # собираем участников
        users = [user async for user in reaction.users()]
        participants = [u for u in users if not u.bot]

        if not participants:
            await interaction.channel.send("❌ Участников нет, победителей выбрать невозможно.")
            return

        winners_count = min(winners, len(participants))
        winners_list = random.sample(participants, k=winners_count)

        winners_mentions = ", ".join(user.mention for user in winners_list)

        # обновляем embed
        finished_embed = message.embeds[0]
        finished_embed.color = discord.Color.green()
        finished_embed.title = "✅ Розыгрыш завершён!"
        finished_embed.description = (
            f"Приз: **{prize}**\n"
            f"Победители ({winners_count}): {winners_mentions}\n\n"
            f"Сообщение розыгрыша: [jump]({message.jump_url})"
        )
        await message.edit(embed=finished_embed)

        await interaction.channel.send(f"🎉 Поздравляем, {winners_mentions}! Вы выиграли **{prize}** 🎁")

    @staticmethod
    def parse_duration(duration: str) -> Optional[int]:
        """
        duration: строка вида 10s / 5m / 2h / 1d
        возвращает количество секунд или None, если формат неверный
        """
        pattern = r"^(\d+)([smhd])$"
        match = re.match(pattern, duration.lower())
        if not match:
            return None

        amount = int(match.group(1))
        unit = match.group(2)

        multipliers = {
            "s": 1,
            "m": 60,
            "h": 60 * 60,
            "d": 60 * 60 * 24,
        }

        return amount * multipliers[unit]


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayCog(bot))