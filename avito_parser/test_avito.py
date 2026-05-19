import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    async with async_playwright() as p:
        iphone_13 = p.devices['iPhone 13']
        browser = await p.webkit.launch(headless=True)
        context = await browser.new_context(
            **iphone_13,
            locale="ru-RU",
            timezone_id="Europe/Moscow"
        )
        page = await context.new_page()
        
        # Stealth for webkit might not be supported well by playwright-stealth
        # but let's see if the device emulation is enough
        
        print("Перехожу на m.avito.ru...")
        await page.goto("https://m.avito.ru/moskva/avtomobili", wait_until="networkidle")
        
        title = await page.title()
        print(f"Заголовок страницы: {title}")
        
        # Делаем скриншот для проверки
        await page.screenshot(path="avito_mobile_screenshot.png")
        print("Скриншот сохранен в avito_mobile_screenshot.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
