# This scraper can sometimes raise a Network Error for some listings, it happens intermittently and is due to a bug in Pyppeteer. No known fixes exist, there is a bounty for the bug, suffice to say I have not claimed that bounty. The listing still scrapes successfully when the exception is raised.

import time
import math
import json
import asyncio

# This must be imported as it is imported with get_gps, and if requests is imported before grequests it will cause recursion error
import grequests
from pyppeteer import launch
from pprint import pprint
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode

from models import Listing
from utilities.utilities import get_gps

try:
    try:
        with open("listings.json", "r", encoding="utf8") as infile:
            listings_json = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/listings.json", "r", encoding="utf8"
        ) as infile:
            listings_json = json.load(infile)
except:
    listings_json = []

try:
    with open("postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/postcodes_dict.json", "r", encoding="utf8"
    ) as infile:
        postcodes_dict = json.load(infile)

try:
    try:
        with open("postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/postcodes_gps_dict.json",
            "r",
            encoding="utf8",
        ) as infile:
            gps_dict = json.load(infile)
except:
    print("gps_dict not found")
    gps_dict = []


def beaux_get_listings():
    t0 = time.perf_counter()

    URL = "https://beauxvillages.com/fr/nos-biens_fr?option=com_iproperty&view=allproperties&id=0&layout=&autocomplete=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne%2CAude&filter_province=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne&filter_county=Aude&filter_order=p.price&filter_order_Dir=ASC&commit=&5a7fb023d0edd8037757cf17e9634828=1&Itemid=10504793"

    page = requests.get(URL)

    beaux_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = beaux_soup.find("span", class_="ip-pagination-results").get_text()
    num_props_div = [int(num) for num in num_props_div.split() if num.isnumeric()]
    num_props = num_props_div[2]
    per_page = num_props_div[1]
    print(f"\nBeaux Villages number of listings: {num_props}")
    pages = math.ceil(num_props / per_page)
    # This retrieves the total number of listings, and the number of search page results
    print(f"Pages: {pages} \nFinding urls now, this will take approx 15 seconds.")

    search_urls = list(
        set(
            [
                f"https://beauxvillages.com/fr/nos-biens_fr?option=com_iproperty&view=allproperties&id=0&layout=&autocomplete=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne%2CAude&filter_province=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne&filter_county=Aude&filter_order=p.price&filter_order_Dir=ASC&commit=&5a7fb023d0edd8037757cf17e9634828=1&Itemid=10504793&start={i*per_page}"
                for i in range(pages)
            ]
        )
    )

    # This will return the url of all available listings
    links = asyncio.get_event_loop().run_until_complete(
        scrape_all_search_pages(search_urls)
    )

    listings = [
        listing for listing in listings_json if listing["agent"] == "Beaux Villages"
    ]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Beaux Villages":
            links_old.append(listing["link_url"])

    links_to_scrape = [link for link in links if link not in links_old]
    print("New listings to add:", len(links_to_scrape))

    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    results = []
    if links_to_scrape:
        print(
            f"Scraping {len(links_to_scrape)} links, this will take approx {len(links_to_scrape)/2} seconds"
        )
        results = asyncio.get_event_loop().run_until_complete(
            run_scrape(links_to_scrape)
        )

    for result in results:
        if isinstance(result, str):
            failed_scrape_links.append(result)
            counter_fail += 1
        else:
            listings.append(result)
            counter_success += 1

    if links_to_scrape:
        print(f"Successfully scraped: {counter_success}/{len(links_to_scrape)}")

    if failed_scrape_links:
        print(f"Failed to scrape: {counter_fail}/{len(links_to_scrape)} \nFailed URLs:")
        pprint(failed_scrape_links)

    listings.sort(key=lambda x: x["price"])

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Time elapsed for Beaux Villages: {time_taken:.2f}s")

    return listings


async def scrape_page_links(url, browser):
    page = await browser.newPage()
    await page.goto(url)
    await page.waitForSelector(".ip-property-thumb-holder")
    elements = await page.querySelectorAll(".ip-property-thumb-holder")
    links = []
    for element in elements:
        try:
            link = await element.querySelectorEval("a", "e => e.href")
            links.append(link)

        # If the property is "sold", the property href will not exist, but the thumbnail is still present with the class ip-property-thumb-holder. This code will allow the specific error of the missing href to pass, but will raise an exception for any other fault
        except Exception as e:
            if str(e) == 'Error: failed to find element matching selector "a"':
                pass
            else:
                raise Exception(f"Error fetching href, {e}")

    await page.close()
    return links


async def scrape_all_search_pages(search_urls):
    browser = await launch(headless=True)
    all_links = []
    tasks = []
    for url in search_urls:
        task = asyncio.ensure_future(scrape_page_links(url, browser))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    for links in results:
        all_links += links
    await browser.close()
    return all_links


async def get_listing_details(url, semaphore, browser):
    async with semaphore:
        try:
            page = await browser.newPage()

            # Enable request interception, this is used to block images and CSS files form downloading to speed up the process
            await page.setRequestInterception(True)

            # Set up the request interception handler
            # try:
            page.on(
                "request", lambda request: asyncio.ensure_future(block_images(request))
            )
            # except NetworkError as e:
            #     print(f"AAAAA Error occurred: {e}")

            # This increases the timeout as it is sometimes triggered at the default of 30s
            page.setDefaultNavigationTimeout(60000)

            await page.goto(url)

            # Waits until this selector has been rendered as it contains most of the data, then runs the parser
            await page.waitForSelector(".result-r")
            html = await page.content()
            agent = "Beaux Villages"
            link_url = url

            soup = BeautifulSoup(html, "html.parser")

            label_div = soup.find_all("div", "label-r")
            result_div = soup.find_all("div", "result-r")
            label_list = [item.get_text().strip() for item in label_div]
            result_list = [
                item.get_text().replace("m2", "").strip() for item in result_div
            ]

            town = None
            postcode = None
            rooms = None
            bedrooms = None
            size = None
            plot = None

            for i in range(len(label_list)):
                if label_list[i] == "Référence":
                    ref = result_list[i]
                elif label_list[i] == "Chambres":
                    try:
                        bedrooms = int(result_list[i])
                    except:
                        pass
                elif label_list[i] == "Secteur":
                    try:
                        town = unidecode(result_list[i].replace("-", " ")).capitalize()
                    except:
                        pass
                elif label_list[i] == "Type de bien":
                    types = result_list[i]
                    if "," in types:
                        types = types.split(",")[0].strip()
                elif label_list[i] == "Espace habitable":
                    try:
                        size = int(result_list[i])
                    except:
                        pass
                elif label_list[i] == "Surface terrain":
                    try:
                        plot = int(result_list[i])
                    except:
                        pass
                elif label_list[i] == "N° pieces":
                    try:
                        rooms = int(result_list[i])
                    except:
                        pass

            # print(ref)
            # print(type(ref))
            # print(plot)
            # print(type(plot))
            # print(size)
            # print(type(size))
            # print(town)
            # print(types)
            # print(bedrooms)
            # print(rooms)
            # print(type(bedrooms))

            price_raw = soup.find("div", class_="ip-detail-price").get_text()
            price = int("".join([x for x in price_raw if x.isnumeric()]))

            # print(price)
            try:
                description = []
                description_raw = (
                    soup.find("div", class_="span_8 pull-left description-col")
                    .get_text(separator="\n", strip=True)
                    .splitlines()
                )
                for line in description_raw:
                    if "Géorisques" or "Plus de détails" in line:
                        break
                    if line:
                        description.append(line)
            except:
                description - []
            # pprint(description)

            for postcode_key, towns in postcodes_dict.items():
                if town.casefold() in towns:
                    postcode = postcode_key
                    break

            gps = None
            try:
                if isinstance(town, str):
                    # Check if town is in premade database of GPS locations, if not searches for GPS
                    if (postcode + ";" + town.casefold()) in gps_dict:
                        gps = gps_dict[postcode + ";" + town.casefold()]
                    else:
                        try:
                            gps = get_gps(town, postcode)
                        except:
                            gps = None
            except:
                print(
                    f"Town and postcode information not correctly found. Information as scraped: \nTown: {town}, Postcode: {postcode}, GPS: {gps}, URL: {url}"
                )

            photos = []
            try:
                photos_div = soup.find("div", id="ipgalleryplug")
                photos_raw = photos_div.find_all("a")
                for link in photos_raw:
                    photos.append(link.get("href"))
            except:
                pass

            photos_hosted = photos

            listing = Listing(
                types,
                town,
                postcode,
                price,
                agent,
                ref,
                bedrooms,
                rooms,
                plot,
                size,
                link_url,
                description,
                photos,
                photos_hosted,
                gps,
            )

            # print("Listing scraped", time.perf_counter())
            return listing.__dict__
        except Exception as e:
            # print(f"Failed url: {url}")
            # print(e)
            return url
        finally:
            await page.close()


async def run_scrape(links_to_scrape):
    # Semaphore used to limit the number of active coroutines. Above 20 results in some connections being closed by the remote host and scrapes failing. No semaphore usually results in all links failing. Semaphore = 10 resulted in the best time across 100 links, approx 96 seconds. Semaphore = 1 takes 286 seconds (since it's no longer asynchronous), 5 and 20 both around 100 seconds.

    semaphore = asyncio.Semaphore(10)
    browser = await launch(headless=True)
    tasks = []

    for link in links_to_scrape:
        tasks.append(
            asyncio.ensure_future(get_listing_details(link, semaphore, browser))
        )
    listings = await asyncio.gather(*tasks)

    await browser.close()
    return listings


# This function will block any request for images or CSS from the page loading. Reduces time required by approx 25%
async def block_images(request):
    if request.resourceType in ["image", "stylesheet"]:
        await request.abort()
    else:
        await request.continue_()


# Time taken to scrape 50 links 10 semaphore: 43.56s images and CSS blocked
# Time taken to scrape 50 links 10 semaphore: 57.72s downloading everything

# beaux_listings = beaux_get_listings()

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(beaux_listings, outfile, ensure_ascii=False)

# get_links(url)


# get_listing_details("https://beauxvillages.com/fr/nos-biens_fr/property/244923-BVI59352")
