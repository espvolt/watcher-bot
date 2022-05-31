import discord
import globals

from discord.ext import commands
from extensions.misc import blacklistHook

class Poll(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        ...

    @commands.command()
    async def createpoll(self, ctx: commands.Context, type: str="multiple"):
        await blacklistHook(ctx)


        if (isinstance(ctx.channel, discord.DMChannel)): # Why would you make polls in a dm channel
            await ctx.send("How about no?")
            return
        
        type = type.lower() # Convert to lowercase
        guildID = str(ctx.guild.id)

        if (type == "multiple"): # If the user wants a multiple choice type poll
            embed = discord.Embed()

            # Should never be None because when you call a command if the prefix isn't in prefix data its created
            prefix = globals.prefixData[guildID] 

            title = f"To add poll options type `{prefix} <emoji> <text>` `{prefix} cancel` to cancel"
            description = "Current Options: \n" # Put all current options in this string

            embed.description = description
            embed.title = title

            embed.color = discord.Color.from_rgb(0, 200, 0) # Green color for the embed
            embed.set_footer(text="You have 20 seconds to input next command")

            message = await ctx.send(embed=embed)
            
            try:
                while True:
                    check = lambda message: message.author.id == ctx.author.id and message.content.startswith(f"{prefix} ")
                    msg: discord.Message = await self.bot.wait_for("message", check=check, timeout=20)

                    print(msg.content)
                    

                    

                    ...
            except:
                ...
def setup(bot: commands.AutoShardedBot):
    bot.add_cog(Poll(bot))