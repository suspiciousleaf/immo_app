import asyncio
from pyppeteer import launch
from pprint import pprint
import time

pages = 13
search_urls = [f"https://beauxvillages.com/fr/nos-biens_fr?option=com_iproperty&view=allproperties&id=0&layout=&autocomplete=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne%2CAude&filter_province=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne&filter_county=Aude&filter_order=p.price&filter_order_Dir=ASC&commit=&5a7fb023d0edd8037757cf17e9634828=1&Itemid=10504793&start={i*30}" for i in range(pages)]

async def scrape_page(url, browser):

    page = await browser.newPage()
    await page.goto(url)
    await page.waitForSelector('.ip-property-thumb-holder')
    elements = await page.querySelectorAll('.ip-property-thumb-holder')
    links = []
    for element in elements:
        try:
            link = await element.querySelectorEval('a', 'e => e.href')
            links.append(link)

         # If the property is "sold", the property href will not exist, but the thumbnail is still present with the class ip-property-thumb-holder. This code will allow the specific error of the missing href to pass, but will raise an exception for any other fault
        except Exception as e:
            if str(e) == 'Error: failed to find element matching selector "a"':
                pass
            else:
                raise Exception(f"Error fetching href, {e}")

    await page.close()
    return links

async def main():
    browser = await launch(headless=True)
    all_links = []
    tasks = []
    for url in search_urls:
        task = asyncio.ensure_future(scrape_page(url, browser))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    for links in results:
        all_links += links
    await browser.close()
    return all_links

def get_links():    # Takes approx 21 seconds

    t0 = time.perf_counter()
    links = asyncio.get_event_loop().run_until_complete(main())

    pprint(links)
    print(len(links))

    t1 = time.perf_counter()

    time_taken = t1 - t0

    print(f"Time taken to scrape links: {time_taken:.2f}s")



