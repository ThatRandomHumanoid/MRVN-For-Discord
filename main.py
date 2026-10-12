import json
import os
import discord
import datetime
import aiohttp
import feedparser
from discord.ext import tasks
from discord.ext import commands
from discord import app_commands
from pathlib import Path

StartDate = datetime.date(2024, 4, 8)
ExcludedPrefix = "Uploading A Titanfall 2 Clip Everyday Until A New Titanfall Game Is Announced"
YouTubeChannelID = "UC4fjAQSKcfFa0Lmy9o7QMRw"
ChannelUploadsChannelID = 1559285089278500884
ChannelUploadsRoleID = 1559289939802194020

SeenVideosFile = Path(__file__).with_name("SeenVideos.json")


def SaveSeenVideos(Videos):
    TemporaryFile = SeenVideosFile.with_suffix(".tmp")
    TemporaryFile.write_text(
        json.dumps(sorted(Videos), indent=4),
        encoding="utf-8"
    )
    TemporaryFile.replace(SeenVideosFile)

def ShouldAnnounce(Title):
    return not Title.casefold().startswith(ExcludedPrefix.casefold())

class Client(discord.Client):
    
    async def setup_hook(self):
        self.CheckYouTube.start()

    @tasks.loop(minutes=5)
    async def CheckYouTube(self):
        URL = (
            f"https://www.youtube.com/feeds/videos.xml"
            f"?channel_id={YouTubeChannelID}"
        )

        try:
            async with aiohttp.ClientSession() as Session:
                async with Session.get(
                    URL, timeout=aiohttp.ClientTimeout(total=20)
                ) as Response:
                    Response.raise_for_status()
                    FeedText = await Response.text()

        except (aiohttp.ClientError, TimeoutError) as Error:
            print(f"YouTube request failed: {Error}")
            return

        Feed = feedparser.parse(FeedText)

        if Feed.bozo or not Feed.entries:
            print("YouTube feed unavailable or invalid")
            return

        CurrentVideos = {
            Entry.yt_videoid
            for Entry in Feed.entries
            if Entry.get("yt_videoid")
        }

        # First run: save existing uploads without announcing them
        if not SeenVideosFile.exists():
            SaveSeenVideos(CurrentVideos)
            print("Initialized YouTube video history")
            return

        try:
            SeenVideos = set(json.loads(
                SeenVideosFile.read_text(encoding="utf-8")
            ))
        except (OSError, ValueError, TypeError) as Error:
            print(f"Cannot read video history: {Error}")
            return

        Channel = self.get_channel(ChannelUploadsChannelID)

        if Channel is None:
            print("Channel uploads channel not found")
            return

        for Entry in reversed(Feed.entries):
            VideoID = Entry.get("yt_videoid")

            if not VideoID or VideoID in SeenVideos:
                continue

            if not ShouldAnnounce(Entry.title):

                SeenVideos.add(VideoID)
                SaveSeenVideos(SeenVideos)
                continue

            try:
                await Channel.send(
                    f'<@&{ChannelUploadsRoleID}>\n'
                    f'ThatRandomHumanoid just uploaded!!!\n'
                    f'{Entry.link}',
                    allowed_mentions=discord.AllowedMentions(
                        roles=True,
                        users=False,
                        everyone=False
                    )
                )
            except discord.HTTPException as Error:
                print(f"Announcement failed: {Error}")
                continue

            SeenVideos.add(VideoID)
            SaveSeenVideos(SeenVideos)
            print(f"Announced: {Entry.title}")

    @CheckYouTube.before_loop
    async def BeforeCheckYouTube(self):
        await self.wait_until_ready()


    
    async def on_ready(self):
        print(f'Logged in as {self.user}!')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.lower().startswith('hello mrvn'):
            await message.channel.send(f'Hello, {message.author.display_name}!')
    async def on_member_join(self, member):
            Today = datetime.date.today()
            DaysSinceStart = (Today - StartDate).days

            try:
                await member.send(f'Welcome to the server! So far we have been waiting for Titanfall 3 for {DaysSinceStart} days.')
            
            except discord.Forbidden:
                print(f"Could not send message to {member.display_name}")

            WelcomeChannel = member.guild.get_channel(1559283171453833237)

            if WelcomeChannel is not None:
                await WelcomeChannel.send(f'Hi {member.mention} to the server! So far we have been waiting for Titanfall 3 for {DaysSinceStart} days, and be sure to check out <#1427384995433021551>')

            DefaultRole = member.guild.get_role(1487504342394212402)

            if DefaultRole is not None:
                await member.add_roles(DefaultRole)


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = Client(intents=intents)
client.run(os.environ.get("DISCORD_BOT_TOKEN"))
