import discord
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

    # команда: !giveaway 10m 3 Крутой приз
    @commands.command(name="giveaway", aliases=["gstart"])
    @commands.has_permissions(manage_guild=True)
    async def start_giveaway(self, ctx: commands.Context, duration: str, winners: int, *, prize: str):
        """
        Запуск розыгрыша.
        Пример: !giveaway 10m 3 Нитро на месяц
        duration формата: 10s / 5m / 2h / 1d
        winners — количество победителей (целое число >= 1)
        """
        if winners < 1:
            await ctx.send("❌ Количество победителей должно быть **минимум 1**.")
            return

        seconds = self.parse_duration(duration)
        if seconds is None:
            await ctx.send("❌ Неверный формат времени. Используй, например: `10s`, `5m`, `2h`, `1d`.")
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
        embed.set_footer(text=f"Создано: {ctx.author}", icon_url=ctx.author.display_avatar.url)

        message = await ctx.send(embed=embed)
        await message.add_reaction(emoji)

        # ждём завершения розыгрыша
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            return  # если вдруг что-то отменили – просто выходим

        # пробуем снова получить сообщение, вдруг были новые реакции
        try:
            message = await ctx.channel.fetch_message(message.id)
        except discord.NotFound:
            await ctx.send("❌ Сообщение розыгрыша было удалено, итоги провести нельзя.")
            return

        # ищем нужную реакцию
        reaction = discord.utils.get(message.reactions, emoji=emoji)
        if reaction is None:
            await ctx.send("❌ Никто не успел отреагировать на розыгрыш.")
            return

        # собираем участников
        users = [user async for user in reaction.users()]
        participants = [u for u in users if not u.bot]

        if not participants:
            await ctx.send("❌ Участников нет, победителей выбрать невозможно.")
            return

        winners_count = min(winners, len(participants))
        winners_list = random.sample(participants, k=winners_count)

        winners_mentions = ", ".join(user.mention for user in winners_list)

        # обновим embed, чтобы было видно, что розыгрыш завершён
        finished_embed = message.embeds[0]
        finished_embed.color = discord.Color.green()
        finished_embed.title = "✅ Розыгрыш завершён!"
        finished_embed.description = (
            f"Приз: **{prize}**\n"
            f"Победители ({winners_count}): {winners_mentions}\n\n"
            f"Сообщение розыгрыша: [jump]({message.jump_url})"
        )
        await message.edit(embed=finished_embed)

        await ctx.send(f"🎉 Поздравляем, {winners_mentions}! Вы выиграли **{prize}** 🎁")

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
