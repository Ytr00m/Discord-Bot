import discord, os, youtube_dl, json, asyncio, random
from discord.ext import commands

with open("config.json", 'r') as arq:
    config = json.load(arq)

TOKEN = config["TOKEN"]
PREFIX = config["PREFIX"]
COGS_FILEPATH = config["COGS_FILEPATH"]
INTENTS = discord.Intents.default()
bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)


def load_cogs():
    for file in os.listdir(COGS_FILEPATH):
        path = os.path.join(COGS_FILEPATH, file)
        path = os.path.relpath(path, os.curdir)
        if os.path.splitext(file)[1] == ".py" and os.path.isfile(path):
            try:
                bot.load_extension(path.replace("/", ".")[:-3])
            except (commands.ExtensionNotFound, commands.ExtensionError) as err:
                print(f"Failed to load {path} cog!")
                raise err
            else:
                print(f"Cog {path} was loaded!")


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}')
    print(f'With ID: {bot.user.id}')
    print('Loading Cogs...')
    load_cogs()
    print("Bot ready ✅")

bot.run(TOKEN)
