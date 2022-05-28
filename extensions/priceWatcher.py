import discord
import asyncio
import globals
import json
import validators

from discord.ext import commands
from urllib.parse import urlparse
from util.scrapers import getLowestG2APrice
from extensions.misc import blacklistHook


async def printPriceLoop():
    while (True):
        linkPrices = {}

        for channelID in globals.priceData:
            links = globals.priceData[channelID]["links"]

            for link in links:
                # Checks if the price of a specific link has already been found, don't want to make unneccesary requests
                if (link not in linkPrices):
                    parsedUrl = urlparse(link).netloc # Makes it easier to figure out which scraper to use

                    price = None

                    match parsedUrl:
                        case "www.g2a.com":
                            price = await getLowestG2APrice(link)
                                
                    
                    linkPrices[link] = price

        

        newData = {}
        for channelID in globals.priceData:
            channel = globals.priceData[channelID]["channelObject"]
            links = globals.priceData[channelID]["links"]

            for link in links:
                currentPrice = linkPrices[link]
                newData[channelID] = {}
                newData[channelID][link] = links[link] # Set to previous values, and override them if they are needed
                

                if (currentPrice == None): # There was an error, probably a time out, just apply previous and skip
                    continue

                previousPrice = links[link]["lastPrice"]
                threshold = links[link]["differenceThreshold"]

                # Price is over threshold, notify channel and update data in both globals and prices.json
                if (abs(previousPrice - currentPrice) > abs(threshold)): 
                    updateData = {
                        "lastPrice": currentPrice,
                        "differenceThreshold": threshold
                    }

                    newData[channelID][link] = updateData
                    globals.priceData[channelID]["links"][link] = updateData

                    description = f"{link}\n"
                    
                    embed = discord.Embed(title=f"Price change", url=link)
                    if (previousPrice == -1): # Means this is the first time a price is detected
                        description = f"First time detection: {currentPrice}"
                    elif (previousPrice > currentPrice):
                        description += f"Price drop from {previousPrice} to {currentPrice}"
                        embed.color = discord.Color.from_rgb(0, 200, 0)
                    elif (previousPrice < currentPrice):
                        description += f"Price rise from {previousPrice} to {currentPrice}"
                        embed.color = discord.Color.from_rgb(200, 0, 0)


                    embed.description = description

                    await channel.send(embed=embed)



        
        with open("./persistent/prices.json", "w") as f:
            json.dump(newData, f, indent=4)



                


        await asyncio.sleep(10)


class PriceWatcher(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @staticmethod
    def savePrices(): # Needs to be called from other places
        with open("./persistent/prices.json", "w") as f:
            saveData = {}

            for channelID in globals.priceData:
                saveData[channelID] = globals.priceData[channelID]["links"]
            
            json.dump(saveData, f, indent=4)

    @commands.command()
    async def watchprice(self, ctx: commands.Context, link: str, difference: float=0):
        await blacklistHook(ctx)

        channelID = str(ctx.channel.id)

        if (not link.endswith("/")): # google.com/ is the same as google.com
            link += "/"

        if (not validators.url(link)):
            await ctx.send(f"`{link}` is not a valid url")
            return
            
        if (channelID not in globals.priceData): # Initialises channel in priceData
            globals.priceData[channelID] = {"links": {}, "channelObject": ctx.channel}
           
        if (link in globals.priceData[channelID]["links"]): # The link is already in the priceData so just ignore
            await ctx.send(f"`{link}` is already being watched. Use `stopwatching <link>` to stop watching this link")
            return

        channelLinks = globals.priceData[channelID]["links"]

        channelLinks[link] = {
            "lastPrice": -1,
            "differenceThreshold": difference
        }

        PriceWatcher.savePrices()
        await ctx.send(f"`{link}` is being watched in `{ctx.channel.name}`")

    
    @commands.command()
    async def stopwatching(self, ctx: commands.Context, link: str):
        channelID = str(ctx.channel.id)

        if (not link.endswith("/")):
            link += "/"
        
        if (not validators.url(link)):
            await ctx.send(f"`{link}` is not a valid url")
            return

        if (channelID not in globals.priceData):
            globals.priceData[channelID] = {"links": {}, "channelObject": ctx.channel}

        if (link not in globals.priceData[channelID]["links"]):
            await ctx.send(f"`{link}` was not found in current text channel. Use `watchprice <link>` to watch a link")
            return
        
        globals.priceData[channelID]["links"].pop(link)

        PriceWatcher.savePrices()
        await ctx.send(f"`{link}` is no longer being watched in `{ctx.channel.name}`")


    

def setup(bot: commands.AutoShardedBot):
    bot.add_cog(PriceWatcher(bot))
    