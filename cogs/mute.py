import discord
from discord.ext import commands
import asyncio
import time
from datetime import datetime, timedelta


class Mute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.muted_users = {}  # {guild_id: {user_id: unmute_time}}

    async def create_mute_role(self, guild):
        """Создает роль для мьюта если её нет"""
        mute_role = discord.utils.get(guild.roles, name="Muted")

        if not mute_role:
            try:
                #Создаем роль
                mute_role = await guild.create_role(
                    name="Muted",
                    color=discord.Color.dark_gray(),
                    reason="Роль для мьюта пользователей"
                )

                #Настраиваем права для роли во всех каналах
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(
                            mute_role,
                            send_messages=False,
                            send_messages_in_threads=False,
                            create_public_threads=False,
                            create_private_threads=False,
                            speak=False,
                            add_reactions=False,
                            connect=False
                        )
                    except:
                        continue

            except discord.Forbidden:
                return None

        return mute_role

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason="Не указана"):
        """Замутить пользователя"""
        if member == ctx.author:
            await ctx.send("❌ Нельзя замутить самого себя!")
            return

        if member.guild_permissions.administrator:
            await ctx.send("❌ Нельзя замутить администратора!")
            return

        mute_role = await self.create_mute_role(ctx.guild)
        if not mute_role:
            await ctx.send("❌ Не удалось создать или найти роль для мьюта!")
            return

        # Проверяем, не замьючен ли уже пользователь
        if mute_role in member.roles:
            await ctx.send("❌ Этот пользователь уже замьючен!")
            return

        try:
            # Добавляем роль мьюта
            await member.add_roles(mute_role, reason=reason)

            # Сохраняем в нашу базу
            guild_id = ctx.guild.id
            if guild_id not in self.muted_users:
                self.muted_users[guild_id] = {}

            # Создаем embed-сообщение
            embed = discord.Embed(
                title="🔇 Пользователь замьючен",
                color=discord.Color.red()
            )
            embed.add_field(name="Пользователь", value=member.mention, inline=True)
            embed.add_field(name="Модератор", value=ctx.author.mention, inline=True)
            embed.add_field(name="Причина", value=reason, inline=False)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

            await ctx.send(embed=embed)

            #Отправляем ЛС пользователю
            try:
                dm_embed = discord.Embed(
                    title="🔇 Вы были замьючены",
                    description=f"На сервере **{ctx.guild.name}**",
                    color=discord.Color.red()
                )
                dm_embed.add_field(name="Модератор", value=ctx.author.display_name, inline=True)
                dm_embed.add_field(name="Причина", value=reason, inline=True)
                await member.send(embed=dm_embed)
            except:
                pass  #Если ЛС закрыты

        except discord.Forbidden:
            await ctx.send("❌ У меня нет прав для выдачи ролей!")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member, *, reason="Не указана"):
        """Размутить пользователя"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")

        if not mute_role:
            await ctx.send("❌ Роль для мьюта не найдена!")
            return

        if mute_role not in member.roles:
            await ctx.send("❌ Этот пользователь не замьючен!")
            return

        try:
            #Убираем роль мьюта
            await member.remove_roles(mute_role, reason=reason)

            #Удаляем из нашей базы
            guild_id = ctx.guild.id
            if guild_id in self.muted_users and member.id in self.muted_users[guild_id]:
                del self.muted_users[guild_id][member.id]

            #Создаем embed-сообщение
            embed = discord.Embed(
                title="🔊 Пользователь размьючен",
                color=discord.Color.green()
            )
            embed.add_field(name="Пользователь", value=member.mention, inline=True)
            embed.add_field(name="Модератор", value=ctx.author.mention, inline=True)
            embed.add_field(name="Причина", value=reason, inline=False)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

            await ctx.send(embed=embed)

            #Отправляем ЛС пользователю
            try:
                dm_embed = discord.Embed(
                    title="🔊 Вы были размьючены",
                    description=f"На сервере **{ctx.guild.name}**",
                    color=discord.Color.green()
                )
                dm_embed.add_field(name="Модератор", value=ctx.author.display_name, inline=True)
                dm_embed.add_field(name="Причина", value=reason, inline=True)
                await member.send(embed=dm_embed)
            except:
                pass  #Если ЛС закрыты

        except discord.Forbidden:
            await ctx.send("❌ У меня нет прав для управления ролями!")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def tempmute(self, ctx, member: discord.Member, duration: str, *, reason="Не указана"):
        """Временно замутить пользователя (пример: 10m, 1h, 1d)"""
        if member == ctx.author:
            await ctx.send("❌ Нельзя замутить самого себя!")
            return

        if member.guild_permissions.administrator:
            await ctx.send("❌ Нельзя замутить администратора!")
            return

        # Парсим время
        time_units = {
            's': 1,  #секунды
            'm': 60,  #минуты
            'h': 3600,  #часы
            'd': 86400  #дни
        }

        try:
            unit = duration[-1].lower()
            if unit not in time_units:
                raise ValueError

            amount = int(duration[:-1])
            if amount <= 0:
                raise ValueError

            seconds = amount * time_units[unit]
            unmute_time = datetime.now() + timedelta(seconds=seconds)

        except (ValueError, IndexError):
            embed = discord.Embed(
                title="❌ Неверный формат времени",
                description="Используйте: `10s` (секунды), `5m` (минуты), `1h` (часы), `1d` (дни)",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        mute_role = await self.create_mute_role(ctx.guild)
        if not mute_role:
            await ctx.send("❌ Не удалось создать или найти роль для мьюта!")
            return

        if mute_role in member.roles:
            await ctx.send("❌ Этот пользователь уже замьючен!")
            return

        try:
            #Мьют
            await member.add_roles(mute_role, reason=reason)

            #Сохраняем время размьюта
            guild_id = ctx.guild.id
            if guild_id not in self.muted_users:
                self.muted_users[guild_id] = {}

            self.muted_users[guild_id][member.id] = unmute_time.timestamp()

            #Запускаем таймер для авто-размьюта
            self.bot.loop.create_task(self.auto_unmute(member, seconds))

            #Форматируем время для красивого вывода
            time_formats = {
                's': f"{amount} секунд",
                'm': f"{amount} минут",
                'h': f"{amount} часов",
                'd': f"{amount} дней"
            }

            #Embed-сообщение
            embed = discord.Embed(
                title="⏰ Пользователь временно замьючен",
                color=discord.Color.orange()
            )
            embed.add_field(name="Пользователь", value=member.mention, inline=True)
            embed.add_field(name="Длительность", value=time_formats[unit], inline=True)
            embed.add_field(name="Модератор", value=ctx.author.mention, inline=True)
            embed.add_field(name="Причина", value=reason, inline=False)
            embed.add_field(name="Размут", value=f"<t:{int(unmute_time.timestamp())}:R>", inline=True)

            await ctx.send(embed=embed)

            #ЛС пользователю
            try:
                dm_embed = discord.Embed(
                    title="⏰ Вы были временно замьючены",
                    description=f"На сервере **{ctx.guild.name}**",
                    color=discord.Color.orange()
                )
                dm_embed.add_field(name="Длительность", value=time_formats[unit], inline=True)
                dm_embed.add_field(name="Размут", value=f"<t:{int(unmute_time.timestamp())}:R>", inline=True)
                dm_embed.add_field(name="Модератор", value=ctx.author.display_name, inline=False)
                dm_embed.add_field(name="Причина", value=reason, inline=False)
                await member.send(embed=dm_embed)
            except:
                pass

        except discord.Forbidden:
            await ctx.send("❌ У меня нет прав для выдачи ролей!")

    async def auto_unmute(self, member, delay):
        """Автоматический размьют через указанное время"""
        await asyncio.sleep(delay)

        try:
            mute_role = discord.utils.get(member.guild.roles, name="Muted")
            if mute_role and mute_role in member.roles:
                await member.remove_roles(mute_role, reason="Авто-размьют")

                #Удаляем из базы
                guild_id = member.guild.id
                if guild_id in self.muted_users and member.id in self.muted_users[guild_id]:
                    del self.muted_users[guild_id][member.id]

                #Отправляем ЛС
                try:
                    dm_embed = discord.Embed(
                        title="🔊 Автоматический размьют",
                        description=f"Ваш мьют на сервере **{member.guild.name}** истёк!",
                        color=discord.Color.green()
                    )
                    await member.send(embed=dm_embed)
                except:
                    pass
        except:
            pass  #Если пользователь вышел с сервера или другие ошибки

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def muted_list(self, ctx):
        """Показать список замьюченных пользователей"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")

        if not mute_role:
            await ctx.send("❌ Роль для мьюта не найдена!")
            return

        muted_members = [member for member in ctx.guild.members if mute_role in member.roles]

        if not muted_members:
            await ctx.send("🔊 На сервере нет замьюченных пользователей!")
            return

        embed = discord.Embed(
            title="📋 Список замьюченных пользователей",
            color=discord.Color.orange()
        )

        for i, member in enumerate(muted_members[:10], 1):  # Ограничиваем 10 пользователями
            guild_id = ctx.guild.id
            unmute_time = None

            if guild_id in self.muted_users and member.id in self.muted_users[guild_id]:
                unmute_time = self.muted_users[guild_id][member.id]
                time_info = f"Размут: <t:{int(unmute_time)}:R>"
            else:
                time_info = "⏳ Бессрочно"

            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"{member.mention}\n{time_info}",
                inline=False
            )

        if len(muted_members) > 10:
            embed.set_footer(text=f"И ещё {len(muted_members) - 10} пользователей...")

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def muteinfo(self, ctx, member: discord.Member):
        """Информация о мьюте пользователя"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")

        if not mute_role or mute_role not in member.roles:
            await ctx.send("❌ Этот пользователь не замьючен!")
            return

        embed = discord.Embed(
            title=f"ℹ️ Информация о мьюте {member.display_name}",
            color=discord.Color.blue()
        )

        embed.add_field(name="Пользователь", value=member.mention, inline=True)
        embed.add_field(name="Статус", value="🔇 Замьючен", inline=True)

        guild_id = ctx.guild.id
        if guild_id in self.muted_users and member.id in self.muted_users[guild_id]:
            unmute_time = self.muted_users[guild_id][member.id]
            embed.add_field(name="Тип мьюта", value="⏰ Временный", inline=True)
            embed.add_field(name="Размут", value=f"<t:{int(unmute_time)}:R>", inline=True)
            embed.add_field(name="Осталось", value=f"<t:{int(unmute_time)}:R>", inline=True)
        else:
            embed.add_field(name="Тип мьюта", value="⏳ Бессрочный", inline=True)

        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Восстанавливает мьют если пользователь вышел и вернулся"""
        guild_id = member.guild.id

        if guild_id in self.muted_users and member.id in self.muted_users[guild_id]:
            mute_role = discord.utils.get(member.guild.roles, name="Muted")
            if mute_role:
                await asyncio.sleep(1)  #Ждем немного чтобы роли обновились
                await member.add_roles(mute_role, reason="Восстановление мьюта")


async def setup(bot):
    await bot.add_cog(Mute(bot))