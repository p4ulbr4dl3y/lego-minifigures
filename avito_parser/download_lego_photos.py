import asyncio
import random
import os
import aiohttp
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def download_image(url, folder, filename):
    if not url: return
    try:
        # Удаление запрещенных символов из имени файла
        clean_filename = "".join([c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
        clean_filename = f"{clean_filename[:100]}.jpg"
        filepath = os.path.join(folder, clean_filename)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(filepath, 'wb') as f:
                        f.write(await response.read())
                    return filepath
    except Exception as e:
        print(f"Не удалось скачать {filename}: {e}")
    return None

async def main():
    img_folder = "lego_images"
    os.makedirs(img_folder, exist_ok=True)

    async with async_playwright() as p:
        user_data_dir = "./avito_user_data"
        
        print("Запуск браузера в ВИДИМОМ режиме...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, 
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 900}
        )
        
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        url = "https://www.avito.ru/moskva/kollektsionirovanie?cd=1&q=lego+%D0%BC%D0%B8%D0%BD%D0%B8%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%BA%D0%B8"
        
        print("Переход на Avito...")
        await page.goto(url, wait_until="domcontentloaded")
        
        try:
            print("Ожидание появления объявлений. При наличии капчи - пройдите её вручную.")
            await page.wait_for_selector('[data-marker="item"]', timeout=60000)
            
            # Прокрутка вниз для подгрузки всех фотографий
            print("Прокрутка страницы для загрузки изображений...")
            for i in range(10):
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(0.5)
            
            # Возврат в начало страницы для проверки наличия всех DOM-элементов
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)

            items = await page.query_selector_all('[data-marker="item"]')
            print(f"Найдено объявлений: {len(items)}. Скачивание...")
            
            downloaded = 0
            for i, item in enumerate(items):
                try:
                    title_elem = await item.query_selector('[data-marker="item-title"]')
                    # Поиск всех изображений внутри элемента и выбор первого подходящего
                    img_elems = await item.query_selector_all('img')
                    
                    if title_elem and img_elems:
                        name = await title_elem.inner_text()
                        
                        # Поиск реального URL изображения (src или data-src)
                        img_url = None
                        for img in img_elems:
                            src = await img.get_attribute("src")
                            if src and src.startswith('http') and 'static' not in src:
                                img_url = src
                                break
                        
                        if img_url:
                            # Попытка получить изображение большего размера
                            # В URL Avito обычно присутствует /640x480/ или /208x156/
                            # img_url = img_url.replace('208x156', '640x480') 
                            
                            res = await download_image(img_url, img_folder, f"{i+1}_{name}")
                            if res:
                                downloaded += 1
                                if downloaded % 5 == 0:
                                    print(f"Скачано {downloaded} изображений...")
                except:
                    continue
            
            print(f"\nСкачивание завершено. Всего загружено: {downloaded} фотографий.")
            print(f"Путь к папке: {os.path.abspath(img_folder)}")
            
        except Exception as e:
            print(f"Ошибка в процессе: {e}")

        print("\nЗавершение. Браузер закроется через 10 секунд.")
        await asyncio.sleep(10)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
