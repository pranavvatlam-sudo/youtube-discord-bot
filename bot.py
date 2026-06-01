import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from googleapiclient.discovery import build

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
        # Sync slash commands globally with Discord
        await self.tree.sync()
        print("Slash commands synchronized.")

client = MyBot()

def get_latest_youtube_video():
    # Build connection to YouTube API
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    # Request the most recent public video from the channel
    request = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        maxResults=1,
        order="date",
        type="video"
    )
    response = request.execute()
    
    if response and 'items' in response and response['items']:
        video_data = response['items'][0]
        title = video_data['snippet']['title']
        video_id = video_data['id']['videoId']
        thumbnail_url = video_data['snippet']['thumbnails']['high']['url']
        video_url = f"https://youtube.com{video_id}"
        return title, video_url, thumbnail_url
    return None, None, None

@client.tree.command(name="news", description="Fetches the newest video from the monitored YouTube channel.")
async def news(interaction: discord.Interaction):
    # Defer response to prevent the command timing out during API request
    await interaction.response.defer()
    
    try:
        title, video_url, thumbnail_url = get_latest_youtube_video()
        
        if title and video_url:
            # Create an attractive rich embed message
            embed = discord.Embed(
                title="📢 Latest Video Upload!",
                description=f"**[{title}]({video_url})**",
                color=discord.Color.red()
            )
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
        client.run(DISCORD_TOKEN)
