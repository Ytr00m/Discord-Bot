import discord, os, youtube_dl, json, asyncio, random
from discord.ext import commands

with open("config.json", 'r') as arq:
    config = json.load(arq)

TOKEN = config["TOKEN"]
PREFIX = config["PREFIX"]
INTENTS = discord.Intents.default()
bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)

ydl_opts = {
    'format': 'bestaudio/best', 'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3'
    }]}
ytdl = youtube_dl.YoutubeDL(ydl_opts)
ytdlFlat = youtube_dl.YoutubeDL({'extract_flat': True, 'quiet': True})
linkPlaylist = "https://www.youtube.com/playlist"
linkVideo = "https://www.youtube.com/watch?v="


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}')
    print(f'With ID: {bot.user.id}')


queue = []
tocando_agora = []


@bot.command()
async def play(ctx, *args):
    if ctx.author.voice is None:
        await ctx.send(f"***{ctx.author.mention}*** não está em nenhum canal de voz!:mute:")
        return
    try:
        await ctx.author.voice.channel.connect()
    except discord.errors.ClientException or discord.ext.commands.errors.CommandInvokeError:
        pass

    if ctx.voice_client.channel != ctx.author.voice.channel:
        await ctx.send(
            f"{ctx.author.mention} **não** está no canal de voz **{ctx.voice_client.channel}**! Excutando mesmo assim.")
    if args[0] == "playlist":
        msg = await ctx.send(f":notes: *Processando playlist* **`{args[1]}`**.")
        await play_playlist(ctx, msg, args[1])

        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            try:
                await play(ctx, queue.pop(0))
            except IndexError:
                pass
            return
        return
    if type(args[0]) != dict:
        if args[0].startswith(linkPlaylist):
            videos_playlist = extrai_playlist(args[0])
            for i in range(len(videos_playlist)):
                if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                    await play(ctx, linkVideo + videos_playlist[i]['url'])
                else:
                    queue.append(videos_playlist[i])
            return
    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
        try:
            info = ytdl.extract_info(args[0], download=False)
            tocando_agora.append(info)
            await ctx.message.add_reaction("✅")
            print(f"Tocando agora: {tocando_agora[0]['title']} [{':'.join(duracao(tocando_agora[0]['duration']))}].")

            ctx.voice_client.play(discord.FFmpegPCMAudio(info['url']), after=lambda e: next_song(ctx))
            return
        except TypeError:
            info = ytdl.extract_info(linkVideo + args[0]['url'], download=False)
            tocando_agora.append(args[0])
            print(f"Tocando agora: {tocando_agora[0]['title']} [{':'.join(duracao(tocando_agora[0]['duration']))}].")
            ctx.voice_client.play(discord.FFmpegPCMAudio(info['url']), after=lambda e: next_song(ctx))
            return
    else:
        info = ytdlFlat.extract_info(args[0], download=False)
        queue.append(info)
        await ctx.send(f"{ctx.author.mention} **{info['title']}** adicicionada a fila! :white_check_mark:")
        await ctx.message.add_reaction("✅")
        return


@bot.command()
async def skip(ctx):
    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        if len(queue) == 0:
            await stop(ctx)
            return
        await ctx.send(f":next_track: **{tocando_agora[0]['title']}** *pulada!*")
        print(f"{tocando_agora[0]['title']} pulada.")
        ctx.voice_client.stop()
        await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
        return
    await ctx.send("*Não tem nenhuma musica tocando!*:x:")


@bot.command()
async def stop(ctx):
    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        queue.clear()
        tocando_agora.clear()
        ctx.voice_client.stop()
        await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
        await ctx.send(":stop_button: *O player foi parado e a fila esvaziada!*")
        print("Player parado e fila esvaziada.")
        return

    await ctx.send("*Não tem nenhuma musica tocando!*:x:")


@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
        await ctx.send(f":play_pause: **{tocando_agora[0]['title']}** *pausada!*")
        print("Player pausado.")
        return

    await ctx.send("*Não tem nenhuma musica tocando!*:x:")


@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
        await ctx.send(f":play_pause: **{tocando_agora[0]['title']}** tocando novamente!")
        print("Player despausado")
        return

    await ctx.send("*Não tem nenhuma musica pausada!*:x:")


@bot.command()
async def tocando(ctx):
    try:
        if ctx.voice_client.is_playing():
            tempo = duracao(tocando_agora[0]['duration'])
            duration_song = ':'.join(tempo)
            await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(
                f":musical_note: **{tocando_agora[0]['title']}** **`[{duration_song}]`**")
            return
        await ctx.send("*Não tem nenhuma musica tocando!*")
    except AttributeError:
        await ctx.send("*Não tem nenhuma musica tocando!*")


@bot.command()
async def fila(ctx, *args):
    if len(queue) == 0:
        await tocando(ctx)
    else:
        try:
            arg = args[0]
        except IndexError:
            arg = 1

        embeds = cria_embeds(queue)
        tempo = duracao(tocando_agora[0]['duration'])
        duration_song = ':'.join(tempo)
        pagina = arg
        try:
            msg = await ctx.send(
                f":musical_note: ***`{tocando_agora[0]['title']}`*** `[{duration_song}]`\n:notes:**`{len(queue)}`** na fila:",
                embed=discord.Embed(description=embeds[int(pagina) - 1] + f"Pagina {pagina}/{len(embeds)}"))
            await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
        except IndexError:
            msg = await ctx.send("Pagina inexistente!")
            await msg.add_reaction("❌")
            return


@bot.command()
async def playlists(ctx):
    playlists = os.listdir("Musica/Playlists")
    text = "`" + '` `'.join(playlists).replace(".txt", "") + "`"
    msg = await ctx.send(f"*Playlists:* **{text}**")
    await msg.add_reaction(random.choice(await ctx.guild.fetch_emojis()))


@bot.command()
async def ajuda(ctx):
    await ctx.send(f"{ctx.author.mention}",
                   embed=discord.Embed(title=
                                       "**Comandos**", description=
                                       "**Musica:**\n" +
                                       f"\n**`{PREFIX}play:`**\n" +
                                       f"\t{PREFIX}play <**`url`**>: Toca uma música a partir do **`url`** dado, se estiver alguma musica tocando, adiciona á fila. Se o link for uma **`playlist`** do youtube, extrai todos os videos dela e adiciona á fila.\n" +
                                       f"\t{PREFIX}play playlist <**`nome da playlist`**>: Toca as músicas da playlist, se alguma estiver tocando, adiciona toda a playlist á fila.\n" +
                                       f"\n**`{PREFIX}skip:`** Pula a música atual ou para de tocar se a fila estiver vazia.\n" +
                                       f"**`{PREFIX}stop:`** Para a música atual e esvazia a fila.\n" +
                                       f"**`{PREFIX}pause:`** Pausa a música atual.\n" +
                                       f"**`{PREFIX}resume:`** Despausa a música pausada.\n" +
                                       f"**`{PREFIX}tocando:`** Exibe a música atual.\n" +
                                       f"**`{PREFIX}fila`** <**`pagina`**>: exibe a **`pagina`** da fila, se nenhuma pagina for especificada exibe a primeira\n" +
                                       f"**`{PREFIX}playlists:`** Exibe as playlists diponíveis."))


def next_song(ctx):
    tocando_agora.clear()
    if len(queue) > 0:
        asyncio.run(play(ctx, queue.pop(0)))


async def play_playlist(ctx, mensagem_do_bot, playlist_nome):
    try:
        print(f"Processando playlist {playlist_nome}.")
        with open(f"Musica/Playlists/{playlist_nome}.txt", "r") as arq:
            playlist = arq.readlines()
    except OSError:
        print(f"Erro: A playlist {playlist_nome} não existe.")
        await mensagem_do_bot.add_reaction("❌")
        await ctx.send(f"{ctx.author.mention}, *A playlist* **`{playlist_nome}`** *não existe!*")
        return
    for i in range(len(playlist)):
        if playlist[i].startswith(linkPlaylist):
            videos_playlist = extrai_playlist(playlist[i])
            for i in range(len(videos_playlist)):
                if not ctx.voice_client.is_playing():
                    await play(ctx, videos_playlist[i]['url'])
                else:
                    queue.append(videos_playlist[i])
        else:
            info = ytdlFlat.extract_info(videos_playlist[i], download=False)
            queue.append(info)

    await mensagem_do_bot.add_reaction("✅")


def duracao(duration):
    tempo = []
    dias = duration // 86400
    segundos_rest = duration % 86400
    horas = segundos_rest // 3600
    segundos_rest = segundos_rest % 3600
    minutos = segundos_rest // 60
    segundos_rest = segundos_rest % 60
    if dias > 0:
        if dias < 10:
            dias = f"0{str(int(dias))}"
        tempo.append(dias)
    if horas > 0:
        if horas < 10:
            horas = f"0{int(str(horas))}"
        tempo.append(str(int(horas)))
    tempo.append(f"0{str(int(minutos))}" if minutos < 10 else str(int(minutos)))
    tempo.append(f"0{str(int(segundos_rest))}" if segundos_rest < 10 else str(int(segundos_rest)))
    return tempo


def cria_embeds(queue):
    tamanho_max = 10
    count = 1
    songs = ""
    embeds = []

    for i in queue:
        tempo = duracao(queue[count - 1]['duration'])
        duration_song = ':'.join(tempo)
        songs += f"`{count}.` [**`{queue[count - 1]['title']}`**]({linkVideo + queue[count - 1]['url']})  `[{duration_song}]`\n"
        count += 1
        if count % tamanho_max == 1 or count == len(queue) + 1:
            embeds.append(songs)
            songs = ""

    return embeds


def extrai_playlist(playlist_url):
    ytd = youtube_dl.YoutubeDL({'extract_flat': True, 'playlistrandom': True, 'quiet': True})
    result = ytd.extract_info(playlist_url, download=False)
    playlist = []
    for i in range(len(result['entries'])):
        playlist.append(result['entries'][i])

    return playlist


bot.run(TOKEN)
