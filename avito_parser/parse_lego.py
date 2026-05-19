import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def human_delay(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def main():
    async with async_playwright() as p:
        user_data_dir = "./avito_user_data"
        
        print("Запуск браузера в ВИДИМОМ режиме (headless=False)...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # Теперь браузер откроется на экране
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )
        
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        url = "https://www.avito.ru/moskva/kollektsionirovanie?cd=1&q=lego+%D0%BC%D0%B8%D0%BD%D0%B8%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%BA%D0%B8"
        
        print(f"Переходим на страницу поиска LEGO...")
        await page.goto(url, wait_until="domcontentloaded")
        
        print("\n!!! ВНИМАНИЕ: Если вы видите капчу или блокировку, пройдите её в открывшемся окне браузера !!!")
        print("Ожидаю появления объявлений (таймаут 2 минуты)...")
        
        try:
            # Ждем появления элементов до 2 минут, чтобы пользователь успел пройти капчу
            await page.wait_for_selector('[data-marker="item"]', timeout=120000)
            
            print("\nУра! Объявления найдены. Начинаю сбор данных...")
            
            # Небольшая пауза после появления, чтобы все прогрузилось
            await human_delay(2, 4)
            
            items = await page.query_selector_all('[data-marker="item"]')
            print(f"Найдено объявлений: {len(items)}\n")
            
            for i, item in enumerate(items[:15]):
                title_elem = await item.query_selector('[data-marker="item-title"]')
                price_elem = await item.query_selector('[data-marker="item-price"]')
                
                name = await title_elem.inner_text() if title_elem else "N/A"
                price = await price_elem.inner_text() if price_elem else "N/A"
                print(f"{i+1}. {name} | {price}")
                
            # Сохраним скриншот успеха
            await page.screenshot(path="avito_success.png")
            print("\nСкриншот успеха сохранен в avito_success.png")
            
        except Exception as e:
            print(f"\nНе удалось дождаться появления объявлений. Ошибка: {e}")
            await page.screenshot(path="avito_fail.png")

        print("\nБраузер закроется через 15 секунд. Вы можете успеть посмотреть на результат в окне.")
        await asyncio.sleep(15)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
