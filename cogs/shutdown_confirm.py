import discord
from discord.ext import commands
import asyncio
import os
import sys


class ShutdownConfirm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_shutdowns = {}

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx):
        """Выключить бота с подтверждением (только для владельца)"""
        embed = discord.Embed(
            title="🔴 Подтверждение выключения",
            description="Вы уверены, что хотите выключить бота?",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Для подтверждения",
            value="Нажмите ✅ для выключения\nНажмите ❌ для отмены",
            inline=False
        )

        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        self.pending_shutdowns[ctx.author.id] = message.id

    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx):
        """Перезагрузить бота с подтверждением (только для владельца)"""
        embed = discord.Embed(
            title="🔄 Подтверждение перезагрузки",
            description="Вы уверены, что хотите перезагрузить бота?",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Для подтверждения",
            value="Нажмите ✅ для перезагрузки\nНажмите ❌ для отмены",
            inline=False
        )

        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        self.pending_shutdowns[ctx.author.id] = message.id

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Обработка реакций для подтверждения выключения"""
        if user.bot or user.id not in self.pending_shutdowns:
            return

        if reaction.message.id != self.pending_shutdowns[user.id]:
            return

        # Проверяем что это сообщение с подтверждением
        if len(reaction.message.embeds) == 0:
            return

        embed = reaction.message.embeds[0]

        if "Подтверждение выключения" in embed.title or "Подтверждение перезагрузки" in embed.title:
            if str(reaction.emoji) == "✅":
                # Подтверждение получено
                if "выключения" in embed.title:
                    # Выключение
                    new_embed = discord.Embed(
                        title="🔴 Выключение...",
                        description="Бот выключается...",
                        color=discord.Color.red()
                    )
                    await reaction.message.edit(embed=new_embed)
                    await reaction.message.clear_reactions()

                    print(f"🛑 Бот выключен пользователем {user} (ID: {user.id})")
                    del self.pending_shutdowns[user.id]

                    await asyncio.sleep(2)
                    await self.bot.close()

                elif "перезагрузки" in embed.title:
                    # Перезагрузка
                    new_embed = discord.Embed(
                        title="🔄 Перезагрузка...",
                        description="Бот перезагружается...",
                        color=discord.Color.orange()
                    )
                    await reaction.message.edit(embed=new_embed)
                    await reaction.message.clear_reactions()

                    print(f"🔄 Бот перезагружен пользователем {user} (ID: {user.id})")
                    del self.pending_shutdowns[user.id]

                    await asyncio.sleep(2)
                    os.execv(sys.executable, ['python'] + sys.argv)

            elif str(reaction.emoji) == "❌":
                # Отмена
                new_embed = discord.Embed(
                    title="✅ Действие отменено",
                    description="Выключение/перезагрузка отменена",
                    color=discord.Color.green()
                )
                await reaction.message.edit(embed=new_embed)
                await reaction.message.clear_reactions()
                del self.pending_shutdowns[user.id]

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Глобальная обработка ошибок для команд владельца"""
        if isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                title="❌ Доступ запрещен",
                description="Эта команда только для владельца бота!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ShutdownConfirm(bot))