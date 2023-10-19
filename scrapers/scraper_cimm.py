import json
import requests
import time

from pprint import pprint
from unidecode import unidecode

from models import Listing

# This scraper is different - Cimm have an accessible API so each time it runs, all properties are scraped and returned, and images are used from their server rather than downloaded and hosted locally. The whole process takes approx 1 second, so no real benefit for async etc.


def cimm_get_listings(old_listing_urls_dict, sold_url_list):
    t0 = time.perf_counter()

    print("Starting Cimm Immobilier")

    URL = "https://api.cimm.com/api/realties?agencies=12444"
    page = requests.get(URL)

    cimm_listing = json.loads(page.content.decode("utf-8"))

    cimm_listings = [
        cimm_create_listing(listing) for listing in cimm_listing["results"]
    ]

    # Terrain listings often show the plot area in place of the building area, this swaps them back over.
    for listing in cimm_listings:
        if listing["types"] == "Terrain":
            if listing["size"] and listing["plot"] == None:
                listing["plot"] = listing["size"]
                listing["size"] = None

    cimm_listings = [
        listing for listing in cimm_listings if listing["link_url"] not in sold_url_list
    ]

    links = set([listing["link_url"] for listing in cimm_listings])

    links_old = set(old_listing_urls_dict.keys())

    links_to_scrape = set([link for link in links if link not in links_old])
    print("New listings to add:", len(links_to_scrape))
    # pprint(links_to_scrape)
    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))

    listings_to_return = [
        listing for listing in cimm_listings if listing["link_url"] in links_to_scrape
    ]

    t1 = time.perf_counter()
    time_taken = t1 - t0
    print(f"\nTime elapsed for Cimm Immobilier: {time_taken:.2f}s")

    return {"listings": listings_to_return, "urls_to_remove": links_dead}


def cimm_create_listing(listing):
    types = listing["realty_family"].capitalize()
    town = unidecode(listing["real_city"]).capitalize().replace("-", " ")
    postcode = listing["real_cp"]
    price = int(listing["price"])
    agent = "Cimm Immobilier"
    ref = listing["reference"]
    bedrooms = listing["bedroom_number"]
    rooms = listing["room_number"]
    gps = [
        listing["public_location"]["coordinates"][1],
        listing["public_location"]["coordinates"][0],
    ]
    if listing["field_surface"] == None:
        plot = None
    else:
        plot = int(listing["field_surface"])
    if listing["inhabitable_surface"] == None:
        size = None
    else:
        size = int(listing["inhabitable_surface"])
    link_url = "https://cimm.com/bien/" + listing["slug"]
    try:
        description_raw = listing["fr_text"].replace("\\", "").splitlines()
        description = [string for string in description_raw if string]
    except:
        description = []

    photos = []
    photos.append(listing["photo"])
    for i in range(len(listing["realtyphoto_set"])):
        photos.append(listing["realtyphoto_set"][i]["image"])
    photos_hosted = photos

    return Listing(
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
    ).__dict__


# try:
#     with open("sold_urls.json", "r", encoding="utf8") as infile:
#         sold_url_list = json.load(infile)
# except:
#     sold_url_list = {"urls": []}

# cimm_listings = cimm_get_listings(sold_url_list)
# for listing in cimm_listings:
#     print(listing["description"])
