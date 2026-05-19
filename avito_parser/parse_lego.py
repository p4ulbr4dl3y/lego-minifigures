import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def human_delay(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def main():
    async with async_playwright() as p:
        user_data_dir = "./avito_user_data"
        
        print("Запуск браузера в видимом режиме...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,  # Браузер откроется в видимом режиме
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )
        
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        url = "https://www.avito.ru/moskva/kollektsionirovanie?cd=1&q=lego+%D0%BC%D0%B8%D0%BD%D0%B8%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%BA%D0%B8"
        
        print("Переход на страницу поиска LEGO...")
        await page.goto(url, wait_until="domcontentloaded")
        
        print("\nВНИМАНИЕ: при наличии капчи или блокировки - пройдите проверку в открывшемся окне браузера.")
        print("Ожидание появления объявлений (до 2 минут)...")
        
        try:
            # Ожидание появления элементов до 2 минут для прохождения капчи
            await page.wait_for_selector('[data-marker="item"]', timeout=120000)
            
            print("\nОбъявления найдены. Сбор данных...")
            
            # Пауза после появления элементов для полной загрузки
            await human_delay(2, 4)
            
            items = await page.query_selector_all('[data-marker="item"]')
            print(f"Найдено объявлений: {len(items)}\n")
            
            for i, item in enumerate(items[:15]):
                title_elem = await item.query_selector('[data-marker="item-title"]')
                price_elem = await item.query_selector('[data-marker="item-price"]')
                
                name = await title_elem.inner_text() if title_elem else "N/A"
                price = await price_elem.inner_text() if price_elem else "N/A"
                print(f"{i+1}. {name} | {price}")
                
            # Сохранение скриншота успешного результата
            await page.screenshot(path="avito_success.png")
            print("\nСкриншот успеха сохранен в avito_success.png")
            
        except Exception as e:
            print(f"\nНе удалось дождаться появления объявлений. Ошибка: {e}")
            await page.screenshot(path="avito_fail.png")

        print("\nБраузер закроется через 15 секунд.")
        await asyncio.sleep(15)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
