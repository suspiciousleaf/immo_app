import os
import time
import math
import json
import concurrent.futures


# This must be imported as it is imported with get_gps, and if requests is imported before grequests it will cause recursion error
import grequests
import requests
from pprint import pprint
from bs4 import BeautifulSoup, NavigableString, Tag
import shutil
from unidecode import unidecode

from utilities.async_image_downloader import make_photos_dir, dl_comp_photo
from json_search import agent_dict
from models import Listing
from utilities.utilities import get_gps, get_data

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


def api_get_listings(host_photos=False):
    t0 = time.perf_counter()

    URL = "http://www.pyrenees-immobilier.com/fr/annonces-immobilieres-p-r12-1.html#page=1"
    page = requests.get(URL)

    api_soup = BeautifulSoup(page.content, "html.parser")

    num_props = int(api_soup.find("span", id="NbBien").get_text())
    print("\nApi Immo number of listings:", num_props)
    pages = math.ceil(num_props / 10)
    print("Pages:", pages)

    links = []

    results_pages = [
        f"http://www.pyrenees-immobilier.com/fr/annonces-immobilieres-p-r12-{i}.html#page={i}"
        for i in range(1, pages + 1)
    ]
    resp = get_data(results_pages)
    for item in resp:
        links += api_get_links(item["response"])

    print("Number of unique listing URLs found:", len(links))

    listings = [listing for listing in listings_json if listing["agent"] == "A.P.I."]

    links_old = []
    for listing in listings:
        if listing["agent"] == "A.P.I.":
            links_old.append(listing["link_url"])
    # print("Listings found from prevous scrape:", len(links_old))

    links_to_scrape = [link for link in links if link not in links_old]
    print("New listings to add:", len(links_to_scrape))
    # pprint(links_to_scrape)
    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))
    # pprint(links_dead)

    listing_photos_to_delete_local = []

    if links_dead:
        for listing in listings:
            if listing["link_url"] in links_dead:
                listing_photos_to_delete_local.append(listing["ref"])
                listings.remove(listing)

        for listing_ref in listing_photos_to_delete_local:
            try:
                shutil.rmtree(
                    f"{cwd}/static/images/api/{listing_ref}", ignore_errors=True
                )
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    #   async scraping is too fast, results in many 503 responses. Multi-threading is just slow enough to get all the responses, and async still works for the photos

    with concurrent.futures.ThreadPoolExecutor() as executor:
        response_objects = executor.map(
            requests.get, (link for link in links_to_scrape)
        )
        results = executor.map(
            get_listing_details,
            (item for item in response_objects),
            links_to_scrape,
            [host_photos for x in links_to_scrape],
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
    print(f"Time elapsed for A.P.I: {time_taken:.2f}s")

    return listings


def api_get_links(page):
    api_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in api_soup.find_all("a"):
        links_raw.add(link.get("href"))
    links_raw.discard(None)
    links = [
        link
        for link in links_raw
        if "http://www.pyrenees-immobilier.com/fr/vente" in link
    ]

    return links


def get_listing_details(page, url, host_photos):
    try:
        agent = "A.P.I."
        soup = BeautifulSoup(page.content, "html.parser")
        link_url = url

        # print("\n\nNext property\n")

        # Get type

        types = soup.find("div", class_="type").get_text()
        # print("Type:", types)

        # Get location
        postcode_div = soup.find("h1").get_text()
        postcode_div = postcode_div.split()
        postcode_string = [line for line in postcode_div if "(" in line][0]
        postcode = "".join([num for num in postcode_string if num.isdigit()])
        # print("Postcode:", postcode)

        town = unidecode(soup.find("div", class_="ville").get_text().capitalize())
        # print("Town:", town)

        # Get price
        price_div = soup.find("div", class_="price-all").get_text()
        price = int("".join([num for num in price_div if num.isdigit()]))
        # print("Price:", price, "€")

        # Get ref

        details_div = soup.find("div", class_="detail-bien-specs").get_text()
        details_div = details_div.split("\n")
        prop_ref = [line for line in details_div if "Ref" in line and len(line) < 10][0]
        ref = "".join([num for num in prop_ref if num.isdigit()])

        # print("ref:", ref)

        # Get property details

        try:
            bedrooms = [line for line in details_div if "Chambres" in line][0]
            bedrooms = int("".join([num for num in bedrooms if num.isdigit()]))
        except:
            bedrooms = None

        # print("Bedrooms:", bedrooms)

        # Rooms
        try:
            rooms = [line for line in details_div if "Pièces" in line][0]
            rooms = int("".join([num for num in rooms if num.isdigit()]))
        except:
            rooms = None

        # print("Rooms:", rooms)

        # Plot size
        try:
            plot = [
                line for line in details_div if "Terrain" in line and "Type" not in line
            ][0]
            plot = int(
                "".join([num for num in plot if num.isdigit() and num.isascii()])
            )
        except:
            plot = None

        # print("Plot:", plot, "m²")

        # Property size
        try:
            size = [line for line in details_div if "Surface" in line][0]
            size = int(
                "".join([num for num in size if num.isdigit() and num.isascii()])
            )
        except:
            size = None

        # print("Size:", size, "m²")

        description_list = []
        description_raw = soup.find("div", class_="detail-bien-desc-content").p.contents
        for item in description_raw:
            # print(type(item))
            if isinstance(item, NavigableString):
                description_list.append(item)
            if isinstance(item, Tag):
                for element in item.contents:
                    if len(element.get_text()) > 3:
                        description_list.extend(element.get_text().splitlines())

        for i, item in enumerate(description_list):
            if "PYRENEES IMMOBILIER (API)" in item:
                try:
                    description_list[i] = item[
                        : item.find("PYRENEES IMMOBILIER (API)") - 7
                    ]
                except:
                    pass

        description = [
            elem.strip()
            for elem in description_list
            if elem.strip() and "www.georisques.gouv.fr" not in elem
        ]
        # print(description)

        # Photos
        photos = []
        photos_div = soup.find_all("img", class_="photo-large")
        for element in photos_div:
            if "https://assets.adaptimmo.com/" in element.get("src"):
                photos.append(element.get("src"))
        # pprint(photos)

        if host_photos:
            agent_abbr = [i for i in agent_dict if agent_dict[i] == agent][0]

            make_photos_dir(ref, cwd, agent_abbr)

            photos_hosted = []
            i = 0
            failed = 0

            resp = get_data(photos, header=False)
            for item in resp:
                try:
                    photos_hosted.append(
                        dl_comp_photo(item["response"], ref, i, cwd, agent_abbr)
                    )
                    i += 1
                except:
                    failed += 1

            if failed:
                print(f"{failed} photos failed to scrape")
        else:
            photos_hosted = photos

        gps = None
        if isinstance(town, str):
            # Check if town is in premade database of GPS locations, if not searches for GPS
            if (postcode + ";" + town.casefold()) in gps_dict:
                gps = gps_dict[postcode + ";" + town.casefold()]
            else:
                try:
                    gps = get_gps(town, postcode)
                except:
                    gps = None

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
        # print(e)
        return url


cwd = os.getcwd()

# test_urls = [
#     "http://www.pyrenees-immobilier.com/fr/vente-maison-foix-p-r7-0900418033.html"
# ]

# for test_url in test_urls:
#     get_listing_details(requests.get(test_url), test_url, False)

# api_listings = api_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(api_listings, outfile, ensure_ascii=False)

# Time elapsed for A.P.I: 44.31s without photos
