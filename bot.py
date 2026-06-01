import os
import discord
import threading
from discord import app_commands
from dotenv import load_dotenv
from googleapiclient.discovery import build
from flask import Flask

# ----------------- WEB SERVER FOR RENDER -----------------
# This creates a dummy webpage so Render passes its port scans
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
    # Render automatically provides a PORT environment variable
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
# --------------------------------------------------------

# Load our secret keys
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')

# Initialize Discord Bot client
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
    
    # 1. Search for the latest video ID
    search_request = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        maxResults=1,
        order="date",
        type="video"
    )
    search_response = search_request.execute()
    
    if search_response and 'items' in search_response and search_response['items']:
        video_data = search_response['items'][0]  # Grab the first item safely
        video_id = video_data['id']['videoId']
        title = video_data['snippet']['title']
        thumbnail_url = video_data['snippet']['thumbnails']['high']['url']
        video_url = f"https://youtube.com{video_id}"
        
        # 2. Make a second precise call to get the full video description detail
        video_request = youtube.videos().list(
            part="snippet",
            id=video_id
        )
        video_response = video_request.execute()
        
        description = "No description provided for this video."
        if video_response and 'items' in video_response and video_response['items']:
            full_description = video_response['items'][0]['snippet']['description']
            if full_description.strip():
                # Clean up text length for clean display
                description = full_description[:250] + "..." if len(full_description) > 250 else full_description

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
            # Display title and summary cleanly in fields
            embed.add_field(name="🎬 Video Title", value=title, inline=False)
            embed.add_field(name="📝 Video Summary / Description", value=description, inline=False)
            embed.set_image(url=thumbnail_url)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Could not find any videos for this channel.")
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        await interaction.followup.send("An error occurred while communicating with YouTube.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable is missing!")
    else:
        # Start the Flask web server in a separate background thread
        threading.Thread(target=run_web_server, daemon=True).start()
        
        # Start the Discord Bot
        client.run(DISCORD_TOKEN)
