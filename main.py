import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Database
conn = sqlite3.connect('reminders.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS reminders 
             (user_id TEXT, guild_id TEXT, channel_id TEXT, message_id TEXT, remind_at REAL, 
              PRIMARY KEY(user_id, message_id))''')
conn.commit()

def parse_time(interval: str) -> int:
    """Parse 2h30m → seconds"""
    patterns = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}
    total = 0
    interval = interval.lower()
    for unit, secs in patterns.items():
        match = re.search(f'(\\d+){unit}', interval)
        if match:
            total += int(match.group(1)) * secs
    return max(total, 60)  # Min 1 minute

class SnoozeView(discord.ui.View):
    def __init__(self, message_id: int, channel_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.message_id = message_id
        self.channel_id = channel_id
        self.guild_id = guild_id

    async def save_reminder(self, interaction: discord.Interaction, seconds: int):
        remind_at = datetime.now().timestamp() + seconds
        c.execute("INSERT OR REPLACE INTO reminders VALUES (?, ?, ?, ?, ?)",
                 (str(interaction.user.id), str(self.guild_id),
                  str(self.channel_id), str(self.message_id), remind_at))
        conn.commit()

    @discord.ui.button(label="15m", style=discord.ButtonStyle.primary, emoji="⏰")
    async def snooze_15m(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.save_reminder(interaction, 15*60)
        await interaction.response.edit_message(
            content="✅ Snoozed for **15 minutes**! ⏰", 
            view=None
        )

    @discord.ui.button(label="1h", style=discord.ButtonStyle.primary, emoji="🕐")
    async def snooze_1h(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.save_reminder(interaction, 3600)
        await interaction.response.edit_message(
            content="✅ Snoozed for **1 hour**! 🕐", 
            view=None
        )

    @discord.ui.button(label="4h", style=discord.ButtonStyle.primary, emoji="🕔")
    async def snooze_4h(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.save_reminder(interaction, 4*3600)
        await interaction.response.edit_message(
            content="✅ Snoozed for **4 hours**! 🕔", 
            view=None
        )

    @discord.ui.button(label="Tomorrow", style=discord.ButtonStyle.secondary, emoji="🌅")
    async def snooze_tomorrow(self, interaction: discord.Interaction, button: discord.ui.Button):
        tomorrow = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if tomorrow < datetime.now(): tomorrow += timedelta(days=1)
        seconds = (tomorrow.timestamp() - datetime.now().timestamp())
        await self.save_reminder(interaction, seconds)
        await interaction.response.edit_message(
            content=f"✅ Snoozed until **tomorrow 9AM**! 🌅", 
            view=None
        )

    @discord.ui.button(label="Custom", style=discord.ButtonStyle.success, emoji="⌨️")
    async def custom_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomModal(self.message_id, self.channel_id, self.guild_id)
        await interaction.response.send_modal(modal)

class CustomModal(discord.ui.Modal, title="Custom Snooze"):
    time_input = discord.ui.TextInput(
        label="Duration", 
        placeholder="min=1m, examples: 2h30m, 1d, 45m",
        required=True
    )

    def __init__(self, message_id: int, channel_id: int, guild_id: int):
        super().__init__()
        self.message_id = message_id
        self.channel_id = channel_id
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        seconds = parse_time(self.time_input.value)
        if seconds < 60:
            await interaction.followup.send("❌ Minimum snooze time is **1 minute**. Use `1m`, `2m`, etc.", ephemeral=True)
            return
            
        remind_at = datetime.now().timestamp() + seconds
        
        c.execute("INSERT OR REPLACE INTO reminders VALUES (?, ?, ?, ?, ?)",
                 (str(interaction.user.id), str(self.guild_id),
                  str(self.channel_id), str(self.message_id), remind_at))
        conn.commit()
        
        await interaction.followup.send(
            f"✅ Snoozed for **{self.time_input.value}**!\n⏰ Reminder: <t:{int(remind_at)}:R>", 
            ephemeral=True
        )

@bot.tree.context_menu(name="🛌 Snooze Message")
async def snooze_menu(interaction: discord.Interaction, message: discord.Message):
    embed = discord.Embed(
        title="⏰ Snooze this message",
        description=f"[Jump back anytime](https://discord.com/channels/{interaction.guild.id}/{message.channel.id}/{message.id})",
        color=0x5865f2
    )
    view = SnoozeView(message.id, message.channel.id, interaction.guild.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def send_reminder(user_id: str, guild_id: str, channel_id: str, message_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        embed = discord.Embed(
            title="⏰ Snooze Reminder",
            description=f"**[Click to return to message]({url})**",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text="SnoozeBot • Right-click any message to snooze again")
        await user.send(embed=embed)
    except:
        pass

@bot.event
async def on_ready():
    print(f'{bot.user} online! Synced {len(await bot.tree.sync())} commands')
    bot.scheduler = AsyncIOScheduler()
    bot.scheduler.add_job(check_reminders, 'interval', minutes=1)
    bot.scheduler.start()
    print("✅ Snooze checker running...")

async def check_reminders():
    now = datetime.now().timestamp()
    c.execute("SELECT * FROM reminders WHERE remind_at <= ?", (now,))
    for row in c.fetchall():
        await send_reminder(*[str(x) for x in row[:4]])
        c.execute("DELETE FROM reminders WHERE user_id=? AND message_id=?", (row[0], row[3]))
    if c.rowcount:
        conn.commit()

if __name__ == "__main__":
    bot.run(TOKEN)
