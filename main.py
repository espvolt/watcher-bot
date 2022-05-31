import configparser
from datetime import datetime
import discord
import sys
import os
import json
import globals
import asyncio

from discord.ext import commands
from extensions.priceWatcher import printPriceLoop
from extensions.reminder import reminderFunction, initReminderGlobals
from extensions.misc import Misc
from pprint import pprint

class Main(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot


    async def initPersistent(self):
        """
        Initializes files in the persistent folder. files that aren't present are created and properly initialized
        """

        prefixData = None

        if (not os.path.exists("./persistent")):
            os.mkdir("./persistent")

        if (os.path.exists("./persistent/prefixes.json")):
            with open("./persistent/prefixes.json", "r") as f:
                prefixData = json.load(f)

        else:
            with open("./persistent/prefixes.json", "w") as f: # Creates prefixes.json file
                prefixData = {
                    "guilds": {},
                    "dmChannels": {}
                }

                json.dump(prefixData, f, indent=4)

        priceData = None

        if (os.path.exists("./persistent/prices.json")):
            with open("./persistent/prices.json", "r") as f:
                data = json.load(f)
                priceData = {}
                for channelID in data:
                    # Guild ID is already string because it is from the json file
                    # Saving data in a dict so the bot doesnt have to get the channel each time it wants to print a price
                    # fetch_channel because DMChannels dont work.
                    priceData[channelID] = {"links": data[channelID], "channelObject": await self.bot.fetch_channel(int(channelID))}

        else:
            with open("./persistent/prices.json", "w") as f:
                priceData = {}

                json.dump(priceData, f, indent=4)

        reminderData = None

        if (os.path.exists("./persistent/reminders.json")):
            with open("./persistent/reminders.json") as f:
                data = json.load(f)
                reminderData = {}
                for channelID in data:
                    newData = {}

                    for userID in data[channelID]: # We need to add an async function for each reminder
                        currentUser = data[channelID][userID]
                        newData[userID] = {}
                        for reminderKey in currentUser:
                            currentReminder = currentUser[reminderKey]

                            newData[userID][reminderKey] = {}

                            newData[userID][reminderKey]["message"] = currentReminder["message"]
                            newData[userID][reminderKey]["targetTime"] = currentReminder["targetTime"]
                            newData[userID][reminderKey]["nextTime"] = currentReminder["nextTime"]

                            newData[userID][reminderKey]["functionObject"] = None

                    reminderData[channelID] = {"users": newData, "channelObject": await self.bot.fetch_channel(int(channelID))}

        else:
            with open("./persistent/reminders.json", "w") as f:
                reminderData = {}

                json.dump(reminderData, f, indent=4)

        blacklistData = None

        if (os.path.exists("./persistent/blacklist.json")):
            with open("./persistent/blacklist.json", "r") as f:
                blacklistData = json.load(f)
        else:
            with open("./persistent/blacklist.json", "w") as f:
                blacklistData = {}
                json.dump(blacklistData, f, indent=4)

        globals.reminderData = reminderData
        globals.prefixData = prefixData
        globals.priceData = priceData
        globals.blacklistData = blacklistData

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        """
        Basic on ready function. Changes activity and initializes persistent files
        """

        await self.initPersistent()
        print("Bot is ready.")

        # Run the loop that prints the prices its watching
        eventLoop = asyncio.get_event_loop()
        eventLoop.create_task(printPriceLoop())

        initReminderGlobals(eventLoop)

        url = "espvolt/watcher-bot"
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=url)) 
    
    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send("pong")


def getCommandPrefix(bot: commands.AutoShardedBot, msg: commands.Context):
    """
    Checks the given message channel/guild id and checks if it is stored. If it is, it returns that prefix.
    If not it returns default prefix and saves it to persistent
    """

    if (isinstance(msg.channel, discord.channel.DMChannel)): # The message was in a direct message text channel
        channelID = str(msg.channel.id) # Convert to string because json doesnt support integer keys

        if (not channelID in globals.prefixData["dmChannels"]):
            # If the channel the user is DMing the bot from isn't found, add default prefix to ./persistent/prefixes.json and the prefixData
            globals.prefixData["dmChannels"][channelID] = "w!"
            
            Misc.savePrefixes()

        return globals.prefixData["dmChannels"][channelID]

    else: # The message was in a guild text channel
        guildID = str(msg.guild.id)

        if (not guildID in globals.prefixData["guilds"]):
            # If the guild the user is calling the bot from isn't found, add default prefix to ./persistent/prefixes.json and the prefixData
            globals.prefixData["guilds"][guildID] = "w!"

            Misc.savePrefixes()
            
        return globals.prefixData["guilds"][guildID]


def loadExtensions(bot: commands.AutoShardedBot, dir: str):
    """
    Loads extensions in a given directory
    """

    extensionName = dir
    if (dir.startswith("./")):
        # Removes './' from the filename as python extensions require this (example: ./folder/extention.py) -> folder.extention
        extensionName = extensionName[2:] 
    
    if (extensionName.endswith("/") or extensionName.endswith("\\")): # Removes ending '/' or '\\'
        extensionName = extensionName[:-1]

    extensionName = extensionName.replace("\\", "/").replace("/", ".") # Replaces all '\\' and '/' with '.'

    for file in os.listdir(dir):
        if (os.path.isfile(f"{dir}/{file}")):
            if (file.endswith(".py")):
                bot.load_extension(f"{extensionName}.{file[:-3]}") # '[:-3]' removes '.py' file extension


def main(argv: list[str]):
    intents = discord.Intents.default()
    intents.members = True

    config = configparser.ConfigParser()
    config.read("./config.ini")

    token = config["GLOBALS"]["DISCORD_BOT_TOKEN"]

    bot = commands.AutoShardedBot(command_prefix=getCommandPrefix, case_insensitive=True, intents=intents)

    bot.add_cog(Main(bot))
    loadExtensions(bot, "./extensions")

    bot.run(token)


if (__name__ == "__main__"):
    main(sys.argv)
