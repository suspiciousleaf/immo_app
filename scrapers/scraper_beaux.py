import time
import math
import json
import concurrent.futures

import grequests
import requests
from bs4 import BeautifulSoup, Tag
from pprint import pprint
from unidecode import unidecode

from utilities.utility_holder import get_data, get_gps
from models import Listing


try:
    with open("static/data/postcode_mapping.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/static/data/postcode_mapping.json",
        "r",
        encoding="utf8",
    ) as infile:
        postcodes_dict = json.load(infile)

try:
    try:
        with open("static/data/town_gps_mapping.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/static/data/town_gps_mapping.json",
            "r",
            encoding="utf8",
        ) as infile:
            gps_dict = json.load(infile)
except:
    print("gps_dict not found")
    gps_dict = []


def beaux_get_listings(old_listing_urls_dict):
    t0 = time.perf_counter()

    URL = "https://beauxvillages.com/fr/nos-biens_fr?option=com_iproperty&view=allproperties&id=0&layout=&autocomplete=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne&filter_province=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne&filter_county=&filter_postcode=&filter_province_num=&filter_price_low=&filter_price_high=&filter_sqft_low=&filter_lotsize_low=&filter_beds=&filter_baths=&filter_keyword=&filter_order=p.price&filter_order_Dir=ASC&commit=&5bc7231ed8719985964946f9e5a4b610=1&Itemid=10504793"

    page = requests.get(URL)

    soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = soup.find("span", class_="ip-pagination-results").get_text()
    num_props_div = [int(num) for num in num_props_div.split() if num.isnumeric()]
    num_props = num_props_div[2]
    per_page = num_props_div[1]
    print(f"\nBeaux Villages number of listings: {num_props}")
    pages = math.ceil(num_props / per_page)
    # This retrieves the total number of listings, and the number of search page results
    print(f"Pages: {pages}")

    search_urls = [
        f"https://beauxvillages.com/fr/nos-biens_fr?option=com_iproperty&view=allproperties&id=0&layout=&autocomplete=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne%2CAude&filter_province=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne&filter_county=Aude&filter_order=p.price&filter_order_Dir=ASC&commit=&5a7fb023d0edd8037757cf17e9634828=1&Itemid=10504793&start={i*per_page}"
        for i in range(pages)
    ]

    links = []

    resp = get_data(search_urls, header=False)
    for item in resp:
        links += beaux_get_links(item["response"])

    print("Number of unique listing URLs found:", len(links))

    links_old = set(old_listing_urls_dict.keys())

    links_to_scrape = [link for link in links if link not in links_old]
    print("New listings to add:", len(links_to_scrape))
    # pprint(links_to_scrape)
    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))
    # pprint(links_dead)

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    #   async scraping is too fast, results in many 503 responses. Multi-threading is just slow enough to get all the responses, and async still works for the photos

    listings = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        resp_to_scrape = get_data(links_to_scrape, header=False)
        results = executor.map(
            get_listing_details,
            (item["response"] for item in resp_to_scrape),
            links_to_scrape,
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

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Time elapsed for Beaux Villages: {time_taken:.2f}s")

    return {"listings": listings, "urls_to_remove": links_dead}


def beaux_get_links(page):
    beaux_listing_soup = BeautifulSoup(page.content, "html.parser")
    listing_urls = beaux_listing_soup.find_all("div", class_="ip-property-thumb-holder")
    page_links = []
    for div in listing_urls:
        suffix = div.find("a")
        if isinstance(suffix, Tag):
            try:
                page_links.append("https://beauxvillages.com" + str(suffix.get("href")))
            except:
                pass
    # pprint(page_links)
    return page_links


def get_listing_details(page, url):
    try:
        agent = "Beaux Villages"
        link_url = url

        soup = BeautifulSoup(page.content, "html.parser")

        label_div = soup.find_all("div", "label-r")
        result_div = soup.find_all("div", "result-r")
        label_list = [item.get_text().strip() for item in label_div]
        result_list = [item.get_text().replace("m2", "").strip() for item in result_div]

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
            elif label_list[i] == "Surface habitable":
                try:
                    size = int(result_list[i])
                except:
                    pass
            elif label_list[i] == "Surface terrain":
                try:
                    plot = int(result_list[i].replace(",", ""))
                except:
                    pass
            elif label_list[i] == "N° pieces":
                try:
                    rooms = int(result_list[i])
                except:
                    pass

        # Location of "rooms" changed in some listings, code below catches second location.
        if rooms is None:
            label_div_pieces = soup.find_all("div", "label-r-com")
            result_div_pieces = soup.find_all("div", "result-r-com")
            label_list_pieces = [item.get_text().strip() for item in label_div_pieces]
            result_list_pieces = [
                item.get_text(strip=True) for item in result_div_pieces
            ]

            for i in range(len(label_div_pieces)):
                if label_list_pieces[i] == "N° pieces":
                    try:
                        rooms = int(result_list_pieces[i])
                    except:
                        pass

        price_raw = soup.find("div", class_="ip-detail-price").contents[0]
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
                if "Géorisques" in line or "Plus de détails" in line:
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
            pass
            # print(
            #     f"Town and postcode information not correctly found. Information as scraped: \nTown: {town}, Postcode: {postcode}, GPS: {gps}, URL: {url}"
            # )

        photos = []
        try:
            photos_div = soup.find("div", id="ipgalleryplug")
            photos_raw = photos_div.find_all("a")
            for link in photos_raw:
                try:
                    photos.append(link.get("href"))
                except:
                    pass
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

        return listing.__dict__
    except Exception as e:
        return f"{url}: {str(e)}"


# url = "https://beauxvillages.com/fr/nos-biens_fr/property/300274-BVI72287"


# get_listing_details(requests.get(url), url)

# beaux_get_listings()

# for url in search_urls:
#     page = requests.get(url)
#     with open("response.html", mode="w", encoding="utf-8") as outfile:
#         for line in page.text:
#             outfile.write(line)
