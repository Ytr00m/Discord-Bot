import discord
import youtube_dl
import asyncio
import random
import os
from discord.ext import commands


def setup(bot):
    bot.add_cog(MusicCog(bot))


class MusicCog(commands.Cog, name='Musica'):
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.ydl_opts = {
            'format': 'bestaudio/best', 'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3'
            }]}
        self.ytdl = youtube_dl.YoutubeDL(self.ydl_opts)
        self.ytdlFlat = youtube_dl.YoutubeDL({'extract_flat': True, 'quiet': True})
        self.linkPlaylist = "https://www.youtube.com/playlist"
        self.linkVideo = "https://www.youtube.com/watch?v="
        self.queue = []
        self.tocando_agora = []

    @commands.command()
    async def play(self, ctx, *args):
        if args[0] == 0:
            for i in self.bot.guilds:
                if i == ctx.guild:
                    await asyncio.sleep(5)
                    await i.change_voice_state(channel=None)
                    return
        if ctx.voice_client is None:
            try:
                await ctx.author.voice.channel.connect()
            except AttributeError:
                await ctx.send(f"***{ctx.author.mention}*** não está em nenhum canal de voz!:mute:")
                return

        if args[0] == "playlist":
            msg = await ctx.send(f":notes: *Processando playlist* **`{args[1]}`**.")
            await self.play_playlist(ctx, msg, args[1])

            if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                try:
                    await self.play(ctx, self.queue.pop(0))
                except IndexError:
                    pass
                return
            return
        if type(args[0]) != dict:
            if args[0].startswith(self.linkPlaylist):
                videos_playlist = self.extrai_playlist(args[0])
                for i in range(len(videos_playlist)):
                    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                        await self.play(ctx, self.linkVideo + videos_playlist[i]['url'])
                    else:
                        self.queue.append(videos_playlist[i])
                return
        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            try:
                info = self.ytdl.extract_info(args[0], download=False)
                self.tocando_agora.append(info)
                await ctx.message.add_reaction("✅")
                print(
                    f"Tocando agora: {self.tocando_agora[0]['title']} [{':'.join(self.duracao(self.tocando_agora[0]['duration']))}].")

                ctx.voice_client.play(discord.FFmpegPCMAudio(info['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10'),  after=lambda e: self.next_song(ctx))
                return
            except TypeError:
                info = self.ytdl.extract_info(self.linkVideo + args[0]['url'], download=False)
                self.tocando_agora.append(args[0])
                print(
                    f"Tocando agora: {self.tocando_agora[0]['title']} [{':'.join(self.duracao(self.tocando_agora[0]['duration']))}].")
                ctx.voice_client.play(discord.FFmpegPCMAudio(info['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10'), after=lambda e: self.next_song(ctx))
                return
        else:
            info = self.ytdlFlat.extract_info(args[0], download=False)
            self.queue.append(info)
            await ctx.send(f"{ctx.author.mention} **{info['title']}** adicicionada a fila! :white_check_mark:")
            await ctx.message.add_reaction("✅")
            return

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            if len(self.queue) == 0:
                await self.stop(ctx)
                return
            await ctx.send(f":next_track: **{self.tocando_agora[0]['title']}** *pulada!*")
            print(f"{self.tocando_agora[0]['title']} pulada.")
            ctx.voice_client.stop()
            await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            return
        await ctx.send("*Não tem nenhuma musica tocando!*:x:")

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            self.queue.clear()
            self.tocando_agora.clear()
            ctx.voice_client.stop()
            await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(":stop_button: *O player foi parado e a fila esvaziada!*")
            print("Player parado e fila esvaziada.")
            return

        await ctx.send("*Não tem nenhuma musica tocando!*:x:")

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(f":play_pause: **{self.tocando_agora[0]['title']}** *pausada!*")
            print("Player pausado.")
            return

        await ctx.send("*Não tem nenhuma musica tocando!*:x:")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(f":play_pause: **{self.tocando_agora[0]['title']}** tocando novamente!")
            print("Player despausado")
            return

        await ctx.send("*Não tem nenhuma musica pausada!*:x:")

    @commands.command()
    async def tocando(self, ctx):
        try:
            if ctx.voice_client.is_playing():
                tempo = self.duracao(self.tocando_agora[0]['duration'])
                duration_song = ':'.join(tempo)
                await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
                await ctx.send(
                    f":musical_note: **{self.tocando_agora[0]['title']}** **`[{duration_song}]`**")
                return
            await ctx.send("*Não tem nenhuma musica tocando!*")
        except AttributeError:
            await ctx.send("*Não tem nenhuma musica tocando!*")

    @commands.command()
    async def fila(self, ctx, *args):
        if len(self.queue) == 0:
            await self.tocando(ctx)
        else:
            try:
                arg = args[0]
            except IndexError:
                arg = 1

            embeds = self.cria_embeds(self.queue)
            tempo = self.duracao(self.tocando_agora[0]['duration'])
            duration_song = ':'.join(tempo)
            pagina = arg
            try:
                msg = await ctx.send(
                    f":musical_note: ***`{self.tocando_agora[0]['title']}`*** `[{duration_song}]`\n:notes:**`{len(self.queue)}`** na fila:",
                    embed=discord.Embed(description=embeds[int(pagina) - 1] + f"Pagina {pagina}/{len(embeds)}"))
                await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            except IndexError:
                msg = await ctx.send("Pagina inexistente!")
                await msg.add_reaction("❌")
                return

    @commands.command()
    async def playlists(self, ctx):
        playlists = os.listdir("Musica/Playlists")
        text = "`" + '` `'.join(playlists).replace(".txt", "") + "`"
        msg = await ctx.send(f"*Playlists:* **{text}**")
        await msg.add_reaction(random.choice(await ctx.guild.fetch_emojis()))

    @commands.command()
    async def ajuda(self, ctx):
        await ctx.send(f"{ctx.author.mention}",
                       embed=discord.Embed(title=
                                           "**Comandos**", description=
                                           "**Musica:**\n" +
                                           f"\n**`{self.bot.command_prefix}play:`**\n" +
                                           f"\t{self.bot.command_prefix}play <**`url`**>: Toca uma música a partir do **`url`** dado, se estiver alguma musica tocando, adiciona á fila. Se o link for uma **`playlist`** do youtube, extrai todos os videos dela e adiciona á fila.\n" +
                                           f"\t{self.bot.command_prefix}play playlist <**`nome da playlist`**>: Toca as músicas da playlist, se alguma estiver tocando, adiciona toda a playlist á fila.\n" +
                                           f"\n**`{self.bot.command_prefix}skip:`** Pula a música atual ou para de tocar se a fila estiver vazia.\n" +
                                           f"**`{self.bot.command_prefix}stop:`** Para a música atual e esvazia a fila.\n" +
                                           f"**`{self.bot.command_prefix}pause:`** Pausa a música atual.\n" +
                                           f"**`{self.bot.command_prefix}resume:`** Despausa a música pausada.\n" +
                                           f"**`{self.bot.command_prefix}tocando:`** Exibe a música atual.\n" +
                                           f"**`{self.bot.command_prefix}fila`** <**`pagina`**>: exibe a **`pagina`** da fila, se nenhuma pagina for especificada exibe a primeira\n" +
                                           f"**`{self.bot.command_prefix}playlists:`** Exibe as playlists diponíveis."))

    def next_song(self, ctx):
        self.tocando_agora.clear()
        asyncio.run(self.play(ctx, self.queue.pop(0) if len(self.queue) > 0 else 0))

    async def play_playlist(self, ctx, mensagem_do_bot, playlist_nome):
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
            if playlist[i].startswith(self.linkPlaylist):
                videos_playlist = self.extrai_playlist(playlist[i])
                for i in range(len(videos_playlist)):
                    if not ctx.voice_client.is_playing():
                        await self.play(ctx, videos_playlist[i]['url'])
                    else:
                        self.queue.append(videos_playlist[i])
            else:
                info = self.ytdlFlat.extract_info(playlist[i], download=False)
                self.queue.append(info)

        await mensagem_do_bot.add_reaction("✅")

    def duracao(self, duration):
        tempo = []
        dias = duration // 86400
        segundos_rest = duration % 86400
        horas = segundos_rest // 3600
        segundos_rest %= 3600
        minutos = segundos_rest // 60
        segundos_rest %= 60
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

    def cria_embeds(self, queue):
        tamanho_max = 10
        count = 1
        songs = ""
        embeds = []

        for i in queue:
            tempo = self.duracao(queue[count - 1]['duration'])
            duration_song = ':'.join(tempo)
            songs += f"`{count}.` [**`{queue[count - 1]['title']}`**]({self.linkVideo + self.queue[count - 1]['url']})  `[{duration_song}]`\n"
            count += 1
            if count % tamanho_max == 1 or count == len(queue) + 1:
                embeds.append(songs)
                songs = ""

        return embeds

    def extrai_playlist(self, playlist_url):
        ytd = youtube_dl.YoutubeDL({'extract_flat': True, 'playlistrandom': True, 'quiet': True})
        result = ytd.extract_info(playlist_url, download=False)
        playlist = []
        for i in range(len(result['entries'])):
            playlist.append(result['entries'][i])

        return playlist
