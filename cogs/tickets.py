# cogs/tickets.py
import asyncio
import datetime
from io import StringIO

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput

# НАСТРОЙКИ – ЗАМЕНИ на свои ID
SUPPORT_ROLE_ID = 123456789012345678       # роль поддержки
LOG_CHANNEL_ID = 1436029413413224600       # канал для логов тикетов
TICKETS_CATEGORY_ID = 1437387793734172774   # категория для тикет-каналов

CATEGORY_TITLES = {
    "bug": "Баг",
    "idea": "Идея",
    "complaint": "Жалоба",
}


class TicketCloseView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Закрыть тикет",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket_close_button"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        channel = interaction.channel
        guild = interaction.guild

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "Эту кнопку нужно нажимать в текстовом канале тикета.",
                ephemeral=True
            )

        support_role = guild.get_role(SUPPORT_ROLE_ID)
        member = interaction.user

        is_support = support_role in member.roles if support_role else False
        is_admin = member.guild_permissions.administrator

        if not (is_support or is_admin):
            return await interaction.response.send_message(
                "Только поддержка или администратор могут закрывать тикеты.",
                ephemeral=True
            )

        await interaction.response.defer()

        # Генерация транскрипта
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        transcript = StringIO()
        transcript.write(f"Тикет: #{channel.name}\nID: {channel.id}\n")
        transcript.write(f"Закрыл: {member} ({member.id})\n")
        transcript.write(f"Дата закрытия: {datetime.datetime.utcnow()} UTC\n\n")
        transcript.write("---- Сообщения ----\n")

        async for msg in channel.history(limit=None, oldest_first=True):
            author = f"{msg.author} ({msg.author.id})"
            content = msg.content if msg.content else ""
            transcript.write(f"[{msg.created_at}] {author}: {content}\n")
            for a in msg.attachments:
                transcript.write(f"    [Файл] {a.url}\n")

        transcript.seek(0)

        if log_channel:
            file = discord.File(
                fp=transcript,
                filename=f"ticket-{channel.id}.txt"
            )
            embed = discord.Embed(
                title="Тикет закрыт",
                description=f"Канал: {channel.mention}\nЗакрыл: {member.mention}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed, file=file)

        await channel.send("Тикет будет удалён через 5 секунд...")
        await asyncio.sleep(5)
        await channel.delete(reason=f"Тикет закрыт {member}")


class TicketCreateModal(Modal):
    def __init__(self, bot: commands.Bot, category: str):
        self.bot = bot
        self.category = category

        title = f"Тикет: {CATEGORY_TITLES.get(category, 'Вопрос')}"
        super().__init__(title=title, timeout=300)

        self.subject = TextInput(
            label="Кратко опиши проблему/идею",
            placeholder="Например: Музыка не воспроизводится",
            max_length=100
        )
        self.description = TextInput(
            label="Подробное описание",
            style=discord.TextStyle.paragraph,
            placeholder="Что именно произошло, когда, какие команды/действия были?",
            max_length=1000
        )

        self.add_item(self.subject)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Проверяем, есть ли уже тикет у пользователя
        existing = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{user.id}"
        )
        if existing:
            return await interaction.response.send_message(
                f"У тебя уже есть тикет: {existing.mention}",
                ephemeral=True
            )

        category_channel = guild.get_channel(TICKETS_CATEGORY_ID)
        if not isinstance(category_channel, discord.CategoryChannel):
            return await interaction.response.send_message(
                "Категория для тикетов не настроена. Обратись к администратору.",
                ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )
        }

        support_role = guild.get_role(SUPPORT_ROLE_ID)
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        channel = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            category=category_channel,
            overwrites=overwrites,
            reason=f"Тикет ({self.category}) от {user} ({user.id})"
        )

        cat_title = CATEGORY_TITLES.get(self.category, "Вопрос")

        embed = discord.Embed(
            title=f"🎫 Новый тикет — {cat_title}",
            description=(
                f"**Тема:** {self.subject.value}\n\n"
                f"**Описание:**\n{self.description.value}\n\n"
                f"{user.mention}, ожидай ответа поддержки.\n"
                "_Не спамь и не создавай дубликаты тикетов._"
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text=f"ID пользователя: {user.id}")

        view = TicketCloseView(self.bot)

        content = user.mention
        if support_role:
            content += f" | <@&{SUPPORT_ROLE_ID}>"

        await channel.send(
            content=content,
            embed=embed,
            view=view
        )

        await interaction.response.send_message(
            f"Тикет создан: {channel.mention}",
            ephemeral=True
        )


class TicketCategorySelect(Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = [
            discord.SelectOption(
                label="Баг",
                value="bug",
                emoji="🐛",
                description="Что-то не работает / ошибка"
            ),
            discord.SelectOption(
                label="Идея",
                value="idea",
                emoji="💡",
                description="Предложение по улучшению"
            ),
            discord.SelectOption(
                label="Жалоба",
                value="complaint",
                emoji="⚠️",
                description="Жалоба на участника/модерацию"
            ),
        ]
        super().__init__(
            placeholder="Выбери категорию тикета…",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_category_select"
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        modal = TicketCreateModal(self.bot, category)
        await interaction.response.send_modal(modal)


class TicketCategoryView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=60)
        self.add_item(TicketCategorySelect(bot))


class TicketPanelView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Создать тикет",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="ticket_create_button"
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        guild = interaction.guild
        user = interaction.user

        # Проверяем, есть ли уже тикет у пользователя
        existing = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{user.id}"
        )
        if existing:
            return await interaction.response.send_message(
                f"У тебя уже есть тикет: {existing.mention}",
                ephemeral=True
            )

        # Категория нужна уже на этом этапе, проверим
        category = guild.get_channel(TICKETS_CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "Категория для тикетов не настроена. Обратись к администратору.",
                ephemeral=True
            )

        view = TicketCategoryView(self.bot)
        await interaction.response.send_message(
            "Выбери категорию тикета:",
            view=view,
            ephemeral=True
        )


class Tickets(commands.Cog):
    """Система тикетов с категориями"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ticketpanel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel_cmd(self, ctx: commands.Context):
        """Отправить панель с кнопкой создания тикета."""
        embed = discord.Embed(
            title="Поддержка",
            description=(
                "Нажми на кнопку ниже, чтобы создать тикет.\n\n"
                "Сначала выбери категорию (баг, идея, жалоба), "
                "а затем опиши проблему в форме."
            ),
            color=discord.Color.blurple()
        )
        view = TicketPanelView(self.bot)
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="ticketpanel", description="Отправить панель тикетов")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Поддержка",
            description=(
                "Нажми на кнопку ниже, чтобы создать тикет.\n\n"
                "Сначала выбери категорию (баг, идея, жалоба), "
                "а затем заполни форму."
            ),
            color=discord.Color.blurple()
        )
        view = TicketPanelView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
    bot.add_view(TicketPanelView(bot))
    bot.add_view(TicketCloseView(bot))
