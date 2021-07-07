import pyppeteer
import asyncio
import uuid
from logzero import logger
import json
import socket

FLAG = open('flag.txt').read()
try:
    HOSTNAME = socket.getaddrinfo('screenshotter',0)[0][4][0]
except socket.gaierror:
    HOSTNAME = '127.0.0.1'
HOSTNAME += ":1024"
FLAGGER_PW = uuid.uuid4().hex

CHROME_ARGS = ["--no-sandbox", "--disable-gpu",
    "--use-mock-keychain",
    "--password-store=basic",
    "--disable-dev-shm-usage",
    "--test-type=webdriver",
    "--enable-automation",
    "--disable-hang-monitor",
    "--window-size=1280,650",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-sync",
    "--disable-web-resources",
    "--disable-notifications",
    "--disable-translate",
    "--hide-scrollbars",
    "--metrics-recording-only",
    "--mute-audio",
    "--no-first-run",
    "--safebrowsing-disable-auto-update",
    "--user-data-dir=/home/chrome"
] 

async def simulate_user(context):
    page = await context.newPage()
    await asyncio.wait([
            page.goto(f'http://{HOSTNAME}'),
            page.waitForNavigation(),
        ])
    
    await asyncio.sleep(2)
    await page.type('#username', 'flagger')
    await page.type('#password', FLAGGER_PW)
    await asyncio.wait([
        page.click('#login'),
        page.waitForNavigation(),
    ])

    await asyncio.sleep(2)
    if FLAG not in await page.content():
        logger.info(f'adding flag note')
        await page.type('#title', 'flag')
        await page.type('#body', FLAG)
        await asyncio.wait([
            page.click('#submit'),
            page.waitForNavigation(),
        ])
    
    await asyncio.sleep(2)
    logger.info(f'requesting screenshot')
    await page.type('#body', 'http://cscg.de')
    await asyncio.wait([
        page.click('#submit'),
        page.waitForNavigation(),
    ])

    
    # wait for 2 minutes
    for _ in range(0, 4):
        await asyncio.sleep(10)
        await asyncio.wait([
            page.reload(),
            page.waitForNavigation(),
        ])

    await asyncio.sleep(2)
    resp = await page.goto(f'http://{HOSTNAME}/notes.json', {'waitUntil': 'networkidle0'})
    notes = await resp.json()

    await asyncio.sleep(2)
    await asyncio.wait([
        page.goto(f'http://{HOSTNAME}/notes'),
        page.waitForNavigation(),
    ])

    logger.info(f'cleanup notes')
    for note in notes:
        if note['title'] != 'flag':

            await asyncio.sleep(2)
            await asyncio.wait([
                page.click(f"#delete_{note['uuid']}"),
                page.waitForNavigation(),
            ])
    await page.close()

async def main():
    await asyncio.sleep(30)
    while True:
        try:
            logger.info(f'credentials flager:{FLAGGER_PW}')
            browser = await pyppeteer.launch({
                    #'executablePath': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                    'executablePath': '/usr/bin/google-chrome',
                    'headless': True, 'args': CHROME_ARGS})
            context = await browser.createIncognitoBrowserContext()
            while True:
                try:
                    await simulate_user(context)
                except pyppeteer.errors.PageError:
                    logger.warning('pyppeteer.errors.PageError')
                await asyncio.sleep(30)

        except pyppeteer.errors.BrowserError:
            logger.warning('pyppeteer.errors.BrowserError')
            await asyncio.sleep(60)

asyncio.get_event_loop().run_until_complete(main())