import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Dauko bayanan sirri daga .env file
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Ma'ajin wucin gadi na Trades
active_trades = {}

async def get_token_price(token_mint: str):
    """Nemo farashin token ta hanyar Jupiter API"""
    url = f"https://api.jup.ag/price/v2?ids={token_mint}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                data = await response.json()
                return float(data["data"][token_mint]["price"])
        except Exception as e:
            print(f"Kuskure wajen nemo farashi: {e}")
            return None

async def execute_jupiter_swap(chat_id, token_mint, amount):
    """Wurin da zaka rubuta code din siyarwa a Solana Blockchain"""
    print(f"Ana kokarin siyar da {amount} na Token {token_mint} domin kariya...")
    # Anan ake amfani da solana-py da solders wajen sa hannu (sign) da tura transaction
    return True # Mun nuna cewa siyarwar tayi nasara a matsayin misali

async def monitor_prices(app):
    """Tsarin da ke duba farashi a bayan fage kowane sakan 5"""
    while True:
        # Zamu duba duk wani mutum da ya kunna TSL a bot din
        for chat_id, trade in list(active_trades.items()):
            if not trade["is_active"]:
                continue

            current_price = await get_token_price(trade["token_mint"])
            if not current_price:
                continue

            # Idan farashi ya tashi, zamu daga Stop Price dinsa sama!
            if current_price > trade["highest_price"]:
                trade["highest_price"] = current_price
                trade["stop_price"] = current_price * (1 - trade["trail_percentage"] / 100)
                
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=f"📈 Farashi ya tashi! Sabon matakin TSL ya koma: ${trade['stop_price']:.4f}"
                )

            # Idan farashi ya fado ya taba TSL ko yayi kasa da shi
            if current_price <= trade["stop_price"]:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚨 Gargaɗi: Farashi ya fado zuwa TSL (${trade['stop_price']:.4f}). Ana siyarwa yanzu..."
                )
                
                trade["is_active"] = False # Dakatar da tsarin don kar ya maimaita

                success = await execute_jupiter_swap(chat_id, trade["token_mint"], trade["amount"])
                
                if success:
                    await app.bot.send_message(chat_id, "✅ An yi nasarar siyar da Token dinka domin kare asara!")
                    del active_trades[chat_id]
                else:
                    await app.bot.send_message(chat_id, "❌ An samu matsala wajen siyarwa.")
                    trade["is_active"] = True

        await asyncio.sleep(5) # Jira sakan 5 kafin a sake duba farashi


# --- Commands na Telegram ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sannu! Ni ne Solana TSL Bot (na Python).\nYi amfani da /setup_tsl domin gwada ni.")

async def setup_tsl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Misali ne, a ainihin aiki zaka nemi mutum ya turo maka wadannan:
    token_mint = "EKpQGSJfezzmGa6v714131X3t4E3iXNptT5p7Tzxt193" # WIF Token
    trail_percentage = 10
    amount = 1000000 

    await update.message.reply_text("Ina nemo farashin farko daga kasuwa...")
    
    start_price = await get_token_price(token_mint)
    if not start_price:
        await update.message.reply_text("❌ Ba a sami farashin ba. Tabbatar da Mint Address din.")
        return

    initial_stop_price = start_price * (1 - trail_percentage / 100)

    # Ajiye bayanan user
    active_trades[chat_id] = {
        "token_mint": token_mint,
        "trail_percentage": trail_percentage,
        "amount": amount,
        "highest_price": start_price,
        "stop_price": initial_stop_price,
        "is_active": True
    }

    await update.message.reply_text(
        f"✅ An kunna Trailing Stop Loss!\n\n"
        f"Farashin Yanzu: ${start_price}\n"
        f"Stop Price na Farko: ${initial_stop_price:.4f}\n\n"
        f"Zan ci gaba da lura da shi."
    )

if __name__ == '__main__':
    # Fara bot din
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setup_tsl", setup_tsl))

    # Tada tsarin da zai duba farashi a bayan fage (Background Task)
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_prices(app))

    print("Bot din Python ya tashi tsaf!")
    app.run_polling()
