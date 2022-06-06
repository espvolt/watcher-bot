import json
from pydoc import describe
from attr import field, fields
import discord
import globals
import emoji
import asyncio

from discord.ext import commands
from datetime import datetime
from extensions.misc import blacklistHook
from extensions.reminder import Reminder

def initPollGlobals(eventLoop: asyncio.AbstractEventLoop, bot: commands.AutoShardedBot):
    

    for messageID in globals.pollData:
        eventLoop.create_task(pollFunction(messageID, bot))

async def pollFunction(messageKey: str, bot: commands.AutoShardedBot):
    Poll.savePolls()
    pollData = globals.pollData[messageKey]
    message: discord.Message = pollData["messageObject"]
    fieldData = pollData["fields"]


    try:
        while True:
            embed = discord.Embed()
            description = ""


            total = 0

            for field in fieldData:
                total += len(fieldData[field]["users"])

            if (total == 0):
                total = 10
            for field in fieldData:
                description += f"{field} " + "#" * int(10 * len(fieldData[field]["users"]) / total) + "\n"

            embed.add_field(name="emojis", value = "\n".join([field for field in fieldData]), inline=True)
            embed.add_field(name="message", value = "\n".join([fieldData[field]["message"] for field in fieldData]))
            embed.add_field(name="number", value = "\n".join([str(len(fieldData[field]["users"])) for field in fieldData]))

            await message.edit(embed=embed)

            message = await message.channel.fetch_message(int(messageKey))

            timeoutTime = pollData["targetTime"] - datetime.utcnow().timestamp()
            if (timeoutTime < 0):
                raise Exception
            print("?")
            reaction = await bot.wait_for("raw_reaction_add", timeout=timeoutTime, check=lambda reaction: reaction.message_id == message.id)
            print(reaction)
            user = bot.get_user(reaction.user_id)
            if (str(reaction.emoji) not in fieldData and reaction.emoji != "🚫"):
                await reaction.remove(user)

            else:
                emoji = reaction.emoji
                if (emoji == "🚫"):
                    if (user.permissions_in(reaction.message.channel).administrator):
                        globals.pollData.pop(messageKey)
                        Poll.savePolls()
                        return
                    else:
                        await reaction.remove(user)
                        continue

                hasUser = lambda user, users: any([user.id == usr.id for usr in users])
                getReaction = lambda emoji, message: [reaction for reaction in message.reactions if str(reaction.emoji) == str(emoji)][0]

                if (user.bot):
                    continue
                for field in fieldData:
                    if (str(emoji) == field):
                        continue
                        
                    if (hasUser(user, fieldData[field]["users"])):
                        print(message.reactions)
                        reaction = getReaction(field, message)

                        if (reaction != None):

                            await reaction.remove(user)

                            for i, usr in enumerate(fieldData[field]["users"]):
                                if (usr.id == user.id):
                                    fieldData[field]["users"].pop(i)
                                    break
                            break
                
                if (not hasUser(user, fieldData[str(emoji)]["users"])):

                    fieldData[str(emoji)]["users"].append(user)

                Poll.savePolls()

    except asyncio.TimeoutError:
        globals.pollData.pop(messageKey)
        Poll.savePolls()

class Poll(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @staticmethod
    async def getFields(ctx: commands.Context, bot: commands.AutoShardedBot):
        prefix = globals.prefixData["guilds"][str(ctx.guild.id)]

        descriptionHeader = f"To add a field type `{prefix} <emoji> <message>`\n \
                              To remove a field type `{prefix} remove <emoji>`\n \
                              To cancel making this poll, `{prefix} cancel`\n \
                              To finish making this poll, with at least 1 field filled, `{prefix} finish`, or wait 30 seconds\n \
                              \n"
        
        embed = discord.Embed()
        embed.title = "You have 30 seconds to input a command."
        embed.description = descriptionHeader
        embed.color = discord.Color.from_rgb(0, 200, 0)

        message = await ctx.send(embed=embed)

        res = {}

        try:
            while True:
                check = lambda message: message.author.id == ctx.author.id and message.content.startswith(f"{prefix} ")
                isemoji = lambda string: string in emoji.UNICODE_EMOJI_ENGLISH or (string.startswith("<:") and string.endswith(">"))

                message_ = await bot.wait_for("message", check=check, timeout=30)

                commandContent: str = message_.content[len(prefix) + 1:]

                args = commandContent.split(" ", maxsplit=1)

                arg = args[0]
                arg_ = "" if len(args) <= 1 else args[1]

                footer = ""

                if (isemoji(arg)):
                    if (arg != "🚫"):
                        res[arg] = arg_
                        footer = f"Added {arg}: {arg_}"
                    else:
                        footer = "Emoji cannot be 🚫"

                    await message_.delete()

                else:
                    if (arg.lower() == "remove"):
                        if (arg_ in res):
                            fieldvalue = res.pop(arg_)
                            footer = f"Removed {arg_}: {fieldvalue}"

                        await message_.delete()

                    if (arg.lower() == "finish"):
                        await message.delete()
                        await message_.delete()

                        return res

                    if (arg.lower() == "cancel"):
                        await message.delete()
                        await message_.delete()

                        return None

                    
                newDescription = ""

                for fieldEmoji in res:
                    newDescription += f"{fieldEmoji}: {res[fieldEmoji]}\n"
                
                embed.description = descriptionHeader + newDescription
                embed.set_footer(text=footer)

                await message.edit(embed=embed)



        except asyncio.TimeoutError as e:
            await message.delete()
            await message_.delete()

            if (len(res) > 0):
                return res
            return None


    @staticmethod
    def savePolls():
        saveData = {}

        for messageID in globals.pollData:
            saveData[messageID] = {"channelID": str(globals.pollData[messageID]["messageObject"].channel.id), "fields": {}}
            saveData[messageID]["fields"] = {}
            saveData[messageID]["targetTime"] = globals.pollData[messageID]["targetTime"]

            for field in globals.pollData[messageID]["fields"]:
                fields = globals.pollData[messageID]["fields"]
                saveData[messageID]["fields"][field] = {"message": fields[field]["message"], "users": [str(user.id) for user in fields[field]["users"]]}

        with open("./persistent/polls.json", "w", encoding="utf-8") as f:
            json.dump(saveData, f, indent=4)

    @commands.command()
    async def createpoll(self, ctx: commands.Context, time: str = None):
        await blacklistHook(ctx)

        if (isinstance(ctx.channel, discord.DMChannel)):
            await ctx.send("How about no.")
            return

        fields = await Poll.getFields(ctx, self.bot)

        if (fields is None or len(fields) == 0):
            return

        currentTime = datetime.utcnow().timestamp()
        targetTime = None

        if (time is not None):
            hms = Reminder.getSplitTime(time)
            targetTime = currentTime + hms[0] * 3600 + hms[1] * 60 + hms[2]
        else:
            oneWeek = 604800 
            targetTime = currentTime + oneWeek

        embed = discord.Embed()
        embed.description = "Loading..."
        embed.color = discord.Color.from_rgb(200, 0, 0)

        message_ = await ctx.send(embed=embed)

        for field in fields:
            await message_.add_reaction(field)

        await message_.add_reaction("🚫")
        

        messageID = str(message_.id)

        globals.pollData[messageID] = {}
        globals.pollData[messageID]["targetTime"] = targetTime
        globals.pollData[messageID]["messageObject"] = message_
        globals.pollData[messageID]["fields"] = {}

        fieldsObject = globals.pollData[messageID]["fields"]

        for field in fields:
            fieldsObject[field] = {}
            fieldsObject[field]["message"] = fields[field]
            fieldsObject[field]["users"] = []
        
        loop = asyncio.get_event_loop()
        loop.create_task(pollFunction(messageID, self.bot))

        

        
        

        



    
    


def setup(bot: commands.AutoShardedBot):
    bot.add_cog(Poll(bot))