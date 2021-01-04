import os, asyncio, random
import youtube_dl
import discord
from discord.ext import commands

PREFIX = "!"


def setup(bot: commands.Bot):
    bot.add_cog(MusicCog(bot))


class MusicCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queue = []
        self.tocando_agora = []

        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        }
        self.ytdl = youtube_dl.YoutubeDL(self.ydl_opts)

    @commands.command()
    async def play(self, ctx, *args):
        if ctx.author.voice is None:
            await ctx.send(f"***{ctx.author.mention}*** não está em nenhum canal de voz!:mute:")
            return
        try:
            await ctx.author.voice.channel.connect()
        except discord.errors.ClientException or discord.ext.commands.errors.CommandInvokeError:
            pass

        if ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.send(f"{ctx.author.mention} **não** está no canal de voz **{ctx.voice_client.channel}**!")
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
        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            try:
                info = self.ytdl.extract_info(args[0], download=False)
                self.tocando_agora.append(info)
                await ctx.message.add_reaction("✅")
                print(
                    f"Tocando agora: {self.tocando_agora[0]['title']} [{':'.join(self.duracao(self.tocando_agora[0]['duration']))}].")

                ctx.voice_client.play(discord.FFmpegPCMAudio(info['url']), after=lambda e: self.next_song(ctx))
                return
            except TypeError:
                self.tocando_agora.append(args[0])
                print(
                    f"Tocando agora: {self.tocando_agora[0]['title']} [{':'.join(self.duracao(self.tocando_agora[0]['duration']))}].")
                ctx.voice_client.play(discord.FFmpegPCMAudio(args[0]['url']), after=lambda e: self.next_song(ctx))
                return
        else:
            info = self.ytdl.extract_info(args[0], download=False)
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
            ctx.voice_client.stop()
            await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(f":next_track: **{self.tocando_agora[0]['title']}** *pulada!*")
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
            return

        await ctx.send("*Não tem nenhuma musica tocando!*:x:")

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(f":play_pause: **{self.tocando_agora[0]['title']}** *pausada!*")
            return

        await ctx.send("*Não tem nenhuma musica tocando!*:x:")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.message.add_reaction(random.choice(await ctx.guild.fetch_emojis()))
            await ctx.send(f":play_pause: **{self.tocando_agora[0]['title']}** tocando novamente!")
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
                msg = await ctx.send("Pagina não existente!")
                await msg.add_reaction("❌")
                return
            await asyncio.sleep(60)
            await msg.delete()

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
                                           f"\n**`{PREFIX}play:`**\n" +
                                           f"\t{PREFIX}play <**`url`**>: Toca uma música a partir do **`url`** dado, se estiver alguma musica tocando, adiciona á fila.\n" +
                                           f"\t{PREFIX}play playlist <**`nome da playlist`**>: Toca as músicas da playlist, se alguma estiver tocando, adiciona toda a playlist á fila.\n" +
                                           f"\n**`{PREFIX}skip:`** Pula a música atual ou para de tocar se a fila estiver vazia.\n" +
                                           f"**`{PREFIX}stop:`** Para a música atual e esvazia a fila.\n" +
                                           f"**`{PREFIX}pause:`** Pausa a música atual.\n" +
                                           f"**`{PREFIX}resume:`** Despausa a música pausada.\n" +
                                           f"**`{PREFIX}tocando:`** Exibe a música atual.\n" +
                                           f"**`{PREFIX}fila`** <**`pagina`**>: exibe a **`pagina`** da fila, se nenhuma pagina for especificada exibe a primeira\n" +
                                           f"**`{PREFIX}playlists:`** Exibe as playlists diponíveis."))

    def next_song(self, ctx):
        self.tocando_agora.clear()
        if len(self.queue) > 0:
            asyncio.run(self.play(ctx, self.queue.pop(0)))

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
            choice = random.choice(playlist)
            info = self.ytdl.extract_info(choice, download=False)
            self.queue.append(info)
            playlist.remove(choice)

        await mensagem_do_bot.add_reaction("✅")

    def duracao(self, duration):
        tempo = []
        dias = duration // 86400
        segundos_rest = duration % 86400
        horas = segundos_rest // 3600
        segundos_rest = segundos_rest % 3600
        minutos = segundos_rest // 60
        segundos_rest = segundos_rest % 60
        if dias > 0:
            if dias < 10:
                dias = f"0{str(dias)}"
            tempo.append(dias)
        if horas > 0:
            if horas < 10:
                horas = f"0{str(horas)}"
            tempo.append(str(horas))
        tempo.append(f"0{str(minutos)}" if minutos < 10 else str(minutos))
        tempo.append(f"0{str(segundos_rest)}" if segundos_rest < 10 else str(segundos_rest))
        return tempo

    def cria_embeds(self, queue):
        tamanho_max = 10
        count = 1
        songs = ""
        embeds = []

        for i in queue:
            tempo = self.duracao(queue[count - 1]['duration'])
            duration_song = ':'.join(tempo)
            songs += f"`{count}.` [**`{queue[count - 1]['title']}`**]({queue[count - 1]['webpage_url']})  `[{duration_song}]`\n"
            count += 1
            if count % tamanho_max == 1 or count == len(queue) + 1:
                embeds.append(songs)
                songs = ""

        return embeds
