import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    async with async_playwright() as p:
        user_data_dir = "./avito_user_data"
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        url = "https://www.avito.ru/ekaterinburg/kollektsionirovanie/lego_minifigurki_24_seriya_8159009639"
        print(f"Переход на тестовое объявление: {url}")
        
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(5)  # Ожидание полной загрузки
        
        # Сохранение HTML для анализа
        content = await page.content()
        with open("ad_structure.html", "w", encoding="utf-8") as f:
            f.write(content)
        
        await page.screenshot(path="ad_debug.png")
        print("HTML сохранен в ad_structure.html, скриншот в ad_debug.png")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
