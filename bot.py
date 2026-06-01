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
    
    # Step 1: Convert your Channel ID directly into your Uploads Playlist ID
    # YouTube Channel IDs start with 'UC'. Replacing 'UC' with 'UU' targets the uploads playlist!
    uploads_playlist_id = "UU" + CHANNEL_ID[2:] if CHANNEL_ID.startswith("UC") else CHANNEL_ID
    
    # Step 2: Request the very first item from the uploads playlist
    playlist_request = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist_id,
        maxResults=1
    )
    playlist_response = playlist_request.execute()
    
    # Step 3: Safely check and extract the content
    if playlist_response and 'items' in playlist_response and len(playlist_response['items']) > 0:
        latest_item = playlist_response['items'][0]
        
        title = latest_item['snippet']['title']
        description = latest_item['snippet']['description']
        video_id = latest_item['snippet']['resourceId']['videoId']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Safely extract the thumbnail image url
        thumbnails = latest_item['snippet'].get('thumbnails', {})
        high_res = thumbnails.get('high', thumbnails.get('medium', thumbnails.get('default', {})))
        thumbnail_url = high_res.get('url', '')

        # Shorten summary description if it is too long for the embed card
        if not description.strip():
            description = "No description text provided for this video upload."
        elif len(description) > 1500:
            description = description[:1500] + "..."
            
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
            if thumbnail_url:
                embed.set_image(url=thumbnail_url)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Could not find any videos inside this channel's public feed.")
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        await interaction.followup.send("An error occurred while communicating with YouTube.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable is missing!")
    else:
        threading.Thread(target=run_web_server, daemon=True).start()
        client.run(DISCORD_TOKEN)
