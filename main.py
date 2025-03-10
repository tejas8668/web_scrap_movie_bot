import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the bot token and channel ID from environment variables
TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# In-memory storage for user tracking
users = set()
search_results = {}

# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    logger.info("Received /start command")
    user = update.effective_user

    # Add user to the set
    users.add(user.id)

    message = (
        f"New user started the bot:\n"
        f"Name: {user.full_name}\n"
        f"Username: @{user.username}\n"
        f"User ID: {user.id}"
    )
    await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
    await update.message.reply_photo(
        photo='https://ik.imagekit.io/dvnhxw9vq/movie_bot.png?updatedAt=1741412177209',  # Replace with your image URL
        caption=(
            "👋 **ℍ𝕖𝕝𝕝𝕠 𝔻𝕖𝕒𝕣!**\n\n"
            "I am an advanced movie search bot. Just send me any movie name and I will give you a direct download link of any movie.​\n\n"
            "**𝐈𝐦𝐩𝐨𝐫𝐭𝐚𝐧𝐭​​**\n\n"
            "Please search with the correct spelling for better results."
        ),
        parse_mode='Markdown'
    )

def redirection_domain_get(old_url):
    try:
        # Send a GET request to the old URL and allow redirects
        response = requests.get(old_url, allow_redirects=True)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Extract the final URL after redirection
            new_url = response.url
            return new_url
        else:
            return old_url
    except requests.RequestException as e:
        return old_url

async def filmyfly_movie_search(url, domain, update: Update, context: CallbackContext, searching_message_id: int):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all <a> tags with href containing '/page-download/'
        download_links = soup.find_all('a', href=lambda href: href and '/page-download/' in href)

        # Check if no download links were found
        if not download_links:
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=searching_message_id)
            await update.message.reply_text("No search results found, Please check your spelling on google.com")
            return

        # Use a set to store unique links
        unique_links = set()
        buttons = []

        # Extract and print the href attributes
        for i, link in enumerate(download_links):
            href = link.get('href')
            if href and href not in unique_links:
                unique_links.add(href)
                callback_data = f'link_{i}'
                context.user_data[callback_data] = f'{domain}{href}'
                # Extract the last part of the URL for the button title
                button_title = href.split('/')[-1]
                buttons.append([InlineKeyboardButton(button_title, callback_data=callback_data)])

        # Store the search results in the context
        context.user_data['search_results'] = buttons
        context.user_data['current_page'] = 0

        # Delete the "Searching..." message
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=searching_message_id)

        # Send the first page of results
        await send_search_results(update, context)
    except requests.RequestException as e:
        await update.message.reply_text(f"Failed to retrieve the webpage. Error: {e}")
    except Exception as e:
        await update.message.reply_text(f"An unexpected error occurred. Error: {e}")

async def send_search_results(update: Update, context: CallbackContext):
    buttons = context.user_data['search_results']
    current_page = context.user_data['current_page']
    
    # Paginate the results
    start = current_page * 8
    end = start + 8
    page_buttons = buttons[start:end]
    
    # Add a "Next" button if there are more results
    if end < len(buttons):
        page_buttons.append([InlineKeyboardButton("Next", callback_data="next_page")])
    
    reply_markup = InlineKeyboardMarkup(page_buttons)
    if update.message:
        del_msg = await update.message.reply_text("Search Results:", reply_markup=reply_markup)
    elif update.callback_query:
        del_msg = await update.callback_query.message.reply_text("Search Results:", reply_markup=reply_markup)
    
    # Schedule the deletion of the message after 120 seconds without blocking
    asyncio.create_task(delete_message_after_delay(del_msg))

async def delete_message_after_delay(message):
    await asyncio.sleep(120)
    await message.delete()

async def handle_button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == "next_page":
        context.user_data['current_page'] += 1
        await send_search_results(query, context)
    else:
        url = context.user_data.get(query.data)
        if url:
            await filmyfly_download_linkmake_view(url, update)

async def filmyfly_download_linkmake_view(url, update: Update):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all <a> tags with href containing 'https://linkmake.in/view'
        linkmake_links = soup.find_all('a', href=lambda href: href and 'https://linkmake.in/view' in href)
        
        # Check if no linkmake links were found
        if not linkmake_links:
            await update.callback_query.message.reply_text("Download Link Not Available In My Database. Please Try Another Movie.")
            return
        
        # Use a set to store unique links
        unique_links = set()
        buttons = []
        
        # Extract and print the href attributes
        for link in linkmake_links:
            href = link.get('href')
            if href and href not in unique_links:
                unique_links.add(href)
                buttons.append([InlineKeyboardButton(f'Your Download Link', url=href)])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.callback_query.message.reply_text("Download Link:", reply_markup=reply_markup)
    except requests.RequestException as e:
        await update.callback_query.message.reply_text(f"Failed to retrieve the webpage. Error: {e}")
    except Exception as e:
        await update.callback_query.message.reply_text(f"An unexpected error occurred. Error: {e}")

async def filmyfly_scraping(update: Update, context: CallbackContext):
    # Send a "Searching..." message
    searching_message = await update.message.reply_text("Searching...")
    
    # Fetch download links
    filmyflyurl = update.message.text
    if not filmyflyurl:
        await update.message.reply_text("Search Any Movie With Correct Spelling To Download")
        return

    filmyfly_domain = redirection_domain_get("https://filmyfly.esq")
    filmyfly_final = f"{filmyfly_domain}site-1.html?to-search={filmyflyurl}"
    await filmyfly_movie_search(filmyfly_final, filmyfly_domain, update, context, searching_message.message_id)

def main() -> None:
    # Get the port from the environment variable or use default
    port = int(os.environ.get('PORT', 8080))  # Default to port 8080
    webhook_url = f"https://painful-eustacia-chavan-013550df.koyeb.app/{TOKEN}"  # Replace with your server URL

    # Create the Application and pass it your bot's token
    app = ApplicationBuilder().token(TOKEN).build()

    # Register the /start command handler
    app.add_handler(CommandHandler("start", start))

    # Register the link handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filmyfly_scraping))

    # Register the button click handler
    app.add_handler(CallbackQueryHandler(handle_button_click))

    # Run the bot using a webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_url
    )

if __name__ == '__main__':
    main()
