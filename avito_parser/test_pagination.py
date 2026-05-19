import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def human_delay(min_sec=3, max_sec=6):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def test_pagination():
    async with async_playwright() as p:
        user_data_dir = "./avito_user_data"
        
        print("Запуск браузера для теста пагинации...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        # Базовый URL (без номера страницы)
        base_url = "https://www.avito.ru/moskva/kollektsionirovanie?q=lego+%D0%BC%D0%B8%D0%BD%D0%B8%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%BA%D0%B8"
        
        for p_num in [1, 2]: # Проверим 1-ю и 2-ю страницы
            target_url = f"{base_url}&p={p_num}"
            print(f"\n--- Переход на страницу {p_num} ---")
            print(f"URL: {target_url}")
            
            await page.goto(target_url, wait_until="domcontentloaded")
            await human_delay()
            
            title = await page.title()
            print(f"Заголовок: {title}")
            
            if "Доступ ограничен" in title:
                print("!!! Блокировка на странице", p_num)
                await page.screenshot(path=f"block_p{p_num}.png")
                continue
            
            items = await page.query_selector_all('[data-marker="item"]')
            print(f"Найдено объявлений на странице: {len(items)}")
            
            await page.screenshot(path=f"pagination_p{p_num}.png")
            
        print("\nТест завершен. Закрываю браузер через 5 секунд...")
        await asyncio.sleep(5)
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_pagination())
