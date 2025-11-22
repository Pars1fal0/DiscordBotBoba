# economy.py
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
import random
from typing import Optional, Literal

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.economy_file = 'economy.json'
        self.shop_file = 'shop.json'
        self.currency = "крионов"
        self.currency_emoji = "💎"
        
        # Создаём файлы если их нет
        self._ensure_files()
    
    def _ensure_files(self):
        """Создание файлов экономики и магазина если их нет"""
        if not os.path.exists(self.economy_file):
            with open(self.economy_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
        
        if not os.path.exists(self.shop_file):
            with open(self.shop_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "items": [],
                    "next_id": 1
                }, f, ensure_ascii=False, indent=4)
    
    def _load_economy(self) -> dict:
        """Загрузка данных экономики"""
        with open(self.economy_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_economy(self, data: dict):
        """Сохранение данных экономики"""
        with open(self.economy_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _load_shop(self) -> dict:
        """Загрузка данных магазина"""
        with open(self.shop_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_shop(self, data: dict):
        """Сохранение данных магазина"""
        with open(self.shop_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def _get_user_data(self, user_id: str) -> dict:
        """Получение данных пользователя"""
        economy = self._load_economy()
        if user_id not in economy:
            economy[user_id] = {
                "balance": 0,
                "last_daily": None,
                "last_work": None,
                "last_weekly": None,
                "last_monthly": None,
                "inventory": [],
                "game_stats": {
                    "slots_played": 0,
                    "slots_won": 0,
                    "roulette_played": 0,
                    "roulette_won": 0,
                    "coinflip_played": 0,
                    "coinflip_won": 0,
                    "total_won": 0,
                    "total_lost": 0
                },
                "achievements": {},
                "transactions": []
            }
            self._save_economy(economy)
        return economy[user_id]
    
    def _update_balance(self, user_id: str, amount: int):
        """Обновление баланса пользователя"""
        economy = self._load_economy()
        if user_id not in economy:
            self._get_user_data(user_id)
            economy = self._load_economy()
        
        economy[user_id]["balance"] += amount
        self._save_economy(economy)
    
    def _check_cooldown(self, last_time: Optional[str], hours: int) -> tuple[bool, Optional[str]]:
        """Проверка кулдауна. Возвращает (доступно, время до доступности)"""
        if last_time is None:
            return True, None
        
        last_dt = datetime.fromisoformat(last_time)
        now = datetime.now()
        cooldown = timedelta(hours=hours)
        time_passed = now - last_dt
        
        if time_passed >= cooldown:
            return True, None
        
        time_left = cooldown - time_passed
        hours_left = int(time_left.total_seconds() // 3600)
        minutes_left = int((time_left.total_seconds() % 3600) // 60)
        
        if hours_left > 0:
            return False, f"{hours_left}ч {minutes_left}м"
        else:
            return False, f"{minutes_left}м"

    def _get_booster_multiplier(self, member: discord.Member) -> float:
        """Получить множитель для бустера сервера"""
        if member.premium_since:
            return 1.5
        return 1.0
    
    def _add_transaction(self, user_id: str, trans_type: str, amount: int, details: str = ""):
        """Добавить транзакцию в историю (последние 100)"""
        economy = self._load_economy()
        if user_id not in economy:
            self._get_user_data(user_id)
            economy = self._load_economy()
        
        transaction = {
            "type": trans_type,
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        
        if "transactions" not in economy[user_id]:
            economy[user_id]["transactions"] = []
        
        economy[user_id]["transactions"].insert(0, transaction)
        economy[user_id]["transactions"] = economy[user_id]["transactions"][:100]
        self._save_economy(economy)
    
    def _check_achievement(self, user_id: str, achievement_id: str) -> bool:
        """Проверить и разблокировать достижение если еще не разблокировано"""
        economy = self._load_economy()
        if user_id not in economy:
            return False
        
        if "achievements" not in economy[user_id]:
            economy[user_id]["achievements"] = {}
        
        if achievement_id not in economy[user_id]["achievements"]:
            economy[user_id]["achievements"][achievement_id] = {
                "unlocked": True,
                "date": datetime.now().isoformat()
            }
            self._save_economy(economy)
            return True
        return False
    
    # ==================== ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ====================
    
    @app_commands.command(name="balance", description="💰 Посмотреть баланс")
    @app_commands.describe(user="Пользователь для проверки баланса")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Показать баланс пользователя"""
        target = user or interaction.user
        user_data = self._get_user_data(str(target.id))
        
        em = discord.Embed(
            title=f"{self.currency_emoji} Баланс",
            description=f"**{target.display_name}** имеет **{user_data['balance']:,}** {self.currency}",
            color=discord.Color.gold()
        )
        em.set_thumbnail(url=target.display_avatar.url)
        em.set_footer(text=f"Запрос от {interaction.user.display_name}", 
                      icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="daily", description="🎁 Получить ежедневную награду")
    async def daily(self, interaction: discord.Interaction):
        """Ежедневная награда крионов"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        
        can_claim, time_left = self._check_cooldown(user_data.get("last_daily"), 24)
        
        if not can_claim:
            em = discord.Embed(
                title="⏰ Слишком рано!",
                description=f"Вы уже получили ежедневную награду!\nПопробуйте снова через: **{time_left}**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Награда от 100 до 500 крионов
        base_reward = random.randint(100, 500)
        multiplier = self._get_booster_multiplier(interaction.user)
        reward = int(base_reward * multiplier)
        
        economy = self._load_economy()
        economy[user_id]["balance"] += reward
        economy[user_id]["last_daily"] = datetime.now().isoformat()
        self._save_economy(economy)
        
        # Добавляем транзакцию
        self._add_transaction(user_id, "daily", reward, "Ежедневная награда")
        
        # Проверяем достижение
        self._check_achievement(user_id, "first_daily")
        
        em = discord.Embed(
            title="🎁 Ежедневная награда получена!",
            description=f"Вы получили **{reward:,}** {self.currency_emoji} {self.currency}!",
            color=discord.Color.green()
        )
        
        if multiplier > 1.0:
            em.add_field(
                name="🚀 Бонус бустера!",
                value=f"Множитель x{multiplier} ({base_reward} → {reward})",
                inline=False
            )
        
        em.add_field(name="Новый баланс", value=f"{economy[user_id]['balance']:,} {self.currency_emoji}")
        em.set_footer(text="Возвращайтесь завтра за новой наградой!")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="work", description="💼 Поработать и заработать крионы")
    async def work(self, interaction: discord.Interaction):
        """Работа за крионы с кулдауном"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        
        can_work, time_left = self._check_cooldown(user_data.get("last_work"), 1)
        
        if not can_work:
            em = discord.Embed(
                title="😴 Вы устали!",
                description=f"Вы уже работали недавно!\nМожно работать снова через: **{time_left}**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Награда от 50 до 200 крионов
        jobs = [
            "поработали программистом",
            "добыли криптовалюту",
            "разработали бота",
            "провели стрим",
            "написали статью",
            "создали мем",
            "сделали дизайн",
            "протестировали игру"
        ]
        job = random.choice(jobs)
        base_reward = random.randint(50, 200)
        multiplier = self._get_booster_multiplier(interaction.user)
        reward = int(base_reward * multiplier)
        
        economy = self._load_economy()
        economy[user_id]["balance"] += reward
        economy[user_id]["last_work"] = datetime.now().isoformat()
        self._save_economy(economy)
        
        # Добавляем транзакцию
        self._add_transaction(user_id, "work", reward, job)
        
        # Проверяем достижение
        self._check_achievement(user_id, "first_work")
        
        em = discord.Embed(
            title="💼 Работа выполнена!",
            description=f"Вы **{job}** и заработали **{reward:,}** {self.currency_emoji} {self.currency}!",
            color=discord.Color.blue()
        )
        
        if multiplier > 1.0:
            em.add_field(
                name="🚀 Бонус бустера!",
                value=f"Множитель x{multiplier} ({base_reward} → {reward})",
                inline=False
            )
        
        em.add_field(name="Новый баланс", value=f"{economy[user_id]['balance']:,} {self.currency_emoji}")
        em.set_footer(text="Возвращайтесь через час!")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="weekly", description="📅 Получить еженедельную награду")
    async def weekly(self, interaction: discord.Interaction):
        """Еженедельная награда крионов"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        
        can_claim, time_left = self._check_cooldown(user_data.get("last_weekly"), 24 * 7)
        
        if not can_claim:
            em = discord.Embed(
                title="⏰ Слишком рано!",
                description=f"Вы уже получили еженедельную награду!\nПопробуйте снова через: **{time_left}**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        base_reward = random.randint(1000, 2000)
        multiplier = self._get_booster_multiplier(interaction.user)
        reward = int(base_reward * multiplier)
        
        economy = self._load_economy()
        economy[user_id][" balance"] += reward
        economy[user_id]["last_weekly"] = datetime.now().isoformat()
        self._save_economy(economy)
        
        self._add_transaction(user_id, "weekly", reward, "Еженедельная награда")
        
        em = discord.Embed(
            title="📅 Еженедельная награда получена!",
            description=f"Вы получили **{reward:,}** {self.currency_emoji} {self.currency}!",
            color=discord.Color.purple()
        )
        
        if multiplier > 1.0:
            em.add_field(
                name="🚀 Бонус бустера!",
                value=f"Множитель x{multiplier} ({base_reward} → {reward})",
                inline=False
            )
        
        em.add_field(name="Новый баланс", value=f"{economy[user_id]['balance']:,} {self.currency_emoji}")
        em.set_footer(text="Возвращайтесь через неделю!")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="monthly", description="🗓️ Получить ежемесячную награду")
    async def monthly(self, interaction: discord.Interaction):
        """Ежемесячная награда крионов"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        
        can_claim, time_left = self._check_cooldown(user_data.get("last_monthly"), 24 * 30)
        
        if not can_claim:
            em = discord.Embed(
                title="⏰ Слишком рано!",
                description=f"Вы уже получили ежемесячную награду!\nПопробуйте снова через: **{time_left}**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        base_reward = random.randint(5000, 10000)
        # Особый бонус для бустеров x2
        multiplier = 2.0 if interaction.user.premium_since else 1.0
        reward = int(base_reward * multiplier)
        
        economy = self._load_economy()
        economy[user_id]["balance"] += reward
        economy[user_id]["last_monthly"] = datetime.now().isoformat()
        self._save_economy(economy)
        
        self._add_transaction(user_id, "monthly", reward, "Ежемесячная награда")
        
        em = discord.Embed(
            title="🗓️ Ежемесячная награда получена!",
            description=f"Вы получили **{reward:,}** {self.currency_emoji} {self.currency}!",
            color=discord.Color.magenta()
        )
        
        if multiplier > 1.0:
            em.add_field(
                name="🚀 Мега-бонус бустера!",
                value=f"Множитель x{multiplier} ({base_reward} → {reward})",
                inline=False
            )
        
        em.add_field(name="Новый баланс", value=f"{economy[user_id]['balance']:,} {self.currency_emoji}")
        em.set_footer(text="Возвращайтесь через месяц!")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="transfer", description="💸 Передать крионы другому пользователю")
    @app_commands.describe(
        user="Кому передать крионы",
        amount="Количество крионов"
    )
    async def transfer(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Передача крионов другому пользователю"""
        if amount <= 0:
            await interaction.response.send_message("❌ Сумма должна быть больше 0!", ephemeral=True)
            return
        
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ Нельзя передавать крионы самому себе!", ephemeral=True)
            return
        
        if user.bot:
            await interaction.response.send_message("❌ Нельзя передавать крионы ботам!", ephemeral=True)
            return
        
        sender_id = str(interaction.user.id)
        receiver_id = str(user.id)
        
        sender_data = self._get_user_data(sender_id)
        
        if sender_data["balance"] < amount:
            em = discord.Embed(
                title="❌ Недостаточно средств!",
                description=f"У вас всего **{sender_data['balance']:,}** {self.currency_emoji}\nА вы пытаетесь отправить **{amount:,}** {self.currency_emoji}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Выполняем перевод
        economy = self._load_economy()
        economy[sender_id]["balance"] -= amount
        
        # Создаём данные получателя если их нет
        if receiver_id not in economy:
            self._get_user_data(receiver_id)
            economy = self._load_economy()
        
        economy[receiver_id]["balance"] += amount
        self._save_economy(economy)
        
        # Логируем транзакции
        self._add_transaction(sender_id, "transfer", -amount, f"Отправлено {user.display_name}")
        self._add_transaction(receiver_id, "transfer", amount, f"Получено от {interaction.user.display_name}")
        
        em = discord.Embed(
            title="💸 Перевод выполнен!",
            description=f"**{interaction.user.display_name}** → **{user.display_name}**",
            color=discord.Color.green()
        )
        em.add_field(name="Сумма", value=f"{amount:,} {self.currency_emoji}", inline=False)
        em.add_field(name="Ваш новый баланс", value=f"{economy[sender_id]['balance']:,} {self.currency_emoji}")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="leaderboard", description="🏆 Топ самых богатых пользователей")
    async def leaderboard(self, interaction: discord.Interaction):
        """Рейтинг пользователей по балансу"""
        economy = self._load_economy()
        
        if not economy:
            await interaction.response.send_message("❌ Пока никто не зарабатывал крионы!", ephemeral=True)
            return
        
        # Сортируем по балансу
        sorted_users = sorted(economy.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
        
        em = discord.Embed(
            title="🏆 Топ богатых пользователей",
            description="10 самых богатых участников сервера",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (user_id, data) in enumerate(sorted_users, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                medal = medals[idx - 1] if idx <= 3 else f"`{idx}.`"
                em.add_field(
                    name=f"{medal} {user.display_name}",
                    value=f"{data['balance']:,} {self.currency_emoji}",
                    inline=False
                )
            except:
                continue
        
        em.set_footer(text=f"Запрос от {interaction.user.display_name}", 
                      icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="shop", description="🛒 Посмотреть магазин")
    async def shop(self, interaction: discord.Interaction):
        """Показать магазин товаров"""
        shop_data = self._load_shop()
        items = shop_data.get("items", [])
        
        if not items:
            em = discord.Embed(
                title="🛒 Магазин",
                description="Магазин пуст! Администратор ещё не добавил товары.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=em)
            return
        
        em = discord.Embed(
            title="🛒 Магазин товаров",
            description="Используйте `/buy <id>` для покупки",
            color=discord.Color.blue()
        )
        
        for item in items:
            item_type = "🎭 Роль" if item["type"] == "role" else "📦 Предмет"
            description = item.get("description", "Без описания")
            
            em.add_field(
                name=f"ID: {item['id']} | {item['name']} {item_type}",
                value=f"{description}\n**Цена:** {item['price']:,} {self.currency_emoji}",
                inline=False
            )
        
        em.set_footer(text=f"Всего товаров: {len(items)}")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="buy", description="💰 Купить товар из магазина")
    @app_commands.describe(item_id="ID товара из магазина")
    async def buy(self, interaction: discord.Interaction, item_id: int):
        """Покупка товара из магазина"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        shop_data = self._load_shop()
        
        # Ищем товар
        item = None
        for shop_item in shop_data.get("items", []):
            if shop_item["id"] == item_id:
                item = shop_item
                break
        
        if not item:
            await interaction.response.send_message(f"❌ Товар с ID {item_id} не найден!", ephemeral=True)
            return
        
        # Проверяем баланс
        if user_data["balance"] < item["price"]:
            em = discord.Embed(
                title="❌ Недостаточно средств!",
                description=f"У вас: **{user_data['balance']:,}** {self.currency_emoji}\nНужно: **{item['price']:,}** {self.currency_emoji}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        # Проверяем что не куплено уже
        if item_id in user_data.get("inventory", []):
            await interaction.response.send_message(f"❌ Вы уже купили **{item['name']}**!", ephemeral=True)
            return
        
        # Если это роль, проверяем и выдаём
        if item["type"] == "role":
            role_id = item.get("role_id")
            if role_id:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    try:
                        await interaction.user.add_roles(role)
                    except discord.Forbidden:
                        await interaction.response.send_message("❌ У бота нет прав на выдачу этой роли!", ephemeral=True)
                        return
                    except Exception as e:
                        await interaction.response.send_message(f"❌ Ошибка при выдаче роли: {e}", ephemeral=True)
                        return
                else:
                    await interaction.response.send_message("❌ Роль не найдена на сервере!", ephemeral=True)
                    return
        
        # Выполняем покупку
        economy = self._load_economy()
        economy[user_id]["balance"] -= item["price"]
        if "inventory" not in economy[user_id]:
            economy[user_id]["inventory"] = []
        economy[user_id]["inventory"].append(item_id)
        self._save_economy(economy)
        
        # Логируем транзакцию
        self._add_transaction(user_id, "purchase", -item["price"], f"Куплено: {item['name']}")
        
        em = discord.Embed(
            title="✅ Покупка успешна!",
            description=f"Вы купили **{item['name']}**!",
            color=discord.Color.green()
        )
        em.add_field(name="Потрачено", value=f"{item['price']:,} {self.currency_emoji}")
        em.add_field(name="Остаток", value=f"{economy[user_id]['balance']:,} {self.currency_emoji}")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="inventory", description="🎒 Посмотреть свой инвентарь")
    async def inventory(self, interaction: discord.Interaction):
        """Показать инвентарь пользователя"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        inventory = user_data.get("inventory", [])
        
        if not inventory:
            em = discord.Embed(
                title="🎒 Ваш инвентарь",
                description="Ваш инвентарь пуст! Купите что-нибудь в магазине!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return
        
        shop_data = self._load_shop()
        
        em = discord.Embed(
            title="🎒 Ваш инвентарь",
            description=f"У вас {len(inventory)} предметов",
            color=discord.Color.purple()
        )
        
        for item_id in inventory:
            # Ищем товар в магазине
            for shop_item in shop_data.get("items", []):
                if shop_item["id"] == item_id:
                    item_type = "🎭 Роль" if shop_item["type"] == "role" else "📦 Предмет"
                    em.add_field(
                        name=f"{shop_item['name']} {item_type}",
                        value=f"ID: {item_id} | Цена: {shop_item['price']:,} {self.currency_emoji}",
                        inline=False
                    )
                    break
        
        await interaction.response.send_message(embed=em, ephemeral=True)
    
    # ==================== ИГРЫ ====================
    
    @app_commands.command(name="slots", description="🎰 Сыграть в игровой автомат")
    @app_commands.describe(bet="Ставка (минимум 10 крионов)")
    async def slots(self, interaction: discord.Interaction, bet: int):
        """Игровой автомат с тремя барабанами"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        
        if bet < 10:
            await interaction.response.send_message("❌ Минимальная ставка 10 крионов!", ephemeral=True)
            return
        
        if user_data["balance"] < bet:
            await interaction.response.send_message(
                f"❌ У вас недостаточно крионов! (баланс: {user_data['balance']:,} {self.currency_emoji})",
                ephemeral=True
            )
            return
        
        # Символы слотов
        symbols = ["🍒", "🍋", "🍊", "⭐", "💎", "7️⃣"]
        weights = [30, 25, 20, 15, 8, 2]
        
        # Крутим барабаны
        reels = random.choices(symbols, weights=weights, k=3)
        
        # Проверяем выигрыш
        winnings = 0
        multiplier_text = ""
        
        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "7️⃣":
                winnings = bet * 50
                multiplier_text = "ДЖЕКПОТ x50!"
                self._check_achievement(user_id, "jackpot")
            elif reels[0] == "💎":
                winnings = bet * 10
                multiplier_text = "x10"
            elif reels[0] == "⭐":
                winnings = bet * 5
                multiplier_text = "x5"
            else:
                winnings = bet * 2
                multiplier_text = "x2"
        elif reels[0] == reels[1] or reels[1] == reels[2]:
            winnings = bet
            multiplier_text = "Возврат ставки"
        
        # Бонус бустера
        booster_mult = self._get_booster_multiplier(interaction.user)
        if winnings > 0 and booster_mult > 1.0:
            winnings = int(winnings * booster_mult)
        
        # Обновляем баланс
        economy = self._load_economy()
        economy[user_id]["balance"] -= bet
        economy[user_id]["balance"] += winnings
        
        # Статистика
        if "game_stats" not in economy[user_id]:
            economy[user_id]["game_stats"] = {}
        
        economy[user_id]["game_stats"]["slots_played"] = economy[user_id]["game_stats"].get("slots_played", 0) + 1
        
        if winnings > bet:
            economy[user_id]["game_stats"]["slots_won"] = economy[user_id]["game_stats"].get("slots_won", 0) + 1
            economy[user_id]["game_stats"]["total_won"] = economy[user_id]["game_stats"].get("total_won", 0) + (winnings - bet)
            self._add_transaction(user_id, "game_win", winnings - bet, "Слоты (выигрыш)")
        else:
            economy[user_id]["game_stats"]["total_lost"] = economy[user_id]["game_stats"].get("total_lost", 0) + bet
            self._add_transaction(user_id, "game_loss", -bet, "Слоты (проигрыш)")
        
        self._save_economy(economy)
        
        # Достижение за первую игру
        if economy[user_id]["game_stats"].get("slots_played", 0) == 1:
            self._check_achievement(user_id, "first_game")
        
        # Результат
        result = " | ".join(reels)
        
        if winnings > bet:
            em = discord.Embed(
                title="🎰 Слоты - ВЫИГРЫШ!",
                description=f"**{result}**\n\n{multiplier_text}",
                color=discord.Color.gold()
            )
            em.add_field(name="Ставка", value=f"{bet:,} {self.currency_emoji}", inline=True)
            em.add_field(name="Выигрыш", value=f"+{winnings - bet:,} {self.currency_emoji}", inline=True)
        elif winnings == bet:
            em = discord.Embed(
                title="🎰 Слоты - Ничья",
                description=f"**{result}**\n\n{multiplier_text}",
                color=discord.Color.blue()
            )
        else:
            em = discord.Embed(
                title="🎰 Слоты - Проигрыш",
                description=f"**{result}**",
                color=discord.Color.red()
            )
            em.add_field(name="Потеря", value=f"-{bet:,} {self.currency_emoji}", inline=True)
        
        em.add_field(name="Новый баланс", value=f"{economy[user_id]['balance']:,} {self.currency_emoji}", inline=False)
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="roulette", description="🎲 Сыграть в рулетку")
    @app_commands.describe(
        bet="Ставка (минимум 50 крионов)",
        color="Цвет для ставки"
    )
    async def roulette(self, interaction: discord.Interaction, bet: int, color: Literal["red", "black", "green"]):
        """Рулетка - ставка на цвет"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        
        if bet < 50:
            await interaction.response.send_message("❌ Минимальная ставка 50 крионов!", ephemeral=True)
            return
        
        if user_data["balance"] < bet:
            await interaction.response.send_message(
                f"❌ У вас недостаточно крионов! (баланс: {user_data['balance']:,} {self.currency_emoji})",
                ephemeral=True
            )
            return
        
        # Крутим рулетку
        colors = ["red"] * 18 + ["black"] * 18 + ["green"] * 2
        result_color = random.choice(colors)
        
        # Эмодзи для цветов
        color_emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}
        color_names = {"red": "Красное", "black": "Чёрное", "green": "Зелёное (0)"}
        
        # Проверяем выигрыш
        winnings = 0
        if result_color == color:
            if color == "green":
                winnings = bet * 10
            else:
                winnings = bet * 2
        
        # Бонус бустера
        booster_mult = self._get_booster_multiplier(interaction.user)
        if winnings > 0 and booster_mult > 1.0:
            winnings = int(winnings * booster_mult)
        
        # Обновляем баланс
        economy = self._load_economy()
        economy[user_id]["balance"] -= bet
        economy[user_id]["balance"] += winnings
        
        # Статистика
        if "game_stats" not in economy[user_id]:
            economy[user_id]["game_stats"] = {}
        
        economy[user_id]["game_stats"]["roulette_played"] = economy[user_id]["game_stats"].get("roulette_played", 0) + 1
        
        if winnings > bet:
            economy[user_id]["game_stats"]["roulette_won"] = economy[user_id]["game_stats"].get("roulette_won", 0) + 1
            economy[user_id]["game_stats"]["total_won"] = economy[user_id]["game_stats"].get("total_won", 0) + (winnings - bet)
            self._add_transaction(user_id, "game_win", winnings - bet, "Рулетка (выигрыш)")
        else:
            economy[user_id]["game_stats"]["total_lost"] = economy[user_id]["game_stats"].get("total_lost", 0) + bet
            self._add_transaction(user_id, "game_loss", -bet, "Рулетка (проигрыш)")
        
        self._save_economy(economy)
        
        # Результат
        if winnings > 0:
            em = discord.Embed(
                title="🎲 Рулетка - ВЫИГРЫШ!",
                description=f"Выпало: **{color_names[result_color]}** {color_emoji[result_color]}\nВы поставили на: **{color_names[color]}** {color_emoji[color]}",
                color=discord.Color.gold()
            )
            em.add_field(name="Ставка", value=f"{bet:,} {self.currency_emoji}", inline=True)
            em.add_field(name="Выигрыш", value=f"+{winnings - bet:,} {self.currency_emoji}", inline=True)
        else:
            em = discord.Embed(
                title="🎲 Рулетка - Проигрыш",
                description=f"Выпало: **{color_names[result_color]}** {color_emoji[result_color]}\nВы поставили на: **{color_names[color]}** {color_emoji[color]}",
                color=discord.Color.red()
            )
            em.add_field(name="Потеря", value=f"-{bet:,} {self.currency_emoji}", inline=True)
        
        em.add_field(name="Новый баланс", value=f"{economy[user_id]['balance']:,} {self.currency_emoji}", inline=False)
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="coinflip", description="🪙 Подбросить монетку")
    @app_commands.describe(
        bet="Ставка",
        side="Орёл или решка"
    )
    async def coinflip(self, interaction: discord.Interaction, bet: int, side: Literal["heads", "tails"]):
        """Подбрасывание монетки"""
        user_id = str(interaction.user.id)
        user_data = self._get_user_data(user_id)
        
        if bet <= 0:
            await interaction.response.send_message("❌ Ставка должна быть больше 0!", ephemeral=True)
            return
        
        if user_data["balance"] < bet:
            await interaction.response.send_message(
                f"❌ У вас недостаточно крионов! (баланс: {user_data['balance']:,} {self.currency_emoji})",
                ephemeral=True
            )
            return
        
        # Подбрасываем монетку
        result = random.choice(["heads", "tails"])
        
        side_names = {"heads": "Орёл 🦅", "tails": "Решка 🔰"}
        
        # Проверяем выигрыш
        winnings = bet * 2 if result == side else 0
        
        # Бонус бустера
        booster_mult = self._get_booster_multiplier(interaction.user)
        if winnings > 0 and booster_mult > 1.0:
            winnings = int(winnings * booster_mult)
        
        # Обновляем баланс
        economy = self._load_economy()
        economy[user_id]["balance"] -= bet
        economy[user_id]["balance"] += winnings
        
        # Статистика
        if "game_stats" not in economy[user_id]:
            economy[user_id]["game_stats"] = {}
        
        economy[user_id]["game_stats"]["coinflip_played"] = economy[user_id]["game_stats"].get("coinflip_played", 0) + 1
        
        if winnings > bet:
            economy[user_id]["game_stats"]["coinflip_won"] = economy[user_id]["game_stats"].get("coinflip_won", 0) + 1
            economy[user_id]["game_stats"]["total_won"] = economy[user_id]["game_stats"].get("total_won", 0) + (winnings - bet)
            self._add_transaction(user_id, "game_win", winnings - bet, "Монетка (выигрыш)")
        else:
            economy[user_id]["game_stats"]["total_lost"] = economy[user_id]["game_stats"].get("total_lost", 0) + bet
            self._add_transaction(user_id, "game_loss", -bet, "Монетка (проигрыш)")
        
        self._save_economy(economy)
        
        # Результат
        if winnings > 0:
            em = discord.Embed(
                title="🪙 Монетка - ВЫИГРЫШ!",
                description=f"Выпало: **{side_names[result]}**\nВы выбрали: **{side_names[side]}**",
                color=discord.Color.gold()
            )
            em.add_field(name="Ставка", value=f"{bet:,} {self.currency_emoji}", inline=True)
            em.add_field(name="Выигрыш", value=f"+{winnings - bet:,} {self.currency_emoji}", inline=True)
        else:
            em = discord.Embed(
                title="🪙 Монетка - Проигрыш",
                description=f"Выпало: **{side_names[result]}**\nВы выбрали: **{side_names[side]}**",
                color=discord.Color.red()
            )
            em.add_field(name="Потеря", value=f"-{bet:,} {self.currency_emoji}", inline=True)
        
        em.add_field(name="Новый баланс", value=f"{economy[user_id]['balance']:,} {self.currency_emoji}", inline=False)
        
        await interaction.response.send_message(embed=em)
    
    # ==================== ДОСТИЖЕНИЯ И ИСТОРИЯ ====================
    
    @app_commands.command(name="achievements", description="🏆 Просмотр достижений")
    @app_commands.describe(user="Пользователь для просмотра достижений")
    async def achievements(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Показать достижения пользователя"""
        target = user or interaction.user
        user_id = str(target.id)
        user_data = self._get_user_data(user_id)
        
        unlocked_achievements = user_data.get("achievements", {})
        
        # Все достижения
        all_achievements = {
            "first_daily": {"name": "Первый день", "desc": "Получить первую ежедневную награду", "emoji": "🎁"},
            "first_work": {"name": "Трудоголик", "desc": "Поработать первый раз", "emoji": "💼"},
            "first_game": {"name": "Игрок", "desc": "Сыграть первую игру", "emoji": "🎰"},
            "jackpot": {"name": "Джекпот!", "desc": "Сорвать джекпот в слотах", "emoji": "💰"},
            "millionaire": {"name": "Миллионер", "desc": "Накопить 1,000,000 крионов", "emoji": "💎"},
        }
        
        em = discord.Embed(
            title=f"🏆 Достижения {target.display_name}",
            description=f"Разблокировано: {len(unlocked_achievements)}/{len(all_achievements)}",
            color=discord.Color.gold()
        )
        
        for ach_id, ach_info in all_achievements.items():
            if ach_id in unlocked_achievements:
                date = unlocked_achievements[ach_id].get("date", "Неизвестно")
                if date != "Неизвестно":
                    try:
                        dt = datetime.fromisoformat(date)
                        date_str = f"<t:{int(dt.timestamp())}:D>"
                    except:
                        date_str = date
                else:
                    date_str = date
                em.add_field(
                    name=f"✅ {ach_info['emoji']} {ach_info['name']}",
                    value=f"{ach_info['desc']}\n*Получено: {date_str}*",
                    inline=False
                )
            else:
                em.add_field(
                    name=f"🔒 {ach_info['emoji']} {ach_info['name']}",
                    value=ach_info['desc'],
                    inline=False
                )
        
        # Проверяем достижение миллионера
        if user_data.get("balance", 0) >= 1000000:
            self._check_achievement(user_id, "millionaire")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="history", description="📜 История транзакций")
    @app_commands.describe(
        user="Пользователь для просмотра истории",
        limit="Количество транзакций (макс 20)"
    )
    async def history(self, interaction: discord.Interaction, user: Optional[discord.Member] = None, limit: int = 10):
        """Показать историю транзакций"""
        target = user or interaction.user
        user_id = str(target.id)
        user_data = self._get_user_data(user_id)
        
        transactions = user_data.get("transactions", [])
        
        if not transactions:
            await interaction.response.send_message("📜 История транзакций пуста!", ephemeral=True)
            return
        
        # Ограничиваем количество
        limit = min(limit, 20)
        transactions = transactions[:limit]
        
        em = discord.Embed(
            title=f"📜 История транзакций {target.display_name}",
            description=f"Последние {len(transactions)} транзакций",
            color=discord.Color.blue()
        )
        
        # Иконки для типов
        type_icons = {
            "daily": "🎁",
            "weekly": "📅",
            "monthly": "🗓️",
            "work": "💼",
            "transfer": "💸",
            "game_win": "🎰",
            "game_loss": "🎲",
            "purchase": "🛒",
            "admin": "⚙️"
        }
        
        for trans in transactions:
            trans_type = trans.get("type", "unknown")
            amount = trans.get("amount", 0)
            timestamp = trans.get("timestamp", "")
            details = trans.get("details", "")
            
            icon = type_icons.get(trans_type, "📊")
            sign = "+" if amount >= 0 else ""
            
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = f"<t:{int(dt.timestamp())}:R>"
            except:
                time_str = timestamp
            
            em.add_field(
                name=f"{icon} {trans_type.upper()}",
                value=f"{sign}{amount:,} {self.currency_emoji}\n{details}\n*{time_str}*",
                inline=True
            )
        
        await interaction.response.send_message(embed=em)
    
    # ==================== АДМИНИСТРАТИВНЫЕ КОМАНДЫ ====================
    
    @app_commands.command(name="eco-add", description="➕ [ADMIN] Добавить крионы пользователю")
    @app_commands.describe(
        user="Пользователь",
        amount="Количество крионов"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_add(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Добавить крионы пользователю"""
        if amount <= 0:
            await interaction.response.send_message("❌ Сумма должна быть больше 0!", ephemeral=True)
            return
        
        user_id = str(user.id)
        self._update_balance(user_id, amount)
        
        user_data = self._get_user_data(user_id)
        
        em = discord.Embed(
            title="✅ Крионы добавлены",
            description=f"**{amount:,}** {self.currency_emoji} добавлено пользователю {user.mention}",
            color=discord.Color.green()
        )
        em.add_field(name="Новый баланс", value=f"{user_data['balance']:,} {self.currency_emoji}")
        em.set_footer(text=f"Действие выполнил {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="eco-remove", description="➖ [ADMIN] Убрать крионы у пользователя")
    @app_commands.describe(
        user="Пользователь",
        amount="Количество крионов"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_remove(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Убрать крионы у пользователя"""
        if amount <= 0:
            await interaction.response.send_message("❌ Сумма должна быть больше 0!", ephemeral=True)
            return
        
        user_id = str(user.id)
        user_data = self._get_user_data(user_id)
        
        if user_data["balance"] < amount:
            await interaction.response.send_message(
                f"❌ У пользователя всего {user_data['balance']:,} {self.currency_emoji}!",
                ephemeral=True
            )
            return
        
        self._update_balance(user_id, -amount)
        user_data = self._get_user_data(user_id)
        
        em = discord.Embed(
            title="✅ Крионы убраны",
            description=f"**{amount:,}** {self.currency_emoji} убрано у пользователя {user.mention}",
            color=discord.Color.orange()
        )
        em.add_field(name="Новый баланс", value=f"{user_data['balance']:,} {self.currency_emoji}")
        em.set_footer(text=f"Действие выполнил {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="eco-set", description="🎚️ [ADMIN] Установить баланс пользователю")
    @app_commands.describe(
        user="Пользователь",
        amount="Новый баланс"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_set(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Установить баланс пользователю"""
        if amount < 0:
            await interaction.response.send_message("❌ Баланс не может быть отрицательным!", ephemeral=True)
            return
        
        user_id = str(user.id)
        economy = self._load_economy()
        
        if user_id not in economy:
            self._get_user_data(user_id)
            economy = self._load_economy()
        
        economy[user_id]["balance"] = amount
        self._save_economy(economy)
        
        em = discord.Embed(
            title="✅ Баланс установлен",
            description=f"Баланс {user.mention} установлен на **{amount:,}** {self.currency_emoji}",
            color=discord.Color.blue()
        )
        em.set_footer(text=f"Действие выполнил {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="eco-reset", description="🗑️ [ADMIN] Сбросить экономику")
    @app_commands.describe(user="Пользователь для сброса (оставьте пустым чтобы сбросить всех)")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_reset(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Сброс экономики"""
        if user:
            # Сброс конкретного пользователя
            user_id = str(user.id)
            economy = self._load_economy()
            if user_id in economy:
                del economy[user_id]
                self._save_economy(economy)
                await interaction.response.send_message(
                    f"✅ Экономика пользователя {user.mention} сброшена!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ У пользователя {user.mention} нет данных экономики!",
                    ephemeral=True
                )
        else:
            # Сброс всей экономики - требуем подтверждение
            view = ConfirmResetView(self)
            em = discord.Embed(
                title="⚠️ Подтверждение сброса",
                description="Вы уверены, что хотите **сбросить ВСЮ экономику сервера**?\nЭто действие необратимо!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=em, view=view, ephemeral=True)
    
    @app_commands.command(name="shop-add", description="➕ [ADMIN] Добавить товар в магазин")
    @app_commands.describe(
        name="Название товара",
        price="Цена товара",
        item_type="Тип товара",
        role="Роль (только для типа 'role')",
        description="Описание товара"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def shop_add(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        price: int,
        item_type: Literal["role", "item"],
        role: Optional[discord.Role] = None,
        description: Optional[str] = None
    ):
        """Добавить товар в магазин"""
        if price <= 0:
            await interaction.response.send_message("❌ Цена должна быть больше 0!", ephemeral=True)
            return
        
        if item_type == "role" and not role:
            await interaction.response.send_message("❌ Для товара типа 'role' нужно указать роль!", ephemeral=True)
            return
        
        shop_data = self._load_shop()
        
        new_item = {
            "id": shop_data["next_id"],
            "name": name,
            "price": price,
            "type": item_type,
            "description": description or "Без описания"
        }
        
        if item_type == "role" and role:
            new_item["role_id"] = str(role.id)
        
        shop_data["items"].append(new_item)
        shop_data["next_id"] += 1
        self._save_shop(shop_data)
        
        em = discord.Embed(
            title="✅ Товар добавлен",
            description=f"**{name}** добавлен в магазин!",
            color=discord.Color.green()
        )
        em.add_field(name="ID", value=new_item["id"], inline=True)
        em.add_field(name="Цена", value=f"{price:,} {self.currency_emoji}", inline=True)
        em.add_field(name="Тип", value=item_type, inline=True)
        if description:
            em.add_field(name="Описание", value=description, inline=False)
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="shop-remove", description="➖ [ADMIN] Удалить товар из магазина")
    @app_commands.describe(item_id="ID товара")
    @app_commands.checks.has_permissions(administrator=True)
    async def shop_remove(self, interaction: discord.Interaction, item_id: int):
        """Удалить товар из магазина"""
        shop_data = self._load_shop()
        
        # Ищем товар
        item_found = False
        for i, item in enumerate(shop_data["items"]):
            if item["id"] == item_id:
                removed_item = shop_data["items"].pop(i)
                item_found = True
                break
        
        if not item_found:
            await interaction.response.send_message(f"❌ Товар с ID {item_id} не найден!", ephemeral=True)
            return
        
        self._save_shop(shop_data)
        
        em = discord.Embed(
            title="✅ Товар удалён",
            description=f"**{removed_item['name']}** удалён из магазина!",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=em)
    
    @app_commands.command(name="shop-edit", description="✏️ [ADMIN] Изменить товар в магазине")
    @app_commands.describe(
        item_id="ID товара",
        field="Что изменить",
        value="Новое значение"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def shop_edit(
        self, 
        interaction: discord.Interaction, 
        item_id: int,
        field: Literal["name", "price", "description"],
        value: str
    ):
        """Изменить товар в магазине"""
        shop_data = self._load_shop()
        
        # Ищем товар
        item = None
        for shop_item in shop_data["items"]:
            if shop_item["id"] == item_id:
                item = shop_item
                break
        
        if not item:
            await interaction.response.send_message(f"❌ Товар с ID {item_id} не найден!", ephemeral=True)
            return
        
        # Изменяем поле
        if field == "price":
            try:
                price = int(value)
                if price <= 0:
                    await interaction.response.send_message("❌ Цена должна быть больше 0!", ephemeral=True)
                    return
                item["price"] = price
            except ValueError:
                await interaction.response.send_message("❌ Цена должна быть числом!", ephemeral=True)
                return
        else:
            item[field] = value
        
        self._save_shop(shop_data)
        
        em = discord.Embed(
            title="✅ Товар изменён",
            description=f"Поле **{field}** товара **{item['name']}** изменено!",
            color=discord.Color.blue()
        )
        em.add_field(name="Новое значение", value=value)
        
        await interaction.response.send_message(embed=em)

    # Обработка ошибок для admin команд
    @eco_add.error
    @eco_remove.error
    @eco_set.error
    @eco_reset.error
    @shop_add.error
    @shop_remove.error
    @shop_edit.error
    async def admin_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для использования этой команды!",
                ephemeral=True
            )


class ConfirmResetView(discord.ui.View):
    """View для подтверждения сброса экономики"""
    def __init__(self, economy_cog):
        super().__init__(timeout=30)
        self.economy_cog = economy_cog
    
    @discord.ui.button(label="Подтвердить сброс", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Сбрасываем экономику
        with open(self.economy_cog.economy_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        
        em = discord.Embed(
            title="✅ Экономика сброшена",
            description="Вся экономика сервера успешно сброшена!",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=em, view=None)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        em = discord.Embed(
            title="❌ Отменено",
            description="Сброс экономики отменён.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=em, view=None)


async def setup(bot):
    await bot.add_cog(Economy(bot))
