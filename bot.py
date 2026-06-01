import os
import discord
import threading
from discord import app_commands
from dotenv import load_dotenv
from googleapiclient.discovery import build
from flask import Flask

# ----------------- WEB SERVER FOR RENDER -----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
# --------------------------------------------------------

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.tree.sync()
        print("Slash commands synchronized.")

client = MyBot()

def get_latest_youtube_video_with_summary():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    # Fetch the latest video from the channel
    search_request = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        maxResults=1,
        order="date",
        type="video"
    )
    search_response = search_request.execute()
    
    # Safely unpack the first item using index [0]
    if search_response and 'items' in search_response and len(search_response['items']) > 0:
        first_video = search_response['items'][0]
        
        title = first_video['snippet']['title']
        video_id = first_video['id']['videoId']
        description = first_video['snippet']['description'] 
        thumbnail_url = first_video['snippet']['thumbnails']['high']['url']
        video_url = f"https://youtube.com{video_id}"
        
        if not description.strip():
            description = "No description summary provided for this upload."
            
        return title, video_url, thumbnail_url, description
        
    return None, None, None, None

@client.tree.command(name="news", description="Fetches the newest video and summary from the monitored YouTube channel.")
async def news(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        title, video_url, thumbnail_url, description = get_latest_youtube_video_with_summary()
        
        if title and video_url:
            embed = discord.Embed(
                title="📢 Latest Video Upload!",
                url=video_url,
                color=discord.Color.red()
            )
            embed.add_field(name="🎬 Video Title", value=title, inline=False)
            embed.add_field(name="📝 Video Summary", value=description, inline=False)
            embed.set_image(url=thumbnail_url)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Could not find any public videos for this channel ID.")
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        await interaction.followup.send("An error occurred while communicating with YouTube.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable is missing!")
    else:
        threading.Thread(target=run_web_server, daemon=True).start()
        client.run(DISCORD_TOKEN)
