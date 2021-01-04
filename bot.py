import json
import os

import discord
from discord.ext import commands

with open("config.json", 'r') as arq:
    config = json.load(arq)

TOKEN = config["TOKEN"]
PREFIX = config["PREFIX"]
INTENTS = discord.Intents.default()
COGS_FILEPATH = config["COGS_FILEPATH"]
bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}')
    print(f'With ID: {bot.user.id}')
    print(f'Loading Cogs...')
    load_cogs()

def load_cogs():
    for file in os.listdir(COGS_FILEPATH):
        if os.path.splitext(file)[1] == ".py" and os.path.isfile(file):
            path = os.path.join(COGS_FILEPATH, file).replace("/", ".")
            bot.load_extension(path)
            print(f"Cog {file} was loaded!")

bot.run(TOKEN)