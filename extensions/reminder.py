from math import trunc
from os import access
from pprint import pprint
from sre_constants import CH_LOCALE
import discord
import asyncio
import globals
import json

from discord.ext import commands
from datetime import datetime
from copy import copy
from extensions.misc import blacklistHook

def initReminderGlobals(eventLoop: asyncio.AbstractEventLoop):
    for channelID in globals.reminderData: # This is to check reminders that should have already been removed, usually when the bot is offline
        channelData = globals.reminderData[channelID]

        for userID in channelData["users"]:
            userData = channelData["users"][userID]
            
            for reminderKey in userData: # This entire section just loads reminders
                currentTime = datetime.utcnow().timestamp()

                targetTime = userData[reminderKey]["targetTime"]
                nextTime = userData[reminderKey]["nextTime"]
                if (currentTime > targetTime):
                    if (nextTime != None): # If the reminder in looping then it has to create a new task
                        # Say this starts at 0, with intervals of 30, and the bot is offline for 12 seconds. 12 % 30 = 12, 30 - 12 = 28
                        # Wait 28 seconds.
                        # This is getting really bad
                        newTime = userData[reminderKey]["nextTime"] - ((currentTime - targetTime) % userData[reminderKey]["nextTime"])
                        userData[reminderKey]["functionObject"] = eventLoop.create_task(reminderFunction(newTime,
                        nextTime,
                        userData,
                        reminderKey,
                        channelData["channelObject"]))
                    else:
                        userData[reminderKey]["functionObject"] = eventLoop.create_task(reminderFunction(0,
                        None,
                        userData,
                        reminderKey,
                        channelData["channelObject"]))

                else:
                    userData[reminderKey]["functionObject"] = eventLoop.create_task(reminderFunction(targetTime - currentTime,
                        nextTime,
                        userData,
                        reminderKey,
                        channelData["channelObject"]))


async def reminderFunction(
        timeToWait: float, 
        timeInterval: float, 
        accessDict: dict, 
        reminderKey: str, 
        channel: discord.TextChannel): # This is really, really bad

    accessDict[reminderKey]["targetTime"] = datetime.utcnow().timestamp() + timeToWait # Quickly updates the reminderData cause sometimes it breaks

    await asyncio.sleep(timeToWait)
    await channel.send(accessDict[reminderKey]["message"])

    if (timeInterval is not None):
        while True:
            accessDict[reminderKey]["targetTime"] = datetime.utcnow().timestamp() + timeInterval
            Reminder.saveReminders()
            await asyncio.sleep(timeInterval)
            await channel.send(accessDict[reminderKey]["message"])

    else:
        accessDict.pop(reminderKey)
        Reminder.saveReminders()

class Reminder(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @staticmethod
    def getSplitTime(string: str):
        split = string.split(":")
        hours = 0
        minutes = 0
        seconds = 0

        try:
        # If the user gives 6:00 it will error on seconds, so keep seconds at 0
            hours = int(split[0])
            minutes = int(split[1])
            seconds = int(split[2])
        except:
            ...

        return [hours, minutes, seconds]

    @staticmethod
    def saveReminders():
        with open("./persistent/reminders.json", "w") as f:
            saveData = {}

            for channelID in globals.reminderData: # I dont need the 'users' key 
                channelData = globals.reminderData[channelID]["users"]

                saveData[channelID] = {} #Initialises channelID key

                for userID in channelData: # This part removes the functionObject, json can't hash it
                    saveData[channelID][userID] = {}

                    for reminderKey in channelData[userID]: 
                        # Very annoying workaround, I cant make a copy of the reminderData or the functionObject gets deleted for somereason,
                        # probably because its non copyable
                        saveData[channelID][userID][reminderKey] = {}
                        reminderData = saveData[channelID][userID][reminderKey]
                        
                        reminderData["message"] = channelData[userID][reminderKey]["message"]
                        reminderData["nextTime"] = channelData[userID][reminderKey]["nextTime"]
                        reminderData["targetTime"] = channelData[userID][reminderKey]["targetTime"]

                        

                        
                    
            json.dump(saveData, f, indent=4)

    @commands.command()
    async def remindme(self, ctx: commands.Context, timetowait: str, intervalTime: str, *, message):
        """
        Set <intervalTime> to '.' to have no interval, times should be formatted as '<hours>:<minutes>:<seconds>'
        """

        await blacklistHook(ctx)

        timeHMS = Reminder.getSplitTime(timetowait)
        secondsToWait = timeHMS[0] * 3600 + timeHMS[1] * 60 + timeHMS[2] # 3600 seconds in an hour, 60 seconds in a minute
        targetTime = datetime.utcnow().timestamp() + secondsToWait # If the bot is ever offline I need to preserve this value

        channelID = str(ctx.channel.id)
        userID = str(ctx.author.id)

        if (channelID not in globals.reminderData):
            globals.reminderData[channelID] = {"users": {}, "channelObject": ctx.channel}

        if (userID not in globals.reminderData[channelID]["users"]):
            globals.reminderData[channelID]["users"][userID] = {}

        currentUser = globals.reminderData[channelID]["users"][userID]



        if (intervalTime == "."): # If they want an inteval say, remind them in 8 hours then 6 hours after that set intervalTime = 6:00:00
            intervalTime = None

        nextTimeToWait = None

        if (intervalTime is not None):
            nextTimeHMS = Reminder.getSplitTime(intervalTime)
            nextTimeToWait = nextTimeHMS[0] * 3600 + nextTimeHMS[1] * 60 + nextTimeHMS[2]

        userKey = str(int(datetime.utcnow().timestamp())) # I dont want milliseconds, truncates the float
        loop = asyncio.get_event_loop()
        
        currentUser[userKey] = {} # Uses current time as the unique key of the reminder
        currentUser[userKey]["message"] = message
        currentUser[userKey]["targetTime"] = targetTime
        currentUser[userKey]["nextTime"] = nextTimeToWait
        currentUser[userKey]["functionObject"] = None

        currentUser[userKey]["functionObject"] = loop.create_task( # I need this if the reminder loops and I need to end the task later
            reminderFunction(secondsToWait, nextTimeToWait, currentUser, userKey, ctx.channel))

        Reminder.saveReminders()
        await ctx.send(f"✅ reminder created, will remind in {timeHMS[0]}:{timeHMS[1]}:{timeHMS[2]}")

    @staticmethod 
    def killReminder(channelID: str, userID: str, reminderKey: str):
        # Kills the background function
        globals.reminderData[channelID]["users"][userID][reminderKey]["functionObject"].cancel()
        globals.reminderData[channelID]["users"][userID].pop(reminderKey)

        Reminder.saveReminders()

    @staticmethod
    def getReminderDescription(reminderObject):
        numCharacters = 15
        currentTime = datetime.utcnow().timestamp()

        

        targetTime = reminderObject["targetTime"]

        truncatedMessage = reminderObject["message"] # If a message is > 10 characters reduce it to its 7th letter and add '...'
        
        if (len(truncatedMessage) > numCharacters):
            truncatedMessage = truncatedMessage[:numCharacters - 4] + "..."

        delta = targetTime - currentTime
        # Kind of gross but heres the rundown 3666 3666 // 3600 = 1, 3666 - 3600 * 1 = 66 66 // 60 = 1, 66 - 60 * 1 = 6
        hours = int(delta / 3600)
        delta -= hours * 3600
        minutes = int(delta / 60)
        seconds = int(delta - minutes * 60)

        return f"{truncatedMessage} in {hours}:{minutes}:{seconds}"


    @commands.command()
    async def cancelreminder(self, ctx: commands.Context):
        await blacklistHook(ctx)

        channelID = str(ctx.channel.id)
        userID = str(ctx.author.id)

        # Basic checks
        if (channelID not in globals.reminderData):
            globals.reminderData[channelID] = {"users": {}, "channelObject": ctx.channel}

        if (userID not in globals.reminderData[channelID]["users"] or globals.reminderData[channelID]["users"][userID] == {}): 
            await ctx.send("You don't have any reminders in this channel, use `remindme <timetowait> <intervalTime> <message>` to create a reminder")
            return
        
        reminders = globals.reminderData[channelID]["users"][userID]
        numReminders = len(reminders)

        emoticonDict = {
            "🟩": 0,
            "🟥": 1,
            "🟪": 2,
            "🟦": 3,
            "🟧": 4
        }

        embed = discord.Embed()
        embed.color = discord.Color.from_rgb(200, 0, 0)
        
        if (numReminders <= 5):
            description = ""
            reminderIndex = 0
            emoticonKeys = list(emoticonDict.keys())
            reminderKeys = list(reminders.keys())


            while (reminderIndex < numReminders): # Assign each reminder to a color
                reminderKey = reminderKeys[reminderIndex]
                emoticonKey = emoticonKeys[reminderIndex]

                message = Reminder.getReminderDescription(reminders[reminderKey])
                description += f"{emoticonKey} {message}\n"
                
                reminderIndex += 1
            
            embed.description = description
            # It takes some time to add reactions, so we'll edit the message to when they can use the emojis
            embed.title = "Wait until color is green..." 


            message: discord.Message = await ctx.send(embed=embed)
            for i in range(numReminders): # Add reactions the user can click on to choose what reminder to cancel
                emoticon = emoticonKeys[i]
                # emojiObject = discord.Emoji()
                # emojiObject.name = emoticon
                await message.add_reaction(emoticon)


            embed.color = discord.Color.from_rgb(0, 200, 0)
            embed.title = "You have 20 seconds to decide..."
            await message.edit(embed=embed) # Edit it so that the user knows the can add reactions
            try:
                # Makes sure its the same user and the same message.
                check = lambda reaction, user: user.id == ctx.author.id and reaction.message.id == message.id
                reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=20)
            except: # Means the wait_for timed out, basically they took 20 seconds, delete both messages
                await message.delete()
                if (not isinstance(ctx.channel, discord.DMChannel)): # Cant delete messages in DMChannels
                    await ctx.message.delete()
                return

            # Reaction is the emoji they reacted with find the index of the emoji using the list of keys
            index = emoticonKeys.index(reaction.emoji)
            reminderKey = reminderKeys[index] # Get what reminder they chose

            await message.delete()
            
            Reminder.killReminder(channelID, userID, reminderKey)

            await ctx.send("✅ reminder deleted.")
        else: # Too many, so just ask for a number
            reminderKeys = list(reminders.keys()) # Need to find a key by index, based on what the user inputs

            embed.title = "You have 20 seconds to decide..."
            embed.color = discord.Color.from_rgb(0, 200, 0)
            embed.set_footer(text="Input the reminder number you want to remove")

            value = ""
            num = 0

            for reminderKey in reminders:
                message = Reminder.getReminderDescription(reminders[reminderKey])
                value += f"`{num + 1}:` {message}\n" # + 1 because its easier to read
                
                num += 1
            
            embed.add_field(name=f"reminders", value=value)
            # Makes sure its a number
            
            check = lambda message: message.author.id == ctx.author.id and message.id == message.id and message.content.isnumeric()
            message = await ctx.send(embed=embed)
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=20)
            except:
                await message.delete()
                if (not isinstance(ctx.channel, discord.DMChannel)): # Cant delete messages in DMChannels
                    await ctx.message.delete()
                return
            
            index = int(msg.content) - 1 # - 1 because they are shown 1 value higher to make it easier to read

            reminderKey = reminderKeys[index]
            
            await message.delete()

            Reminder.killReminder(channelID, userID, reminderKey)
            await ctx.send("✅ reminder deleted.")


            
            


                            


def setup(bot: commands.AutoShardedBot):
    bot.add_cog(Reminder(bot))