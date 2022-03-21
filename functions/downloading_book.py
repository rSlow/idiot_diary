import os

import aiohttp
import asyncio
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import img2pdf
import glob
import shutil
from aiogram import types


async def download_book(msg: types.Message, link:str):
    login = "79146996046"
    password = "rS1owmax"

    temp = f"data\\temp\\{msg.from_user.id}"
    domain = "http://elib.igps.ru/"
    archive_server = domain + "ArchiveServer"
    headers = {"User-Agent": UserAgent().random,
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
               "DNT": "1",
               "Upgrade-Insecure-Requests": "1",
               "Connection": "keep-alive",
               "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
               "X-Requested-With": "XMLHttpRequest",
               }

    post_url = "http://elib.igps.ru/?0-1.IBehaviorListener.0-body-widget-northWidgets-widget-1-widgets-widget-1" \
               "-widgets-widget-2-widgets-widget-1-widgets-widget-2-dialog-content-widget-1-tabs-panel-widgets-widget" \
               "-1-form-widgets-widget-5-widgets-widget-2-submit~button= "

    data = {
        "idb_hf_0": "",
        "widgets:widget:1:input-field": login,
        "widgets:widget:2:input-field": password,
        "widgets:widget:5:widgets:widget:2:submit-button": "1"
    }

    def get_params(full_url: str):
        params = dict()
        url, params_full_str = full_url.split("?", maxsplit=1)
        params_str_list = params_full_str.split("&")
        for param in params_str_list:
            key, value = param.split("=")
            params[key] = value
        return params

    async def authorize(session):
        await session.get(url=domain)
        await session.post(url=post_url, data=data, headers=headers)
        await msg.edit_text(text="Авторизация пройдена.")

    async def get_full_url_and_filename(session):
        async with session.get(url=link, headers=headers) as response:
            page_data = await response.read()
            page_soup = BeautifulSoup(page_data, "lxml")
            url: str = page_soup.find("div", {"class": "card-view-cover-link"}).find("a").get("href")
            filename: str = page_soup.find("div", {"class": "card-view-title"}).text.strip()
            full_url = domain + "?" + url.split("?", maxsplit=1)[1]
            return full_url, filename

    async def get_url_to_app_block(session, full_url):
        async with session.get(url=full_url, headers=headers) as response:
            book_app_src = await response.read()
            book_soup = BeautifulSoup(book_app_src, "lxml")
            book_app_url: str = book_soup.find("iframe").get("src")
            book_app_full_url = domain + "?" + book_app_url.split("?", maxsplit=1)[1]
            return book_app_full_url

    async def get_params_from_app_url(session, app_block_url):
        async with session.get(url=app_block_url, headers=headers) as response:
            app_src = await response.read()
            soup = BeautifulSoup(app_src, "lxml")
            redirect_url = soup.find("meta").get("content").split("=", 1)[1]
            params_page = get_params(redirect_url)
            return params_page

    async def get_pages(session, params_page):
        archive_server_url = archive_server + "/vwr/page"

        async with session.get(url=archive_server_url, headers=headers, params=params_page) as response:
            page_data = await response.read()
            page_soup = BeautifulSoup(page_data, "lxml")
            pages = page_soup.find("div", {"class": "last-page-number-textfield"}).text
            await msg.edit_text(text=f"Началась загрузка. Всего {pages} страниц")
            return pages

    async def download_page(session, page, params_img):
        image_url = archive_server + "/vwr/imgres"
        async with session.get(url=image_url, headers=headers, params=params_img) as response:
            image_data = await response.read()
            with open(f"{temp}\\{page}.png", "wb") as img_file:
                img_file.write(image_data)

    async def main():
        async with aiohttp.ClientSession() as session:
            await authorize(session)
            full_url, filename = await get_full_url_and_filename(session)
            app_block_url = await get_url_to_app_block(session, full_url)
            params_page = await get_params_from_app_url(session, app_block_url)
            pages = await get_pages(session, params_page)

            tasks = list()
            for page in range(1, int(pages) + 1):
                params_img = {
                    "page": f"{page}",
                    "docPath": params_page["docPath"],
                    "cachePath": params_page["cacheFolder"],
                    "password": "undefined",
                    "separator": ":"
                }
                tasks.append(asyncio.create_task(download_page(session, page, params_img)))
            await asyncio.gather(*tasks)

            way = os.path.join(temp, "*.png")
            print(way)
            print(glob.glob(way))
            temp_filename = f"data\\temp\\{msg.from_user.id}\\book.pdf"
            with open(temp_filename, "wb") as file:
                file.write(img2pdf.convert(glob.glob(way)))

            doc = types.InputFile(path_or_bytesio=temp_filename,
                                  filename=f"{filename}.pdf")
            await msg.answer_document(doc)

    try:
        if not os.path.exists(temp):
            os.mkdir(temp)
        await main()
    except Exception as ex:
        print(ex)
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    await msg.delete()