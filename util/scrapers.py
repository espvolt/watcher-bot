import aiohttp
from bs4 import BeautifulSoup

async def getLowestG2APrice(url: str):
    html = None

    try:
        # Session headers because G2A blocks certain requests without the correct headers
        sessionHeaders = {
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36"
        }

        async with aiohttp.ClientSession(headers=sessionHeaders) as session:
            async with session.get(url) as request:
                html = await request.text()

    except: # Request timed out
        return None

    try:

        soup = BeautifulSoup(html, "html.parser")
        # Finds the display prices of the product, the one usually above "Buy with G2A Plus"
        displayPrices = soup.find_all("div", attrs={"data-locator": "ppa-payment"})
        # Finds the listed prices of all sellers, usually at the bottom of the page
        # G2A has a premium membership that allows cheaper prices,
        # But since most people dont use it, we dont want it, so we must look for 'ppa-payment' instead of 'ppa-payment-plus'
        listedPrices = soup.find_all("div", attrs={"data-locator": "ppa-offers-list__price"})
        # Sometimes a listed price is better than the display price, for some reason, only checks the first few, because of limitations with requests

        displayPrice = None

        # Usually there is only one tag with 'ppa-payment' as an attribute, and it contains the display price of the product
        price = displayPrices[0].findChildren("span", attrs={"data-locator": "zth-price"})[0]
        
        displayPriceAsString: str = price.text

        if (displayPriceAsString.startswith("$")): # Usually is formatted as '$ xx.xx', we only want 'xx.xx'
            displayPrice = float(displayPriceAsString[2:])
        else:
            displayPrice = float(displayPriceAsString) # Just a backup, hopefully will never get called

        bestListedPrice = None
        minListedPrice = -1
        if (len(listedPrices) > 0): # Sometimes there is only one seller
            for tag in listedPrices:
                # This will usually only have one element which contains the price
                price = tag.findChildren("span", attrs={"data-locator": "zth-price"})[0] 

                priceAsString = price.text
                priceAsFloat = None

                if (priceAsString.startswith("$")): # Usually is formatted as '$ xx.xx', we only want 'xx.xx'
                    priceAsFloat = float(priceAsString[2:])
                else:
                    priceAsFloat = float(priceAsString) # Just a backup, hopefully will never get called

                if (minListedPrice == -1):
                    minListedPrice = priceAsFloat
                else:
                    minListedPrice = min(minListedPrice, priceAsFloat)

                
        return min(minListedPrice, displayPrice)
    except:
        return None