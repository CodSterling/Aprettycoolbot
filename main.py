import discord
from discord.ext import commands
import random
import asyncio
import json
import os
import requests


# Load credentials from Heroku's config variables
TOKEN = os.getenv("DISCORD_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # Convert to integer for Discord channel ID
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")



# Set up the bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='.', intents=intents)
intents.members = True
intents.message_content = True
intents.reactions = True
intents.guilds = True


# TMDB API URL for different categories
TMDB_BASE_URL = "https://api.themoviedb.org/3/discover/movie"

# YouTube API endpoint
YOUTUBE_API_URL = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={YOUTUBE_CHANNEL_ID}&part=snippet&order=date&maxResults=1"

# Load QuotaGuard Static proxy from Heroku config
QUOTAGUARD_URL = os.getenv("QUOTAGUARDSTATIC_URL")


last_video_id = None  # Store last posted video ID


# Setup the proxy for requests
proxies = {
    "http": QUOTAGUARD_URL,
    "https": QUOTAGUARD_URL
}


async def check_youtube():
    """Check for new YouTube videos every hour."""
    global last_video_id
    await bot.wait_until_ready()
    channel = bot.get_channel(DISCORD_CHANNEL_ID)

    while not bot.is_closed():
        try:
            response = requests.get(YOUTUBE_API_URL, proxies=proxies)
            data = response.json()

            if "items" in data and data["items"]:
                video = data["items"][0]
                video_id = video["id"].get("videoId")
                video_title = video["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                if video_id and video_id != last_video_id:
                    last_video_id = video_id  # Update last posted video

                    embed = discord.Embed(
                        title="📢 **New YouTube Video!** 🎥",
                        description=f"**{video_title}**\n\n[Watch now!]({video_url})",
                        color=discord.Color.red(),
                    )
                    embed.set_thumbnail(url=video["snippet"]["thumbnails"]["high"]["url"])
                    embed.set_footer(text="Go check it out!")

                    await channel.send(embed=embed)
                    print(f"✅ New video posted: {video_title}")

        except Exception as e:
            print(f"⚠️ Error checking YouTube: {e}")

        await asyncio.sleep(3600)  # Wait 1 hour before checking again

HEADERS = {
    "Authorization": f"Bearer {TMDB_API_KEY}",
    "Content-Type": "application/json"
}


def get_movies(genre=None, decade=None, count=3):
    """Fetch movies based on genre or decade."""
    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 50,
        "language": "en-US",
        "page": 1
    }

    if genre:
        params["with_genres"] = genre
    if decade:
        params["primary_release_date.gte"] = f"{decade}-01-01"
        params["primary_release_date.lte"] = f"{decade + 9}-12-31"

    response = requests.get(TMDB_BASE_URL, params=params)
    if response.status_code == 200:
        movies = response.json().get("results", [])[:count]
        return [
            {
                "title": movie["title"],
                "overview": movie["overview"].split(". ")[0] + ".",
                "rating": movie["vote_average"]
            }
            for movie in movies
        ]
    return []


async def post_movie_recommendations():
    """Fetch and post movie recommendations every 24 hours."""
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    while not bot.is_closed():
        if not channel:
            print("Channel not found.")
            return

        # Fetch movies
        movies_80s = get_movies(decade=1980)
        horror_movies = get_movies(genre=27)
        action_movies = get_movies(genre=28)

        embed = discord.Embed(title="🎬 **Movie Recommendations** 🎬", color=discord.Color.blue())

        def add_movies_to_embed(movies, category, emoji):
            embed.add_field(
                name=f"\n\n{emoji} **{category} Movies** {emoji}",
                value="\n\n".join(
                    [f"🎥 **{m['title']}**\n📜 {m['overview']}\n⭐ **{m['rating']}/10**" for m in movies]
                ),
                inline=False
            )

        add_movies_to_embed(movies_80s, "80s", "📼")
        add_movies_to_embed(horror_movies, "Horror", "👻")
        add_movies_to_embed(action_movies, "Action", "💥")

        await channel.send(embed=embed)
        print("✅ Movie recommendations posted!")

        # Wait for 24 hours (86400 seconds)
        await asyncio.sleep(86400)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.loop.create_task(post_movie_recommendations())
    bot.loop.create_task(check_youtube())


bot.run(TOKEN)
