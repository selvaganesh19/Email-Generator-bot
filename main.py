# main.py (create this in your project root)
import threading
import uvicorn

def run_api():
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000)

def run_bot():
    import telegram_bot.bot
    telegram_bot.bot.main()

if __name__ == "__main__":
    t1 = threading.Thread(target=run_api)
    t2 = threading.Thread(target=run_bot)
    t1.start()
    t2.start()
    t1.join()
    t2.join()