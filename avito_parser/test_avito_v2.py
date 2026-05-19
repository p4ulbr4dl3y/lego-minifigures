import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def human_delay(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def main():
    async with async_playwright() as p:
        # Пытаемся найти установленный Chrome, он вызывает меньше подозрений
        # Если Chrome не установлен, playwright будет использовать свой chromium
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080",
        ]
        
        # Используем временную папку для профиля, чтобы сохранять куки
        user_data_dir = "./avito_user_data"
        
        print("Запуск браузера с имитацией реального профиля...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True, # Поставим True для начала, но если не выйдет - попросим пользователя запустить с False
            args=browser_args,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )
        
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        # Сначала зайдем на google, чтобы был "реферер"
        print("Заходим на Google для прогрева...")
        await page.goto("https://www.google.com")
        await human_delay(1, 2)
        
        print("Переходим на Avito...")
        # Переходим не сразу на поиск, а на главную
        await page.goto("https://www.avito.ru", wait_until="domcontentloaded")
        
        # Имитируем небольшое ожидание и скролл
        await human_delay(3, 6)
        
        title = await page.title()
        print(f"Заголовок страницы: {title}")
        
        # Если заголовок все еще плохой, попробуем сделать скриншот
        await page.screenshot(path="avito_retry_screenshot.png")
        
        if "Доступ ограничен" in title:
            print("!!! Все еще блокировка по IP. Пробуем зайти на страницу товара напрямую через 5 секунд...")
            await human_delay(5, 7)
            await page.goto("https://www.avito.ru/moskva/avtomobili", wait_until="domcontentloaded")
            await page.screenshot(path="avito_cars_screenshot.png")
            print(f"Новый заголовок: {await page.title()}")

        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
