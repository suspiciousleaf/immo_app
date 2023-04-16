import json
from pprint import pprint
from models import Listing
from unidecode import unidecode
import requests

def cimm_get_listings():

    URL = "https://api.cimm.com/api/realties?agencies=12444"
    page = requests.get(URL)

    cimm_listing = json.loads(page.content)
        
    def cimm_create_listing(listing):
        types = listing["realty_family"].capitalize()
        town = listing["real_city"].capitalize()
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
        # print(gps)

        return Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, photos_hosted, gps)

    cimm_listings = [cimm_create_listing(listing).__dict__ for listing in cimm_listing["results"]]
    
    return cimm_listings

# pprint(cimm_listings)

# cimm_get_listings()


