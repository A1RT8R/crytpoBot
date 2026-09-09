from __future__ import annotations
import asyncio, signal
from app.config import settings
from app.db import init_db
from app.telegram import tg
from app.state_store import state_store
from app.market.core import market
from app.asset_registry import registry
from app.alerts import alert_loop
from app.bot import bot_app
from app.webhook import start_webhook_server

async def warm_market_loop():
    filters={
        "min_spread":settings.default_min_spread,
        "max_spread":settings.default_max_spread,
        "min_volume":settings.default_min_volume,
        "max_slippage":settings.default_max_slippage,
        "min_profit":settings.default_min_net_profit,
    }
    while True:
        try:
            # Shared hot cache: refresh promising books independently from user clicks.
            await market.calculate(settings.default_amount,list(settings.enabled_exchanges),filters,top=20,force_books=False,candidate_limit=settings.warm_candidate_limit)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print("Market warm loop error:",e)
        await asyncio.sleep(settings.opportunity_refresh_seconds)

async def main():
    if not settings.bot_token or settings.bot_token == "PASTE_NEW_TELEGRAM_BOT_TOKEN_HERE":
        raise SystemExit("Set a NEW BOT_TOKEN in .env")
    await init_db()
    await state_store.start()
    await tg.start()
    await registry.start()
    await market.start()
    runner=await start_webhook_server()
    tasks=[
        asyncio.create_task(warm_market_loop(),name="market-warmer"),
        asyncio.create_task(alert_loop(),name="alerts"),
        asyncio.create_task(bot_app.start(),name="telegram-polling"),
    ]
    stop=asyncio.Event()
    loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM):
        try: loop.add_signal_handler(sig,stop.set)
        except NotImplementedError: pass
    await stop.wait()
    for t in tasks: t.cancel()
    await asyncio.gather(*tasks,return_exceptions=True)
    if runner: await runner.cleanup()
    await market.close(); await registry.close(); await tg.close()

if __name__=="__main__":
    asyncio.run(main())
