import discord, asyncio
from discord.ext import commands
import yt_dlp
import os
import io
from dotenv import load_dotenv, dotenv_values
from gtts import gTTS

class mamyoshevo (commands.Bot):
    def __init__(self, guild, **kwargs):
        self.guild = discord.Object(id=guild)
        self.voice_disconnect_tasks = {}
        super().__init__(**kwargs)

    async def on_ready(self):
        print(f'We have logged in as {self.user}')
        try:
            synced = await self.tree.sync(guild=self.guild)
        except Exception as e:
            print(f'{e}')


    async def on_voice_state_update(self, member, before, after):
        if before.channel is None:
            return

        guild = before.channel.guild
        voice_client = guild.voice_client

        # Если бота нет в голосовом канале на этом сервере, ничего не делаем
        if voice_client is None:
            return

        # Проверяем, что люди вышли именно из того канала, где сидит бот
        if voice_client.channel.id == before.channel.id:

            # Считаем количество реальных пользователей (исключая ботов)
            real_users = [m for m in voice_client.channel.members if not m.bot]

            # Если в канале остались только боты (или он совсем пуст)
            if len(real_users) == 0:

                # Если таймер для этого сервера уже запущен, не создаем дубликат
                if guild.id in self.voice_disconnect_tasks and not self.voice_disconnect_tasks[guild.id].done():
                    return

                # Запускаем задачу ожидания 5 минут (300 секунд)
                task = asyncio.create_task(self.wait_and_disconnect(guild, voice_client))
                self.voice_disconnect_tasks[guild.id] = task


    async def wait_and_disconnect(self, guild, voice_client):
        try:
            print(f"[{guild.name}] Канал пуст. Запущен таймер отключения на 1 минуту")
            await asyncio.sleep(60)  # Ожидание 1 минуты

            # По истечении времени проверяем еще раз, пуст ли канал
            if voice_client.is_connected():
                real_users = [m for m in voice_client.channel.members if not m.bot]
                if len(real_users) == 0:
                    await voice_client.disconnect()
                    print(f"[{guild.name}] Бот отключился из-за отсутствия активности.")
        except asyncio.CancelledError:
            # Сюда код попадает, если мы вызвали task.cancel() при возвращении людей
            pass

    async def play(self, ctx, arg):
        if ctx.user.voice is None:
            await ctx.response.send_message("Вы должны находиться в голосовом канале, чтобы использовать эту команду!")
            return

        channel = ctx.user.voice.channel
        voice_client = ctx.guild.voice_client
        if voice_client is not None:
            await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()

        if voice_client.is_playing():
            voice_client.stop()

        await ctx.response.send_message('Запускаю брат')
        voice_client.play(arg)

if __name__ == '__main__':
    load_dotenv()
    intents = discord.Intents.default()
    intents.message_content = True
    bot = mamyoshevo(guild=os.getenv("guild"), command_prefix="!", intents=intents)

    @bot.tree.command(name='пинг', description='пинг', guild=bot.guild)
    async def ping(ctx):
        await ctx.response.send_message('пук')

    @bot.tree.command(name='мамёшиво', description='Запустить музыку про великое Мамёшиво', guild=bot.guild)
    async def play_mamyoshevo(ctx):
        await bot.play(ctx, discord.FFmpegPCMAudio('Mamyoshevo.mp3'))

    @bot.tree.command(name='ютуб', description='Запустить аудио с ютуба', guild=bot.guild)
    async def play_youtube(ctx, url: str):
        YTDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
        }
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }

        ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
        try:
            data = ytdl.extract_info(url, download=False)
            # Проверяем, является ли объект плейлистом
            if 'entries' in data:
                data = data['entries'][0]
        
            filename = data['url']
            title = data.get('title', 'Аудиозапись')
        except Exception as e:
            print(f"{e}")
            return

        await bot.play(ctx, discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS))

    @bot.tree.command(name='сказать', description='сказать текст', guild=bot.guild)
    async def say(ctx, msg: str):
        mp3_fp = io.BytesIO()
        tts = gTTS(text=msg, lang='ru', slow=False)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        try:
            audio_source = discord.FFmpegPCMAudio(
                mp3_fp,
                pipe=True,
                before_options="-f mp3",
                options="-f s16le -ar 48000 -ac 2"
            )
            await bot.play(ctx, audio_source)
        finally:
            mp3_fp.close()

    bot.run(os.getenv("token"))