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
        self.queue = {}
        self.tocando_agora = {}
        self.looop = False

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):

        if member == self.bot.user:
            
            if before.channel:
                print(f"Desconnectado do canal {before.channel}")
                member.guild.change_voice_state(channel=None)
            if after.channel:
                print(f"Connectado ao canal {after.channel} do(a) {member.guild}")

    @commands.command(help="Toca uma música, playlist do youtube ou uma playlist salva.")
    async def play(self, ctx: commands.Context, *args):

        if not ctx.guild.id in self.tocando_agora:
            self.tocando_agora[ctx.guild.id] = []

        if not ctx.guild.id in self.queue:
            self.queue[ctx.guild.id] = []

        if args[0] == 0:

            for i in self.bot.guilds:

                if i == ctx.guild:
                    await asyncio.sleep(5)
                    await i.change_voice_state(channel=None)
                    
                    return

        if ctx.guild.voice_client is None:

            try:
                await ctx.author.voice.channel.connect(reconnect=True)

            except AttributeError:
                await ctx.send(f"***{ctx.author.mention}*** não está em nenhum canal de voz!:mute:")
                
                return

        if args[0] == "playlist":
            msg = await ctx.send(f":notes: *Processando playlist* **`{args[1]}`**.")
            await self.play_playlist(ctx, msg, args[1])

            if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():

                try:
                    await self.play(ctx, self.queue[ctx.guild.id].pop(0))

                except IndexError:
                    pass

            return

        if type(args[0]) != dict:

            if args[0].startswith(self.linkPlaylist):
                videos_playlist = self.extrai_playlist(args[0])

                for i in range(len(videos_playlist)):

                    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                        await self.play(ctx, self.linkVideo + videos_playlist[i]['url'])
                        
                    else:
                        self.queue[ctx.guild.id].append(videos_playlist[i])
                
                return

        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():

            try:
                info = self.ytdl.extract_info(args[0], download=False)

                if not self.looop:
                    self.tocando_agora[ctx.guild.id].append(info)
                    
                await ctx.message.add_reaction("✅")
                if not self.looop:
                    print(
                        f"Tocando agora: {self.tocando_agora[ctx.guild.id][0]['title']} [{':'.join(self.duracao(self.tocando_agora[ctx.guild.id][0]['duration']))}].")

                ctx.voice_client.play(discord.FFmpegPCMAudio(info['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10'),  after=lambda e: self.next_song(ctx))
                
                return

            except TypeError:
                info = self.ytdl.extract_info(self.linkVideo + args[0]['url'], download=False)
                
                if not self.looop:
                    self.tocando_agora[ctx.guild.id].append(args[0])
                    print(
                        f"Tocando agora: {self.tocando_agora[ctx.guild.id][0]['title']} [{':'.join(self.duracao(self.tocando_agora[ctx.guild.id][0]['duration']))}].")

                ctx.voice_client.play(discord.FFmpegPCMAudio(info['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10'), after=lambda e: self.next_song(ctx))
                
                return
        else:
            info = self.ytdlFlat.extract_info(args[0], download=False)
            info['url'] = info['webpage_url'].replace(self.linkVideo, "")
            if not self.looop:
                self.queue[ctx.guild.id].append(info)

            await ctx.send(f"{ctx.author.mention} **{info['title']}** adicicionada a fila! :white_check_mark:")
            await ctx.message.add_reaction("✅")

            return

    @commands.command(help="Pula a música atual.")
    async def skip(self, ctx: commands.Context):

        if self.looop:
            await ctx.send("Comando não disponivel no modo loop.")

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            if len(self.queue[ctx.guild.id]) == 0:
                await self.stop(ctx)

                return

            await ctx.send(f":next_track: **{self.tocando_agora[ctx.guild.id][0]['title']}** *pulada!*")
            print(f"{self.tocando_agora[ctx.guild.id][0]['title']} pulada.")
            ctx.voice_client.stop()
            if await ctx.guild.fetch_emojis():
            	await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))

            return

        await ctx.send("*Não tem nenhuma musica tocando!*:x:")

    @commands.command(help="Para a música atual e esvazia a fila.")
    async def stop(self, ctx: commands.Context):

        if self.looop:
            self.looop = False

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            self.queue[ctx.guild.id].clear()
            self.tocando_agora[ctx.guild.id].clear()
            ctx.voice_client.stop()
            if await ctx.guild.fetch_emojis():
            	await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(":stop_button: *O player foi parado e a fila esvaziada!*")
            print("Player parado e fila esvaziada.")

            return

        await ctx.send("*Não tem nenhuma musica tocando!*:x:")

    @commands.command(help="Pausa a música atual.")
    async def pause(self, ctx: commands.Context):

        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            if await ctx.guild.fetch_emojis():
            	await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(f":play_pause: **{self.tocando_agora[ctx.guild.id][0]['title']}** *pausada!*")
            print("Player pausado.")

            return

        await ctx.send("*Não tem nenhuma musica tocando!*:x:")

    @commands.command(help="Despausa a música pausada.")
    async def resume(self, ctx: commands.Context):

        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            if await ctx.guild.fetch_emojis():
            	await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(f":play_pause: **{self.tocando_agora[ctx.guild.id][0]['title']}** tocando novamente!")

            if self.looop:
                await ctx.send(f"**Aviso! Modo loop ativado.**\n**Use** **´{self.bot.command_prefix}stop´** **para parar o loop.**")

            print("Player despausado")

            return

        await ctx.send("*Não tem nenhuma musica pausada!*:x:")

    @commands.command(help="Exibe a música atual.")
    async def tocando(self, ctx: commands.Context):
        try:

            if ctx.voice_client.is_playing():
                tempo = self.duracao(self.tocando_agora[ctx.guild.id][0]['duration'])
                duration_song = ':'.join(tempo)
                await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
                await ctx.send(
                    f":musical_note: **{self.tocando_agora[ctx.guild.id][0]['title']}** **`[{duration_song}]`**")

                if self.looop:
                    await ctx.send(f"**Aviso! Modo loop ativado.**\n**Use** **`{self.bot.command_prefix}stop`** **para parar o loop.**")

                return

            await ctx.send("*Não tem nenhuma musica tocando!*")

        except AttributeError:
            await ctx.send("*Não tem nenhuma musica tocando!*")

    @commands.command(help="Exibe a fila.")
    async def fila(self, ctx: commands.Context, *args):

        if self.looop:
            await self.tocando(ctx)
            
            return

        if not ctx.guild.id in self.queue:
            await self.tocando(ctx)

        else:

            if len(self.queue[ctx.guild.id]) == 0:
                await self.tocando(ctx)
                return

            try:
                arg = args[0]

            except IndexError:
                arg = 1

            embeds = self.cria_embeds(self.queue[ctx.guild.id], ctx)
            tempo = self.duracao(self.tocando_agora[ctx.guild.id][0]['duration'])
            duration_song = ':'.join(tempo)
            pagina = arg

            try:
                msg = await ctx.send(
                    f":musical_note: ***`{self.tocando_agora[ctx.guild.id][0]['title']}`*** `[{duration_song}]`\n:notes:**`{len(self.queue[ctx.guild.id])}`** na fila:",
                    embed=discord.Embed(description=embeds[int(pagina) - 1] + f"Pagina {pagina}/{len(embeds)}"))
                await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))

            except IndexError:
                msg = await ctx.send("Pagina inexistente!")
                await msg.add_reaction("❌")

                return

    @commands.command(help="Exibe as playlists salvas.")
    async def playlists(self, ctx: commands.Context):
        playlists = os.listdir("Musica/Playlists")
        text = "`" + '` `'.join(playlists).replace(".txt", "") + "`"
        msg = await ctx.send(f"*Playlists:* **{text}**")
        if await ctx.guild.fetch_emojis():
        	await msg.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
    
    @commands.command(help="Toca uma música em loop.")
    async def loop(self, ctx: commands.Context, url: str):

        if self.looop:
            await ctx.send("Já há uma música em loop")

        if ctx.voice_client is not None:
            await ctx.send("Pare o player e esvazie a fila para usar esta função.")

            return

        self.looop = True
        info = self.ytdlFlat.extract_info(url, download=False)
        info['url'] = info['webpage_url'].replace(self.linkVideo, "")
        self.queue[ctx.guild.id] = []
        self.tocando_agora[ctx.guild.id] = []
        self.queue[ctx.guild.id].append(info)
        self.tocando_agora[ctx.guild.id].append(info)
        print(f"Tocando agora: {self.tocando_agora[ctx.guild.id][0]['title']} [{':'.join(self.duracao(self.tocando_agora[ctx.guild.id][0]['duration']))}]. MODO LOOP ATIVADO!!")
        await self.play(ctx, url)


    @commands.command(help="Disponível em breve.")
    async def add_playlist(self):
        pass

    def next_song(self, ctx: commands.Context):

        if not self.looop:
            self.tocando_agora[ctx.guild.id].clear()
            self.tocando_agora.pop(ctx.guild.id)

            if len(self.queue[ctx.guild.id]) == 0:
                self.queue.pop(ctx.guild.id)
            asyncio.run(self.play(ctx, self.queue[ctx.guild.id].pop(0) if ctx.guild.id in self.queue else 0))
        else:
            asyncio.run(self.play(ctx, self.queue[ctx.guild.id][0]))

    async def play_playlist(self, ctx: commands.Context, mensagem_do_bot: discord.Message, playlist_nome):

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
                        self.queue[ctx.guild.id].append(videos_playlist[i])

            else:
                info = self.ytdlFlat.extract_info(playlist[i], download=False)
                self.queue[ctx.guild.id].append(info)

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

    def cria_embeds(self, queue: dict, ctx: commands.Context):
        tamanho_max = 10
        count = 1
        songs = ""
        embeds = []

        for i in self.queue[ctx.guild.id]:
            tempo = self.duracao(i['duration'])
            duration_song = ':'.join(tempo)
            songs += f"`{count}.` [**`{i['title']}`**]({self.linkVideo + i['url']})  `[{duration_song}]`\n"
            count += 1

            if count % tamanho_max == 1 or count == len(self.queue[ctx.guild.id]) + 1:
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
