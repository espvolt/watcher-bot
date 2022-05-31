import json
import discord
import globals
import emoji
import asyncio

from discord.ext import commands
from datetime import datetime
from extensions.misc import blacklistHook


async def pollFunction(options: dict, ctx: commands.Context, bot: commands.AutoShardedBot): # Add comments later
    print("?")
    embed = discord.Embed()
    
    description = Poll.getOptionString(options)
    embed.description = description

    message = await ctx.send(embed=embed)

    for option in options:
        await message.add_reaction(option)

    while True:
        check = lambda reaction, user: reaction.message.id == message.id
        reaction, user = await bot.wait_for("reaction_add", check=check)
        print(reaction.emoji)
    ...

class Poll(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        ...
    
    @staticmethod
    def getOptionString(options: dict): # Returns the option string for embeds
        res = ""
        for option in options:
            res += f"{option} {options[option]}\n"

        return res

    @staticmethod
    def createNewPollData(message: discord.Message, options: dict): # This is a helper function, it helps initialize a new poll in the data
        globals.pollData[str(message.id)] = {} # Uses message id for a key

        currentPoll = globals.pollData[str(message.id)]

        for option in options:
            # Use to track who has reacted to the post    
            currentPoll[option] = {"message": options[option], "users": []} 
        
        currentPoll["messageObject"] = message

    @staticmethod
    def savePollData(): # Comment this stuff later
        with open("./persistent/polls.json", "w") as f:
            newData = {}

            for messageID in globals.pollData:
                currentMessage = globals.pollData[messageID]
                newData[messageID] = {}

                for option in currentMessage:
                    currentOption = currentMessage[option]
                    newData[messageID][currentOption] = {}

                    newData[messageID][currentOption]["message"] = currentOption["message"]
                    newData[messageID][currentOption]["user"] = []
                    for user in currentOption["users"]:
                        newData[messageID][currentOption]["users"].append(str(user.id))
                    
            json.dump(newData, f, indent=4)
    @commands.command()
    async def createpoll(self, ctx: commands.Context, polltype: str="multiple"):
        await blacklistHook(ctx)

        if (isinstance(ctx.channel, discord.DMChannel)): # Why would you make polls in a dm channel
            await ctx.send("How about no?")
            return
        
        polltype = polltype.lower() # Convert to lowercase
        guildID = str(ctx.guild.id)

        if (polltype == "multiple"): # If the user wants a multiple choice type poll
            embed = discord.Embed()

            # Should never be None because when you call a command if the prefix isn't in prefix data its created
            prefix = globals.prefixData["guilds"][guildID] 

            title = f"To add poll options type `{prefix} <emoji> <text>`.\nTo cancel `{prefix} cancel`.\nTo finish `{prefix} end`"
            description = "Current Options: \n" # Put all current options in this string

            embed.description = description
            embed.title = title

            embed.color = discord.Color.from_rgb(0, 200, 0) # Green color for the embed
            embed.set_footer(text="You have 20 seconds to input next command")

            message: discord.Message = await ctx.send(embed=embed)
            
            options = {}

            loop = asyncio.get_event_loop()

            try:
                while True:
                    check = lambda message: message.author.id == ctx.author.id and message.content.startswith(f"{prefix} ")
                    msg: discord.Message = await self.bot.wait_for("message", check=check, timeout=20)


                    commandargs = []

                    commandprefixremoved = msg.content[len(prefix) + 1:] # Removes '<prefix> 'cancel example: w! cancel -> cancel

                    # Since we only want the first arg seperated by a space we do this 
                    # Example: w! :green_square: Ban espvolt -> [":green_square:", "Ban espvolt"]
                    split = commandprefixremoved.split(" ")
                    commandargs.append(split[0])

                    if (len(split) > 1): # Checks if additional arguments were given
                        # [":green_square:", "Ban", "espvolt"] -> "Ban espvolt"
                        commandargs.append(" ".join(split[1:]))

                    option1 = commandargs[0]

                    

                    option2 = None

                    if (len(commandargs) > 1):
                        option2 = commandargs[1]
                    else:
                        option2 = ""

                    if (option1 == "cancel"):
                        await message.delete()
                        await msg.delete()
                        return

                    if (option1 == "end"):
                        await message.delete()
                        await msg.delete()
                        
                        # Currently will not continue if the bot goes offline, maybe do that later
                        loop.create_task(pollFunction(options, ctx, self.bot)) 
                        return

                        # Make async function here.

                    if (option1 == "remove"): 
                        # Checks if its an emoji or a custom emomji
                        if (option2 in emoji.UNICODE_EMOJI_ENGLISH or (option1.startswith("<:") and option1.endswith(">"))): 
                            if (option2 in options): # Checks if an option has been made with that emoji
                                options.pop(option2) # Removes it from current options
                                embed.description = Poll.getOptionString(options) # Edit original message to display all current options
                                
                                await message.edit(embed=embed)
                            await msg.delete()

                    if (option1 in emoji.UNICODE_EMOJI_ENGLISH or (option1.startswith("<:") and option1.endswith(">"))):
                        options[option1] = option2
                        embed.description = Poll.getOptionString(options) 


                        await message.edit(embed=embed)
                        await msg.delete()

                    else: # Means first argument isn't valid
                        await msg.delete()
                        
                    






                    

                    

                    ...
            except Exception as e: # Means it probably, hopefully timed out
                await message.delete()

                if (len(options) > 0):
                    loop.create_task(pollFunction(options, ctx, self.bot)) 

                    return


def setup(bot: commands.AutoShardedBot):
    bot.add_cog(Poll(bot))