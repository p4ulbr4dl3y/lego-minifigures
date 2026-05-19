import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def human_delay(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def main():
    async with async_playwright() as p:
        # Попытка использовать установленный Chrome - он вызывает меньше подозрений.
        # Если Chrome не установлен, Playwright использует встроенный Chromium
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080",
        ]
        
        # Временная папка для профиля с сохранением cookie
        user_data_dir = "./avito_user_data"
        
        print("Запуск браузера с имитацией реального профиля...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,  # При неудаче - переключить на False для ручного прохождения проверок
            args=browser_args,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )
        
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        # Предварительный переход на Google для формирования реферера
        print("Переход на Google для формирования реферера...")
        await page.goto("https://www.google.com")
        await human_delay(1, 2)
        
        print("Переход на Avito...")
        # Переход на главную страницу вместо прямого перехода к поиску
        await page.goto("https://www.avito.ru", wait_until="domcontentloaded")
        
        # Имитация пользовательского ожидания
        await human_delay(3, 6)
        
        title = await page.title()
        print(f"Заголовок страницы: {title}")
        
        # Скриншот для проверки состояния страницы
        await page.screenshot(path="avito_retry_screenshot.png")
        
        if "Доступ ограничен" in title:
            print("Сохраняется блокировка по IP. Попытка прямого перехода на страницу товара через 5 секунд...")
            await human_delay(5, 7)
            await page.goto("https://www.avito.ru/moskva/avtomobili", wait_until="domcontentloaded")
            await page.screenshot(path="avito_cars_screenshot.png")
            print(f"Новый заголовок: {await page.title()}")

        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
