import json
import requests
import time
from pprint import pprint
from unidecode import unidecode
from models import Listing

# This scraper is different - Cimm have an accessible API so each time it runs, all properties are scraped and returned, and images are used from their server rather than downloaded and hosted locally. The whole process takes approx 2.5 seconds, so no real benefit for async etc.

def cimm_get_listings():

    t0 = time.time()

    URL = "https://api.cimm.com/api/realties?agencies=12444"
    page = requests.get(URL)

    cimm_listing = json.loads(page.content)

    cimm_listings = [cimm_create_listing(listing).__dict__ for listing in cimm_listing["results"]]
    
    t1 = time.time()
    time_taken = t1-t0
    print(f"Time elapsed for Cimm Immobilier: {time_taken:.2f}s")

    return cimm_listings

def cimm_create_listing(listing):
    types = listing["realty_family"].capitalize()
    town = unidecode(listing["real_city"]).capitalize()
    postcode = listing["real_cp"]
    price = int(listing["price"])
    agent = "Cimm Immobilier"
    ref = listing["reference"]
    bedrooms = listing["bedroom_number"]
    rooms = listing["room_number"]
    gps = [listing["public_location"]["coordinates"][1], listing["public_location"]["coordinates"][0]]
    if listing["field_surface"] == None:
        plot = None
    else:
        plot = int(listing["field_surface"])
    if listing["inhabitable_surface"] == None:
        size = None
    else:
        size = int(listing["inhabitable_surface"])
    link_url = "https://cimm.com/bien/" + listing["slug"]
    description = unidecode(listing["fr_text"].replace("\r", "").replace("\n", "")).replace("A2", "²").replace("A(c)", "e").replace("\\", "")

    photos = []
    photos.append(listing["photo"])
    for i in range(len(listing["realtyphoto_set"])):
        photos.append(listing["realtyphoto_set"][i]["image"])
    photos_hosted = photos

    return Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, photos_hosted, gps)

# cimm_get_listings()


