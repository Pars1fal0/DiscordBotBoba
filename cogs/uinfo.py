import discord
from discord.ext import commands


class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def uinfo(self, ctx):
        em = discord.Embed(
            title="**👤 Информация о пользователе**",
            color=discord.Color.blurple()
        )
        user = ctx.author
        ws_ms = int(self.bot.latency * 1000)
        em.add_field(name="Имя:", value=user.mention, inline=True)
        em.add_field(name="ID:", value=user.id, inline=True)
        em.add_field(name="Пинг:", value=f"{ws_ms} ms", inline=True)
        em.add_field(name="Присоединился к серверу:", value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        em.add_field(name="Создал дискорд:", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        em.add_field(name="Статус:", value=user.status, inline=True)
        await ctx.send(embed=em)


async def setup(bot):
    await bot.add_cog(UserInfo(bot))