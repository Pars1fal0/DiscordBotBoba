import discord
from discord.ext import commands

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def sinfo(self, ctx):
        guild = ctx.guild

        em = discord.Embed(
            title="**🖥️ Информация о дискорд сервере**",
            color=discord.Color.blurple()
        )

        if guild.icon:
            em.set_thumbnail(url=guild.icon.url)
        # em.add_field(name="\u200b", value="\u200b", inline=False)   пустое inline-поле
        em.add_field(name="Название сервера:", value=f'{guild.name}', inline=True)

        owner_value = guild.owner.mention if guild.owner else f'{guild.owner}'
        em.add_field(name="Владелец:", value=owner_value, inline=True)
        em.add_field(name="Пользователи:", value=f'{guild.member_count}', inline=True)
        em.add_field(name="Роли:", value=f'{len(guild.roles)}', inline=True)
        em.add_field(name="Каналы:", value=f'{len(guild.channels)}', inline=True)
        em.add_field(name="Дата создания:", value=f'{guild.created_at.strftime("%Y-%m-%d %H:%M:%S")}', inline=True)

        await ctx.send(embed=em)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
