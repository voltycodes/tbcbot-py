import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # We need this to fetch member objects

class LeaderboardBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = LeaderboardBot()

def load_data():
    if os.path.exists('data.json'):
        with open('data.json', 'r') as f:
            data = json.load(f)
        return data.get('leaderboard_channel', 'leaderboard'), data.get('updates_channel', 'weekly-updates'), data.get('rankings', {})
    else:
        data = {
            'leaderboard_channel': 'leaderboard',
            'updates_channel': 'weekly-updates',
            'rankings': {}
        }
        with open('data.json', 'w') as f:
            json.dump(data, f)
        return 'leaderboard', 'weekly-updates', {}

@bot.tree.command(name="update_leaderboard", description="Update the leaderboard based on x.com links in the updates channel")
async def update_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    leaderboard_channel, updates_channel, rankings = load_data()

    # Check if channels exist
    leaderboard_ch = discord.utils.get(interaction.guild.channels, name=leaderboard_channel)
    updates_ch = discord.utils.get(interaction.guild.channels, name=updates_channel)
    general = discord.utils.get(interaction.guild.channels, name="general")

    if not leaderboard_ch or not updates_ch:
        await interaction.followup.send("Error: One or both channels don't exist.")
        return

    # Process messages from updates channel
    async for message in updates_ch.history(limit=None):
        if 'x.com' in message.content:
            username = str(message.author.id)  # Store user ID instead of username
            timestamp = message.created_at.timestamp()
            
            if username not in rankings:
                rankings[username] = []
            
            if not rankings[username] or datetime.fromtimestamp(rankings[username][-1]).date() != datetime.fromtimestamp(timestamp).date():
                rankings[username].append(timestamp)

    # Update data.json
    with open('data.json', 'r+') as f:
        data = json.load(f)
        data['rankings'] = rankings
        f.seek(0)
        json.dump(data, f)
        f.truncate()

    await interaction.followup.send("Updated data.json")

    # Update leaderboard message
    leaderboard_content = "# RANKINGS\n\n\n\n"
    
    sorted_rankings = sorted(rankings.items(), key=lambda x: len(x[1]), reverse=True)
    
    for rank, (user_id, timestamps) in enumerate(sorted_rankings, 1):
        member = await interaction.guild.fetch_member(int(user_id))
        if member:
            leaderboard_content += f"\n**[{rank}]** {member.mention} — {len(timestamps)} points\n"
        else:
            leaderboard_content += f"\n**[{rank}]** @{user_id} — {len(timestamps)} points\n"

    # Get the last message in the leaderboard channel
    last_message = None
    async for message in leaderboard_ch.history(limit=1):
        last_message = message
        break

    if last_message:
        await last_message.edit(content=leaderboard_content)
    else:
        await leaderboard_ch.send(leaderboard_content)

    await interaction.followup.send("Updated leaderboard")
    # mention everyone in general channel and tell them to check the leaderboard
    await general.send(f"Hey @everyone! The leaderboard has been updated. Check it out in {leaderboard_ch.mention}.")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Get the bot token from the environment variable
bot_token = os.getenv('DISCORD_BOT_TOKEN')
if not bot_token:
    raise ValueError("No bot token found. Make sure to set the DISCORD_BOT_TOKEN environment variable.")

bot.run(bot_token)
