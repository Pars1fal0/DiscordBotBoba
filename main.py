import discord
from discord.ext import commands
import os
from dotenv import load_dotenv  # <— добавили

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.presences = True
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents, help_command=None)

    async def setup_hook(self):
        # Автозагрузка когов из ./cogs (если папка есть)
        if os.path.isdir('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f'✅ Загружен ког: {filename[:-3]}')
                    except Exception as e:
                        print(f'❌ Ошибка загрузки {filename}: {e}')


bot = MyBot()

@bot.event
async def on_ready():
    print(f'🤖 Бот {bot.user} запущен!')
    print(f'📊 Подключен к {len(bot.guilds)} серверам')
    
    # Синхронизация команд только при явном указании через переменную окружения
    sync_commands = os.getenv('SYNC_COMMANDS', 'false').lower() == 'true'
    
    if sync_commands:
        print('⚙️ Начинается синхронизация команд...')
        try:
            synced = await bot.tree.sync()
            print(f'✅ Синхронизировано {len(synced)} команд')
        except discord.HTTPException as e:
            if e.status == 429:
                print(f'⚠️ Rate limit! Попробуйте синхронизировать команды позже.')
                print(f'   Повторная попытка через {e.retry_after:.0f} секунд')
            else:
                print(f'❌ Ошибка синхронизации: {e}')
        except Exception as e:
            print(f'❌ Ошибка синхронизации: {e}')
    else:
        print('ℹ️ Синхронизация команд отключена (SYNC_COMMANDS=false)')
        print('   Для синхронизации команд установите SYNC_COMMANDS=true в .env')


@bot.command(name='sync')
async def sync_commands(ctx):
    """Синхронизация slash-команд глобально (доступно только владельцу бота)"""
    # Проверка владельца через OWNER_ID из .env
    owner_id = os.getenv('OWNER_ID')
    if not owner_id:
        await ctx.send('❌ OWNER_ID не установлен в .env файле.')
        return
    
    try:
        owner_id = int(owner_id)
    except ValueError:
        await ctx.send('❌ OWNER_ID в .env должен быть числом.')
        return
    
    if ctx.author.id != owner_id:
        await ctx.send('❌ Эта команда доступна только владел!ыьцу бота.')
        return
    
    try:
        await ctx.send('⚙️ Начинается глобальная синхронизация команд...')
        synced = await bot.tree.sync()
        await ctx.send(f'✅ Синхронизировано {len(synced)} команд глобально!')
    except discord.HTTPException as e:
        if e.status == 429:
            await ctx.send(f'⚠️ Rate limit! Попробуйте синхронизировать команды позже.\n'
                          f'Повторная попытка возможна через {e.retry_after:.0f} секунд')
        else:
            await ctx.send(f'❌ Ошибка синхронизации: {e}')
    except Exception as e:
        await ctx.send(f'❌ Ошибка синхронизации: {e}')


@bot.command(name='syncguild')
async def sync_guild_commands(ctx):
    """Синхронизация slash-команд только для текущей гильдии (доступно только владельцу бота)"""
    # Проверка владельца через OWNER_ID из .env
    owner_id = os.getenv('OWNER_ID')
    if not owner_id:
        await ctx.send('❌ OWNER_ID не установлен в .env файле.')
        return
    
    try:
        owner_id = int(owner_id)
    except ValueError:
        await ctx.send('❌ OWNER_ID в .env должен быть числом.')
        return
    
    if ctx.author.id != owner_id:
        await ctx.send('❌ Эта команда доступна только владельцу бота.')
        return
    
    try:
        await ctx.send('⚙️ Начинается синхронизация команд для этого сервера...')
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f'✅ Синхронизировано {len(synced)} команд для этого сервера!')
    except discord.HTTPException as e:
        if e.status == 429:
            await ctx.send(f'⚠️ Rate limit! Попробуйте синхронизировать команды позже.\n'
                          f'Повторная попытка возможна через {e.retry_after:.0f} секунд')
        else:
            await ctx.send(f'❌ Ошибка синхронизации: {e}')
    except Exception as e:
        await ctx.send(f'❌ Ошибка синхронизации: {e}')


if __name__ == "__main__":
    load_dotenv()  # <— читаем .env
    token = os.getenv("DISCORD_TOKEN")
    owner_id = os.getenv('OWNER_ID')

    if not token or not isinstance(token, str) or token.strip() == "":
        raise RuntimeError(
            "DISCORD_TOKEN не найден. Укажи токен в .env или переменной окружения."
        )
    
    # Устанавливаем OWNER_ID для команд @commands.is_owner()
    if owner_id:
        try:
            bot.owner_id = int(owner_id)
            print(f'🔑 Owner ID установлен: {bot.owner_id}')
        except ValueError:
            print('⚠️ OWNER_ID должен быть числом. Команды !sync и !syncguild будут недоступны.')
    else:
        print('⚠️ OWNER_ID не найден в .env. Команды !sync и !syncguild будут недоступны.')

    bot.run(token)
