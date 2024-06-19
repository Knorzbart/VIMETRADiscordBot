# -*- coding: utf-8 -*-
import os
import discord
from discord.ext import commands, tasks
import logging
from logging.handlers import TimedRotatingFileHandler
import openai
import asyncio
from datetime import datetime
import re
from langdetect import detect
from difflib import SequenceMatcher

YOUR_GUILD_ID = 1096398948765290569 #os.getenv('GUILD_ID')
IGNORED_CHANNELS = ["johnny-dump", "welcome", "announcements", "tester-rankings", "intro-and-templates", "johnny-features"]
MAX_DISCORD_MESSAGE_LENGTH = 2000
MESSAGE_PROCESSING_DELAY = 10  # Adjust the delay as needed

client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

log_filename = os.path.join(log_dir, f'bot-log-{datetime.now().strftime("%Y-%m-%d")}.log')

class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when='midnight', interval=1, backupCount=7, encoding=None, delay=False, utc=False, atTime=None):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        self.suffix = "%Y-%m-%d"
        self.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        currentTime = int(self.rolloverAt)
        timeTuple = time.localtime(currentTime)
        dfn = self.baseFilename + "." + time.strftime(self.suffix, timeTuple) + ".log"
        if os.path.exists(dfn):
            os.remove(dfn)
        self.rotate(self.baseFilename, dfn)
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt += self.interval
        if self.utc:
            timeTuple = time.gmtime(newRolloverAt)
        else:
            timeTuple = time.localtime(newRolloverAt)
        newRolloverAt = time.mktime(timeTuple)
        self.rolloverAt = newRolloverAt

logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
console_handler = logging.StreamHandler()
file_handler = CustomTimedRotatingFileHandler(log_filename, when='midnight', interval=1, backupCount=7, encoding='utf-8', utc=True)
console_handler.setLevel(logging.INFO)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger = logging.getLogger()
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(console_handler)
logger.addHandler(file_handler)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

def split_message(message, max_length=MAX_DISCORD_MESSAGE_LENGTH):
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

async def post_split_message(channel, messages):
    message_ids = []
    for msg in messages:
        sent_message = await channel.send(msg)
        message_ids.append(sent_message.id)
    for _ in range(3):
        consecutive = True
        history = [message async for message in channel.history(limit=len(messages))]
        history = list(reversed(history))
        for i, msg_id in enumerate(message_ids):
            if history[i].id != msg_id:
                consecutive = False
                break
        if consecutive:
            break
        else:
            for msg_id in message_ids:
                msg = await channel.fetch_message(msg_id)
                await msg.delete()
            await asyncio.sleep(2)
            message_ids = []
            for msg in messages:
                sent_message = await channel.send(msg)
                message_ids.append(sent_message.id)
    else:
        logger.error("Failed to ensure consecutive message order after retries.")

async def dump_message(guild, author, content):
    try:
        dump_channel = get_channel_by_name(guild, "johnny-dump")
        if dump_channel:
            await dump_channel.send(f"**Original message from {author.name}:**\n{content}\n{'_'*40}")
    except Exception as e:
        logger.error(f"Error dumping message from {author.name}: {e}")

@bot.event
async def on_ready():
    try:
        logger.info(f'We have logged in as {bot.user}')
        log_status.start()
        await update_rankings_on_startup()
        rankings_update.start()
    except Exception as e:
        logger.error(f"Error in on_ready: {e}")

@tasks.loop(minutes=15)
async def log_status():
    try:
        logger.info("The bot is still running.")
    except Exception as e:
        logger.error(f"Error in log_status: {e}")

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

async def rewrite_message(content, user_message):
    try:
        logger.info("Rewriting message using OpenAI API.")
        prompt_instructions = read_file(os.path.join(script_dir, "prompt", "prompt_issues_feature_request.txt"))
        description_website = read_file(os.path.join(script_dir, "description", "description_website.txt"))

        prompt = f"{prompt_instructions}\n\n{description_website}\n\nUser Message:\n{user_message}"

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in rewrite_message: {e}")
        return "An error occurred while rewriting the message. Please try again later."

def is_similar(a, b):
    return SequenceMatcher(None, a, b).ratio() > 0.8

@bot.event
async def on_message(message):
    try:
        if message.author == bot.user:
            return
        guild = bot.get_guild(YOUR_GUILD_ID)
        if guild:
            await dump_message(guild, message.author, message.content)
        if isinstance(message.channel, discord.DMChannel):
            await handle_direct_message(message)
        elif isinstance(message.channel, discord.TextChannel):
            if message.channel.name.lower() in IGNORED_CHANNELS:
                return
            await handle_server_message(message)
        await bot.process_commands(message)
        if guild:
            await update_rankings(guild)
    except Exception as e:
        logger.error(f"Error in on_message: {e}")

async def handle_direct_message(message):
    try:
        logger.info(f"Handling direct message from {message.author.name}.")
        async for previous_message in message.channel.history(limit=1, before=message):
            if previous_message.author == message.author and (message.created_at - previous_message.created_at).seconds < 300:
                if is_similar(previous_message.content, message.content):
                    await previous_message.edit(content=previous_message.content + "\n" + message.content)
                    await message.delete()
                    return

        bot_response = await message.channel.send(f"Thank you {message.author.name} for your feedback. Your message will be processed.")
        await asyncio.sleep(MESSAGE_PROCESSING_DELAY)
        logger.info(f"Processing message from {message.author.name} (ID: {message.author.id}): {message.content}")

        rewritten_message = await rewrite_message(message.content, message.content)
        category, processed_message = determine_category(rewritten_message)

        guild = bot.get_guild(YOUR_GUILD_ID)
        if guild is None:
            raise ValueError(f"Guild with ID {YOUR_GUILD_ID} not found.")
        channel = get_channel_by_name(guild, category)
        messages = split_message(f"Rewritten issue report from {message.author.name}:\n{processed_message}\n{'_'*40}")
        await post_split_message(channel, messages)
        logger.info(f"Rewritten message posted to {channel.name}: {processed_message}")
        await notify_bot_listeners(guild, message.author.name, category, processed_message)
        await bot_response.delete()
    except Exception as e:
        logger.error(f"Error handling DM from {message.author.name} (ID: {message.author.id}): {e}")
        await message.channel.send(f"An error occurred while processing your message, {message.author.name}. Please try again later.")

async def handle_server_message(message):
    try:
        logger.info(f"Handling server message from {message.author.name} in channel {message.channel.name}.")
        async for previous_message in message.channel.history(limit=1, before=message):
            if previous_message.author == message.author and (message.created_at - previous_message.created_at).seconds < 300:
                if is_similar(previous_message.content, message.content):
                    await previous_message.edit(content=previous_message.content + "\n" + message.content)
                    await message.delete()
                    return

        bot_response = await message.channel.send(f"Thank you {message.author.name} for your feedback. Your message will be processed.")
        await asyncio.sleep(MESSAGE_PROCESSING_DELAY)
        logger.info(f"Processing message from {message.author.name} (ID: {message.author.id}): {message.content}")

        rewritten_message = await rewrite_message(message.content, message.content)
        category, processed_message = determine_category(rewritten_message)

        guild = bot.get_guild(YOUR_GUILD_ID)
        if guild is None:
            raise ValueError(f"Guild with ID {YOUR_GUILD_ID} not found.")
        channel = get_channel_by_name(guild, category)
        messages = split_message(f"Rewritten issue report:\n{processed_message}\n{'_'*40}")
        await post_split_message(channel, messages)
        logger.info(f"Rewritten message posted to {channel.name}: {processed_message}")
        await notify_bot_listeners(guild, message.author.name, category, processed_message)
        await message.delete()
        await bot_response.delete()
    except Exception as e:
        logger.error(f"Error handling message from {message.author.name} (ID: {message.author.id}) in channel {message.channel.name}: {e}")
        await message.channel.send(f"An error occurred while processing your message, {message.author.name}. Please try again later.")

def determine_category(message):
    categories = {
        "freies feedback": "freies-feedback",
        "usability": "usability-issues",
        "user experience": "user-experience-issues",
        "performance": "performance-issues",
        "allgemeine fehler": "allgemeine-issues",
        "sicherheit": "sicherheits-issues",
        "feature request": "feature-requests"
    }
    for key, value in categories.items():
        if key.lower() in message.lower():
            return value, message
    return "johnny-answers", message

def get_channel_by_name(guild, channel_name):
    channel = discord.utils.get(guild.channels, name=channel_name.lower())
    if channel is None:
        raise ValueError(f"Channel {channel_name} not found in guild.")
    return channel

async def notify_bot_listeners(guild, author_name, category, content):
    logger.info(f"Notifying bot listeners about a new message from {author_name}.")
    role = discord.utils.get(guild.roles, name='bot-listeners')
    if role:
        for member in role.members:
            try:
                await member.send(f"New message processed.\n**Author:** {author_name}\n**Category:** {category}\n**Content:** {content}")
            except Exception as e:
                logger.error(f"Error notifying member {member.name}: {e}")

@bot.command()
async def hello(ctx):
    try:
        user = ctx.message.author
        await ctx.send(f'Hello, {user.name}!')
        logger.info(f'Hello command was invoked by {user.name} (ID: {user.id})')
        guild = bot.get_guild(YOUR_GUILD_ID)
        if guild:
            await update_rankings(guild)
    except Exception as e:
        logger.error(f"Error in hello command: {e}")
        await ctx.send(f"An error occurred while processing the hello command.")

async def update_rankings(guild):
    try:
        logger.info("Updating tester rankings.")
        ranking_channel = discord.utils.get(guild.text_channels, name="tester-rankings")
        if ranking_channel is None:
            logger.warning("Ranking channel not found.")
            return
        async for message in ranking_channel.history(limit=100):
            try:
                await message.delete()
            except discord.errors.NotFound:
                logger.warning(f"Message {message.id} not found. It may have already been deleted.")
        issue_rankings = {}
        feature_rankings = {}
        issue_channels = ["freies-feedback", "usability-issues", "user-experience-issues", "performance-issues", "allgemeine-issues", "sicherheits-issues"]
        feature_channel = "feature-requests"
        user_pattern = re.compile(r'Rewritten issue report from (.+):')
        devteam_role = discord.utils.get(guild.roles, name="devteam")
        for channel_name in issue_channels:
            channel = discord.utils.get(guild.text_channels, name=channel_name.lower())
            if channel:
                async for message in channel.history(limit=100):
                    if message.author == bot.user:
                        match = user_pattern.search(message.content.lower())
                        if match:
                            user = match.group(1)
                            issue_rankings[user] = issue_rankings.get(user, 0) + 1
                    else:
                        member = await guild.fetch_member(message.author.id)
                        if devteam_role not in member.roles or channel_name != "freies-feedback":
                            user = message.author.name.lower()
                            issue_rankings[user] = issue_rankings.get(user, 0) + 1
        channel = discord.utils.get(guild.text_channels, name=feature_channel.lower())
        if channel:
            async for message in channel.history(limit=100):
                if message.author == bot.user:
                    match = user_pattern.search(message.content.lower())
                    if match:
                        user = match.group(1)
                        feature_rankings[user] = feature_rankings.get(user, 0) + 1
                else:
                    user = message.author.name.lower()
                    feature_rankings[user] = feature_rankings.get(user, 0) + 1
        issue_ranking_text = "# Issue Reporter Rankings:\n" + "\n".join([f"{index+1}. {user}: {count}" for index, (user, count) in enumerate(sorted(issue_rankings.items(), key=lambda item: item[1], reverse=True))])
        feature_ranking_text = "# Feature Requester Rankings:\n" + "\n".join([f"{index+1}. {user}: {count}" for index, (user, count) in enumerate(sorted(feature_rankings.items(), key=lambda item: item[1], reverse=True))])
        await ranking_channel.send(issue_ranking_text + "\n\n" + feature_ranking_text)
        logger.info("Rankings updated.")
    except Exception as e:
        logger.error(f"Error updating rankings: {e}")

async def update_rankings_on_startup():
    try:
        logger.info("Updating rankings on startup.")
        guild = bot.get_guild(YOUR_GUILD_ID)
        if guild:
            await update_rankings(guild)
    except Exception as e:
        logger.error(f"Error in update_rankings_on_startup: {e}")

@tasks.loop(minutes=10)
async def rankings_update():
    try:
        logger.info("Updating rankings every 10 minutes.")
        guild = bot.get_guild(YOUR_GUILD_ID)
        if guild:
            await update_rankings(guild)
    except Exception as e:
        logger.error(f"Error in rankings_update: {e}")

@rankings_update.before_loop
async def before_rankings_update():
    await bot.wait_until_ready()

try:
    bot.run(os.getenv('DISCORD_TOKEN'))
except Exception as e:
    logger.error(f"Error running the bot: {e}")
