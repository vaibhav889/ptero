from threading import Thread
from web import run

Thread(target=run).start()

import discord
from discord import app_commands
import requests
import os

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
PANEL_URL = os.getenv("PANEL_URL")
API_KEY = os.getenv("PTERODACTYL_API_KEY")
SERVER_ID = os.getenv("SERVER_ID")
ADMIN_IDS = [int(uid) for uid in os.getenv("ADMIN_IDS", "").split(",") if uid]

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}

def get_server_status():
    url = f'{PANEL_URL}/api/client/servers/{SERVER_ID}/resources'
    r = requests.get(url, headers=headers)
    return r.json().get('attributes', {}).get('current_state', 'error') if r.status_code == 200 else "error"

def send_power_signal(signal):
    url = f'{PANEL_URL}/api/client/servers/{SERVER_ID}/power'
    r = requests.post(url, json={"signal": signal}, headers=headers)
    return r.status_code == 204

def is_admin(user_id):
    return user_id in ADMIN_IDS

@tree.command(name="start", description="Start the Minecraft server if it's offline")
async def start(interaction: discord.Interaction):
    await interaction.response.defer()
    status = get_server_status()
    if status == "running":
        await interaction.followup.send("✅ Server is already online.")
    elif status == "starting":
        await interaction.followup.send("⏳ Server is already starting.")
    elif status == "offline":
        if send_power_signal("start"):
            await interaction.followup.send("🚀 Server is starting!")
        else:
            await interaction.followup.send("❌ Failed to start the server.")
    else:
        await interaction.followup.send("⚠️ Error checking server status.")

@tree.command(name="stop", description="Stop the Minecraft server (admin only)")
async def stop(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        return await interaction.followup.send("❌ You’re not allowed to use this.")
    await interaction.followup.send("🛑 Stopping…") if send_power_signal("stop") else await interaction.followup.send("❌ Failed to stop.")

@tree.command(name="restart", description="Restart the Minecraft server (admin only)")
async def restart(interaction: discord.Interaction):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        return await interaction.followup.send("❌ You’re not allowed to use this.")
    await interaction.followup.send("🔁 Restarting…") if send_power_signal("restart") else await interaction.followup.send("❌ Failed to restart.")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    try:
        print("Registering commands manually...")
        guild = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
        print(f"Synced {len(synced)} commands to guild {GUILD_ID}")
    except Exception as e:
        print(f"Sync failed: {e}")

try:
    client.run(TOKEN)
except Exception as e:
    print("Bot failed to start:", e)
