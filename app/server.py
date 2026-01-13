import os
import logging
from aiohttp import web


async def ping(req):
    return web.Response(text="here")


async def rs():
    app = web.Application()

    app.add_routes([web.get('/', ping)])
    run = web.AppRunner(app)
    await run.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(run, '0.0.0.0', port)

    await site.start()
    logging.info(port)
