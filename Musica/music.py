import discord, youtube_dl, asyncio, os
from discord.ext import commands

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
    }]}
ytdl = youtube_dl.YoutubeDL(ydl_opts)


@commands.command()
async def _play(ctx, musica):
    if os.path.exists("Playlists/fila.txt"):
        with open("Playlists/fila.txt", 'r') as arq:
            queue = arq.readlines()

    else:
        info = ytdl.extract_info(musica, download=False)
        await ctx.voice_client.play(discord.FFmpegPCMAudio(info['url']))
    await ctx.voice_client.play(discord.FFmpegPCMAudio(info['url']))
