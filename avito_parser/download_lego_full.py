import asyncio
import random
import os
import aiohttp
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def human_delay(min_sec=1, max_sec=3):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def download_image(url, folder, filename):
    if not url: return
    try:
        clean_filename = "".join([c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
        clean_filename = f"{clean_filename[:100]}.jpg"
        filepath = os.path.join(folder, clean_filename)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    with open(filepath, 'wb') as f:
                        f.write(await response.read())
                    return filepath
    except Exception as e:
        print(f"      Ошибка скачивания {filename}: {e}")
    return None

async def process_ad(page, ad_url, ad_title, base_folder, ad_index):
    print(f"   Переход в объявление: {ad_title}")
    
    # Создание папки для объявления
    folder_name = "".join([c for c in ad_title if c.isalnum() or c == ' ']).strip()[:40]
    ad_folder = os.path.join(base_folder, f"ad_{ad_index}_{folder_name}")
    os.makedirs(ad_folder, exist_ok=True)
    
    try:
        await page.goto(ad_url, wait_until="domcontentloaded", timeout=60000)
        await human_delay(2, 4)
        
        # Проверка на блокировку внутри объявления
        if "Доступ ограничен" in await page.title():
            print("      Блокировка внутри объявления. Ожидание...")
            await asyncio.sleep(10)
            await page.reload(wait_until="domcontentloaded")

        # Поиск миниатюр
        thumbnails = await page.query_selector_all('[data-marker="image-preview/item"]')
        img_urls = set()

        if not thumbnails:
            # Одиночная фотография
            main_img = await page.query_selector('[data-marker="image-frame/image-wrapper"] img')
            if main_img:
                src = await main_img.get_attribute("src")
                if src: img_urls.add(src)
        else:
            # Обработка первых 5-7 фотографий (ограничение для ускорения)
            for idx, thumb in enumerate(thumbnails[:8]):
                try:
                    await thumb.click()
                    await asyncio.sleep(0.8)
                    main_img = await page.query_selector('[data-marker="image-frame/image-wrapper"] img')
                    if main_img:
                        srcset = await main_img.get_attribute("srcset")
                        if srcset:
                            img_urls.add(srcset.split(',')[-1].strip().split(' ')[0])
                        else:
                            src = await main_img.get_attribute("src")
                            if src: img_urls.add(src)
                except:
                    continue

        print(f"      Найдено фотографий: {len(img_urls)}. Скачивание...")
        for j, img_url in enumerate(img_urls):
            await download_image(img_url, ad_folder, f"photo_{j+1}")
            
    except Exception as e:
        print(f"      Ошибка при обработке объявления: {e}")

async def main():
    base_folder = "lego_full_images"
    os.makedirs(base_folder, exist_ok=True)
    
    search_base_url = "https://www.avito.ru/moskva/kollektsionirovanie?q=lego+%D0%BC%D0%B8%D0%BD%D0%B8%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%BA%D0%B8"
    
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
        
        global_ad_counter = 1
        
        for p_num in [1, 2]:
            print(f"\n=== ОБРАБОТКА СТРАНИЦЫ {p_num} ===")
            page_url = f"{search_base_url}&p={p_num}"
            
            await page.goto(page_url, wait_until="domcontentloaded")
            await human_delay(3, 5)
            
            # Ожидание загрузки объявлений
            try:
                await page.wait_for_selector('[data-marker="item"]', timeout=30000)
                items = await page.query_selector_all('[data-marker="item"]')
                
                ads_on_page = []
                for item in items:
                    link_elem = await item.query_selector('[data-marker="item-title"]')
                    if link_elem:
                        href = await link_elem.get_attribute("href")
                        title = await link_elem.inner_text()
                        ads_on_page.append({"url": f"https://www.avito.ru{href}", "title": title})
                
                print(f"Найдено {len(ads_on_page)} объявлений на странице {p_num}.")
                
                # Обработка каждого объявления
                for ad in ads_on_page:
                    await process_ad(page, ad['url'], ad['title'], base_folder, global_ad_counter)
                    global_ad_counter += 1
                    # Задержка между объявлениями
                    await human_delay(2, 5)
                    
            except Exception as e:
                print(f"Ошибка на странице поиска {p_num}: {e}")
                await page.screenshot(path=f"error_p{p_num}.png")

        print(f"\nПарсинг завершен. Всего обработано объявлений: {global_ad_counter-1}")
        await asyncio.sleep(5)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
