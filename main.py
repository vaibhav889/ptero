from threading import Thread
from web import run

Thread(target=run).start()

import discord
from discord import app_commands
from discord.app_commands import Choice
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

@tree.command(name="status", description="Check the current server status")
async def status(interaction: discord.Interaction):
    await interaction.response.defer()
    state = get_server_status()
    await interaction.followup.send(f"📊 Server status: **{state.upper()}**")

@tree.command(name="ip", description="Get the Minecraft server IP")
async def ip(interaction: discord.Interaction):
    await interaction.response.send_message("📡 Server IP: `paid-1.guardxhosting.in`")

@tree.command(name="uptime", description="Check how long the server has been online")
async def uptime(interaction: discord.Interaction):
    await interaction.response.defer()
    url = f'{PANEL_URL}/api/client/servers/{SERVER_ID}/resources'
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return await interaction.followup.send("❌ Could not fetch server status.")

    try:
        uptime_secs = r.json()["attributes"]["resources"]["uptime"] // 1000
        hours, minutes = divmod(uptime_secs // 60, 60)
        await interaction.followup.send(f"🕒 Uptime: **{hours}h {minutes}m**")
    except:
        await interaction.followup.send("⚠️ Uptime info not available.")

@tree.command(name="website", description="View the SMP's official website")
async def website(interaction: discord.Interaction):
    await interaction.response.send_message("🌍 Visit our official website to explore everything about the server:\nhttps://mcdeltasmp.vercel.app/")

@tree.command(name="vote", description="Vote for the SMP to support us!")
async def vote(interaction: discord.Interaction):
    message = (
        "**🗳 Vote for McDelta SMP!**\n"
        "1. https://discordservers.com/bump/1354330313240871022\n"
        "2. https://discords.com/servers/1354330313240871022/upvote\n"
        "3. https://discadia.com/vote/mcdeltasmp/"
    )
    await interaction.response.send_message(message)

@tree.command(name="cmd", description="Execute a console command (admin only)")
@app_commands.describe(command="The command to run in server console")
async def cmd(interaction: discord.Interaction, command: str):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        return await interaction.followup.send("❌ You are not authorized.")

    url = f'{PANEL_URL}/api/client/servers/{SERVER_ID}/command'
    r = requests.post(url, json={"command": command}, headers=headers)
    if r.status_code == 204:
        await interaction.followup.send(f"✅ Command sent: `{command}`")
    else:
        await interaction.followup.send("❌ Failed to send command.")

@tree.command(name="whitelist", description="Manage whitelist (admin only)")
@app_commands.describe(action="Choose an action", player="Minecraft username")
@app_commands.choices(action=[
    Choice(name="add", value="add"),
    Choice(name="remove", value="remove"),
    Choice(name="list", value="list"),
])
async def whitelist(interaction: discord.Interaction, action: Choice[str], player: str = None):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        return await interaction.followup.send("❌ You’re not authorized to manage whitelist.")

    if action.value in ["add", "remove"] and not player:
        return await interaction.followup.send("❗ You must provide a player name.")

    command = None
    if action.value == "add":
        command = f"whitelist add {player}"
    elif action.value == "remove":
        command = f"whitelist remove {player}"
    elif action.value == "list":
        command = "whitelist list"

    url = f'{PANEL_URL}/api/client/servers/{SERVER_ID}/command'
    r = requests.post(url, json={"command": command}, headers=headers)

    if r.status_code == 204:
        await interaction.followup.send(f"✅ Sent command: `{command}`")
    else:
        await interaction.followup.send("❌ Failed to send whitelist command.")

@tree.command(name="backup", description="Manage server backups (admin only)")
@app_commands.describe(action="Action to perform: create or delete")
@app_commands.choices(action=[
    Choice(name="create", value="create"),
    Choice(name="delete", value="delete"),
])
async def backup(interaction: discord.Interaction, action: Choice[str]):
    await interaction.response.defer()
    if not is_admin(interaction.user.id):
        return await interaction.followup.send("❌ You are not authorized.")

    if action.value == "create":
        list_url = f"{PANEL_URL}/api/client/servers/{SERVER_ID}/backups"
        response = requests.get(list_url, headers=headers)
        if response.status_code != 200:
            return await interaction.followup.send("⚠️ Failed to check existing backups.")

        backups = response.json().get("data", [])
        if len(backups) >= 1:
            return await interaction.followup.send("📦 Backup limit reached. Please delete an old backup first.")

        create_url = f"{PANEL_URL}/api/client/servers/{SERVER_ID}/backups"
        response = requests.post(create_url, json={"name": "DiscordBot Backup"}, headers=headers)
        if response.status_code == 201 or response.status_code == 200:
            await interaction.followup.send("✅ Backup is being created!")
        else:
            await interaction.followup.send("❌ Failed to create backup, but it might have been triggered.")

    elif action.value == "delete":
        list_url = f"{PANEL_URL}/api/client/servers/{SERVER_ID}/backups"
        response = requests.get(list_url, headers=headers)
        if response.status_code != 200:
            return await interaction.followup.send("⚠️ Failed to list backups.")

        backups = response.json().get("data", [])
        if not backups:
            return await interaction.followup.send("🗑 No existing backups to delete.")

        latest_backup = backups[0]["attributes"]["uuid"]
        delete_url = f"{PANEL_URL}/api/client/servers/{SERVER_ID}/backups/{latest_backup}"
        response = requests.delete(delete_url, headers=headers)
        if response.status_code == 204:
            await interaction.followup.send("🗑 Backup deleted successfully.")
        else:
            await interaction.followup.send("❌ Failed to delete backup.")

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Ready as {client.user}")

client.run(TOKEN)
