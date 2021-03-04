from data import Website
from network_util import UrlDownloader
import asyncio
import concurrent.futures
import traceback

websites = [
    Website(name="Amazon", home_url="https://www.amazon.com", search_query_url="https://www.amazon.com/s",
            search_query_param="k", products=[]),
    Website(name="Tesco", home_url="https://www.tesco.com", search_query_url="https://www.tesco.com/groceries/search",
            search_query_param="query", products=[]),
    Website(name="Aldi-UK", home_url="https://www.aldi.co.uk", search_query_url="https://www.aldi.co.uk/search",
            search_query_param="q", products=[])
]
product_names = [
    "Whole Chicken", "Diced Beef", "Lamb Liver", "Oranges", "Greek Salad"
]
urlDownloader = UrlDownloader()


async def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(websites)) as executor:
        future_list = []
        for temp_website in websites:
            temp_future = executor.submit(urlDownloader.scrap_items, temp_website, product_names)
            future_list.append(temp_future)

        for temp_future in concurrent.futures.as_completed(future_list):
            try:
                temp_website = temp_future.result()
                website: Website = temp_website
                for product in website.products:
                    print(product)
                print(f'\nWebsite --> {website.name} is done for scrapping\n\n')

            except Exception as exp:
                traceback.print_exc()
                print(exp)


loop = asyncio.get_event_loop()
future = asyncio.ensure_future(main())
loop.run_until_complete(future)
