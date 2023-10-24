# __________                  __             __     ________             .___ 
# \______   \  ____    ____  |  | __  ____ _/  |_  /  _____/   ____    __| _/ 
#  |       _/ /  _ \ _/ ___\ |  |/ /_/ __ \\   __\/   \  ___  /  _ \  / __ |  
#  |    |   \(  <_> )\  \___ |    < \  ___/ |  |  \    \_\  \(  <_> )/ /_/ |  
#  |____|_  / \____/  \___  >|__|_ \ \___  >|__|   \______  / \____/ \____ |  
#         \/              \/      \/     \/               \/              \/  
#
# Dark Web Onion Search Discord Bot by RocketGod
# TOR Browser needs to be connected to the TOR Network

import os
import json
import logging
import traceback
import asyncio
import time
import discord
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from discord import Embed
from selenium import webdriver
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO)

def load_config():
    try:
        with open('config.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return None

async def __get_page_resource(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html_content = BeautifulSoup(await response.text(), "html.parser")
            return html_content

async def get_hidden_services(query: str, result_count: int, time_frame: str = "all"):
    try:
        encoded_query = quote_plus(query)
        response_content = await __get_page_resource(f"https://ahmia.fi/search/?q={encoded_query}&d={time_frame}")
        
        results = await asyncio.to_thread(lambda: response_content.find_all('li', {'class': 'result'}))
        links = []

        for index, result in enumerate(results, start=1):
            url = result.find('cite').text
            links.append(url)

            if index == result_count:
                break

        return links
    except Exception as e:
        logging.error(f"Error in get_hidden_services: {e}")
        raise

async def async_get_screenshot_of_onion_site(client, url: str) -> str:
    try:
        PROXY = "127.0.0.1:9150"  # Default Tor SOCKS proxy
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f"--proxy-server=socks5://{PROXY}")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")

        if not url.startswith("http://"):
            url = "http://" + url

        screenshot_name = await client.loop.run_in_executor(None, lambda: _synchronous_screenshot(url, chrome_options))

        return screenshot_name

    except TimeoutException:
        logging.error(f"Timeout error fetching screenshot for URL: {url}")
        raise
    except Exception as e:
        logging.error(f"Error fetching screenshot for URL {url}: {e}")
        raise

def _synchronous_screenshot(url, chrome_options):
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)  
    try:
        driver.get(url)
        screenshot_name = f"screenshot_{time.time()}.png"
        driver.save_screenshot(screenshot_name)
    except TimeoutException:
        logging.warning(f"Page load timeout for URL: {url}")
        screenshot_name = None
    finally:
        driver.quit()
        del driver
    return screenshot_name

class aclient(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = discord.app_commands.CommandTree(self)
        self.activity = discord.Activity(type=discord.ActivityType.watching, name="/onion")
        self.discord_message_limit = 2000

async def handle_errors(interaction, error, error_type="Error"):
    error_message = "An error occurred while processing your request. Please try again later."
    logging.error(f"Error for user {interaction.user}: {error_message}") 
    try:
        if interaction.response.is_done():
            await interaction.followup.send(error_message)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)
    except discord.HTTPException as http_err:
        logging.warning(f"HTTP error while responding to {interaction.user}: {http_err}")
        await interaction.followup.send(error_message)
    except Exception as unexpected_err:
        logging.error(f"Unexpected error while responding to {interaction.user}: {unexpected_err}")
        await interaction.followup.send("An unexpected error occurred. Please try again later.")

def run_discord_bot(token):
    client = aclient()

    @client.event
    async def on_ready():
        await client.tree.sync()
        logging.info(f'{client.user} is online.')

    @client.tree.command(name="onion", description="Search for a query on the dark web")
    async def onion_search(
        interaction: discord.Interaction,
        query: str,
        time_frame: str = "all"
    ):
        """
        :param query: The query to search on the dark web.
        :param time_frame: Time frame for search. 'all' (Any Time), '1' (Last Day), '7' (Last Week), or '30' (Last Month). Defaults to 'all'.
        """
        await interaction.response.defer(ephemeral=False)
        
        logging.info(f"User {interaction.user} from {interaction.guild if interaction.guild else 'DM'} executed '/onion' with query '{query}' and time frame '{time_frame}'.")
        
        try:
            links = await get_hidden_services(query, 10, time_frame)  # Fetch top 10 links
            logging.info(f"Found {len(links)} links for query '{query}'.")

            await interaction.followup.send(f"Finished searching the dark web for **{query}** during the selected time frame. Found {len(links)} results and will now provide links and take screenshots for you.\nThis may take some time.")
            
            sent_count = 0
            for link in links:
                try:
                    screenshot = await async_get_screenshot_of_onion_site(client, link)
                    logging.info(f"Sending screenshot for link: {link}")
                    
                    # Create an embed with the onion link as the title and URL
                    embed = discord.Embed(title=link, url=f"http://{link}", color=discord.Color.blue())
                    file = discord.File(screenshot, filename="screenshot.png")
                    embed.set_image(url="attachment://screenshot.png")
                    
                    await interaction.followup.send(embed=embed, file=file)
                    os.remove(screenshot)
                    
                    sent_count += 1
                    if sent_count >= 10:  # Stop after sending 10 results
                        break
                except Exception as e:
                    logging.error(f"Error processing link {link}: {e}")
                    # Continue with the next link in case of error

        except Exception as e:
            logging.error(f"Exception in onion_search: {traceback.format_exc()}")
            await handle_errors(interaction, str(e))

    client.run(token)

if __name__ == "__main__":
    config = load_config()
    run_discord_bot(config.get("discord_bot_token"))
