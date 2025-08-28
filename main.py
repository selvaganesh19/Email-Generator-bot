import asyncio
import uvicorn

async def run_api():
    config = uvicorn.Config("api.app:app", host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

async def run_bot():
    from telegram_bot.bot import main as bot_main
    await bot_main()  # Make sure your bot.main() is async

async def main():
    await asyncio.gather(
        run_api(),
        run_bot()
    )

if __name__ == "__main__":
    asyncio.run(main())