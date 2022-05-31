import discord
import json
import globals

from discord.ext import commands

class BlackListError(Exception):
    ...

async def blacklistHook(ctx: commands.Context): # use before_invoke for every command now
    if (isinstance(ctx.channel, discord.DMChannel)): # commands in dmchannels cant be blacklisted
        return
        
    authorID = str(ctx.author.id)
    guildID = str(ctx.guild.id)
    
    permissions: discord.Permissions = ctx.author.permissions_in(ctx.channel)
    if (permissions.administrator): # They're admin so they can do anything
        return

    if (guildID in globals.blacklistData): # Just checks if the data exists, if it doesnt, no need to create new data
        
        if (authorID in globals.blacklistData[guildID]):
            blacklistedCommands = globals.blacklistData[guildID][authorID]
            commandName = ctx.command.qualified_name

            if (commandName in blacklistedCommands):
                await ctx.send("You are blacklisted from using this command")
                raise BlackListError

class Misc(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    
    
    @staticmethod
    def savePrefixes():
        with open("./persistent/prefixes.json", "w") as f:
            json.dump(globals.prefixData, f, indent=4)

    @commands.Cog.listener("on_command_error")
    async def error_handler(self, ctx: commands.Context, error):
        # Means it might be from a blacklisted command not all commands have .original
        if (isinstance(error, commands.errors.CommandInvokeError)): 
            if (isinstance(error.original, BlackListError)): 
                return

        await ctx.send(error)
        raise error

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def prefix(self, ctx: commands.Context, newPrefix: str):
        message = ctx.message

        if (newPrefix == ""):
            await ctx.send("New prefix cannot be none")

        if (isinstance(message.channel, discord.channel.DMChannel)): # The message was in a direct message text channel
            channelID = str(message.channel.id) # Convert to string because json doesnt support integer keys

            if (not channelID in globals.prefixData["dmChannels"]):
                # If the channel the user is DMing the bot from isn't found, add default prefix to ./persistent/prefixes.json and the prefixData
                globals.prefixData["dmChannels"][channelID] = ""

            globals.prefixData["dmChannels"][channelID] = newPrefix
            
                
            Misc.savePrefixes()
        else: # The message was in a guild text channel
            guildID = str(message.guild.id)

            if (not guildID in globals.prefixData["guilds"]):
                # If the guild the user is calling the bot from isn't found, add default prefix to ./persistent/prefixes.json and the prefixData
                globals.prefixData["guilds"][guildID] = ""

            globals.prefixData["guilds"][guildID] = newPrefix
            

            Misc.savePrefixes()
            
            ...

        await ctx.send("✅ New prefix set")

    @staticmethod
    def saveBlacklist():
        with open("./persistent/blacklist.json", "w") as f:
            json.dump(globals.blacklistData, f, indent=4)

    

    @commands.command()
    async def blacklist(self, ctx: commands.Context, target: str, *commandlist):
        if (isinstance(ctx.message.channel, discord.channel.DMChannel)):
            await ctx.send("How about no?")
            return

        
        

        guildID = str(ctx.guild.id)
        # userID = str(target)

        if (guildID not in globals.blacklistData):
            globals.blacklistData[guildID] = {}

        if ("server" not in globals.blacklistData[guildID]):
            globals.blacklistData[guildID]["server"] = []

        data = globals.blacklistData[guildID]
        log = "```"
        botCommands = [command.qualified_name for command in self.bot.commands]

        if (commandlist == ()): # No commands were given so they probably want to view the blacklist
            message = "```"

            if (target == "."):
                serverData = data["server"]

                message += f"{ctx.guild.name}'s blacklist\n"
                
                for command in serverData:
                    message += f"\t{command}\n" # \t for an indent, basically a tab
            else:
                userID = target[2:-1]
                user: discord.User = await self.bot.fetch_user(int(userID))

                if (userID not in data):
                    data[userID] = []

                userData = data[userID]

                message += f"{user.name}'s blacklist\n"



                for command in userData:
                    message += f"\t{command}\n"

            await ctx.send(f"{message}```")
            return

        if (not ctx.author.permissions_in(ctx.channel).administrator): # Checks if the user is an admin, so they can set blacklists
            await ctx.send("You are not an administrator")
            return

        if (target == "."): # It means they want this serverwide
            serverData = data["server"]

            for command in commandlist: # Iterate through all commands given
                if (command not in botCommands): # The command is not a valid command, so skip
                    log += f"{command} is not a valid command\n"
                    continue

                if (command in serverData): # The command is already blacklisted to unblacklist it
                    serverData.remove(command)
                    log += f"{command} removed from blacklist\n"
                else:
                    serverData.append(command)
                    log += f"{command} added to blacklist\n"
                
        else: # Means its just for that user
            # User @'s are formatted like <@<userID>> we just want userID
            
            userID = target[2:-1]
            # Why can't I use get_user()? I have no clue
            user: discord.User = await self.bot.fetch_user(int(userID))

            if (userID not in data):
                data[userID] = []

            userData = data[userID]


            for command in commandlist: # Iterate through all commands given
                if (command not in botCommands): # The command is not a valid command, so skip
                    log += f"{command} is not a valid command\n"
                    continue

                if (command in userData): # The command is already blacklisted to unblacklist it
                    userData.remove(command)
                    log += f"{command} removed from blacklist for {user.name}\n"
                else:
                    userData.append(command)
                    log += f"{command} added to blacklist for {user.name}\n"

        Misc.saveBlacklist()
        await ctx.send(f"{log}```")


def setup(bot: commands.AutoShardedBot):
    bot.add_cog(Misc(bot))