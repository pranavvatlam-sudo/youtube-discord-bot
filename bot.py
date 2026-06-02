import os
import discord
import threading
from discord import app_commands
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google import genai
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
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.tree.sync()
        print("Slash commands synchronized.")

client = MyBot()

def get_latest_youtube_video_with_ai_summary():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    # Flexible search extraction query matching channel filters
    search_request = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        maxResults=1,
        order="date",
        type="video"
    )
    search_response = search_request.execute()
    
    # Added explicit array indexing [0] to safely parse parameters
    if search_response and 'items' in search_response and len(search_response['items']) > 0:
        first_video = search_response['items'][0]
        
        title = first_video['snippet']['title']
        raw_description = first_video['snippet']['description']
        video_id = first_video['id']['videoId']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Safely extract matching thumbnails
        thumbnails = first_video['snippet'].get('thumbnails', {})
        high_res = thumbnails.get('high', thumbnails.get('medium', thumbnails.get('default', {})))
        thumbnail_url = high_res.get('url', '')

        # --- GEMINI AI LIVE BREAKDOWN INTEGRATION ---
        ai_summary = "No detailed description summary available."
        if raw_description.strip() and GEMINI_API_KEY:
            try:
                ai_client = genai.Client(api_key=GEMINI_API_KEY)
                
                prompt = (
                    f"You are a helpful Discord community manager assistant. Read the following YouTube video title "
                    f"and text description. Write a clean, highly descriptive, and engaging summary of what this video "
                    f"is about. Structure it nicely with a couple of bullet points for key takeaways. Keep it under "
                    f"1200 characters total.\n\nVideo Title: {title}\nDescription: {raw_description}"
                )
                
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                if response.text:
                    ai_summary = response.text
            except Exception as ai_err:
                print(f"Gemini Processing Error: {ai_err}")
                ai_summary = raw_description[:1000] + "..." if len(raw_description) > 1000 else raw_description
        else:
            ai_summary = raw_description[:1000] + "..." if len(raw_description) > 1000 else raw_description

        return title, video_url, thumbnail_url, ai_summary
        
    return None, None, None, None

@client.tree.command(name="news", description="Fetches the newest video and an AI-generated summary from the channel.")
async def news(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        title, video_url, thumbnail_url, ai_summary = get_latest_youtube_video_with_ai_summary()
        
        if title and video_url:
            embed = discord.Embed(
                title="📢 Latest Video Upload!",
                url=video_url,
                color=discord.Color.green()  # Dark green theme matching Minecraft branding
            )
            embed.add_field(name="🎬 Video Title", value=title, inline=False)
            embed.add_field(name="🧠 AI Video Summary & Highlights", value=ai_summary, inline=False)
            if thumbnail_url:
                embed.set_image(url=thumbnail_url)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Could not find any public videos inside this channel's feed.")
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        await interaction.followup.send("An error occurred while communicating with the systems.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable is missing!")
    else:
        threading.Thread(target=run_web_server, daemon=True).start()
        client.run(DISCORD_TOKEN)
