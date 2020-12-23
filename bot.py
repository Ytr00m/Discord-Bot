import discord, os
import Musica.music
from discord.ext import commands

TOKEN = 'Nzg0MTQxOTg5ODg4OTE3NTI1.X8k_Iw.l8XTJ-aWx0NhCaebGgx3n42ditM'
PREFIX = '!'
INTENTS = discord.Intents.default()
bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}')
    print(f'With ID: {bot.user.id}')


@bot.command()
async def play(ctx, arg):
    try:
        await ctx.author.voice.channel.connect()
    except discord.errors.ClientException or discord.ext.commands.errors.CommandInvokeError:
        pass

    if not ctx.voice_client.is_playing():
        await Musica.music._play(ctx, arg)

    elif os.path.exists("Musica/Playlists/fila.txt"):
        with open("Musica/Playlists/fila.txt", 'a') as arq:
            arq.write(arg + "\n")

    else:
        with open("Musica/Playlists/fila.txt", 'w') as arq:
            arq.write(arg + "\n")


bot.run(TOKEN)
