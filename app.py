# Running this the first time, with no listings.json, will take around three hours. Running with a recent listongs.json with no listings to update will take around 90 seconds.

from jammes_scrape import jammes_get_listings
from time_stone_scrape import time_stone_get_listings
from aude_immo_scrape import aude_immo_get_listings
from richardson_scrape import richardson_get_listings
from cimm_immo_scrape import cimm_get_listings
from arthur_immo_scrape import arthur_immo_get_listings
from mm_immo_scrape import mm_immo_get_listings
from nestenn_immo_scrape import nestenn_immo_get_listings
from api_immo_scrape import api_get_listings
from ami09_immo_scrape import ami09_get_listings
from immo_chez_toit import immo_chez_toit_get_listings

import json
import time
from unidecode import unidecode

t0 = time.time()

failed_scrapes = []
try:
    ami09_listings = ami09_get_listings()
except:
    ami09_listings = []
    failed_scrapes.append("Ami Immobilier")

try:
    api_listings = api_get_listings()
except:
    api_listings = []
    failed_scrapes.append("A.P.I.")

try:
    arthur_immo_listings = arthur_immo_get_listings()
except:
    arthur_immo_listings = []
    failed_scrapes.append("Arthur Immo")

try:
    aude_immo_listings = aude_immo_get_listings()
except:
    aude_immo_listings = []
    failed_scrapes.append("Aude Immobilier")

try:
    cimm_listings = cimm_get_listings()
except:
    cimm_listings = []
    failed_scrapes.append("Cimm Immobilier")

try:
    immo_chez_toit_listings = immo_chez_toit_get_listings()
except:
    immo_chez_toit_listings = []
    failed_scrapes.append("L'Immo Chez Toit")

try:    
    jammes_listings = jammes_get_listings()
except:
    jammes_listings = []
    failed_scrapes.append("Cabinet Jammes")

try:
    mm_immo_listings = mm_immo_get_listings()
except:
    mm_immo_listings = []
    failed_scrapes.append("M&M Immobilier")

try:
    nestenn_listings = nestenn_immo_get_listings()
except:
    nestenn_listings = []
    failed_scrapes.append("Nestenn")

try:
    richardson_listings = richardson_get_listings()
except:
    richardson_listings = []
    failed_scrapes.append("Richardson Immobilier")

try:
    time_stone_listings = time_stone_get_listings()
except:
    time_stone_listings = []
    failed_scrapes.append("Time & Stone Immobilier")

if failed_scrapes:
    print(f"The following agent(s) failed to scrape entirely: {failed_scrapes}")

all_listings = (ami09_listings +
                api_listings +
                arthur_immo_listings +
                aude_immo_listings + 
                cimm_listings + 
                immo_chez_toit_listings +
                jammes_listings + 
                mm_immo_listings +
                nestenn_listings +
                richardson_listings + 
                time_stone_listings
)

# The combined listings have a huge range of property categories, the code below reduces the total categories down to five. house, apartment, multi-lodging buildings, commercial property, and empty land

house_catetogies = ['Autre','Batiment','Cafe','Chalet','Chambre','Chateau','Gite','Grange','Hotel','Investissement','Local','Maison','Propriete','Remise','Restaurant','Villa', 'Ferme','Longere','Demeure']

commerce_categories = ['Agence', 'Ateliers', 'Bazar', 'Tabac', 'Bergerie', 'Boucherie', 'Bureau', 'Chocolaterie', 'Entrepots', 'Epicerie', 'Fleuriste', 'Fonds', 'Fonds-de-commerce', 'Garage', 'Locaux', 'Parking', 'Pret']

apartment_categories = ["Apartment", "Studio", "Duplex", "Appartment", "Appartement"]

i = 0
for listing in all_listings:
    listing["types"] = unidecode(listing["types"].capitalize())
    if len(listing["types"].split()) > 1:
        listing["types"] = listing["types"].split()[0]
    if listing["types"] in house_catetogies:
        listing["types"] = "Maison"
    if listing["types"] in commerce_categories:
        listing["types"] = "Commerce"
    if listing["types"] in apartment_categories:
        listing["types"] = "Appartement"
    listing["id"] = i
    i += 1
    try:
        listing["town"] = unidecode(listing["town"])
    except:
        pass

with open("listings.json", "w") as outfile:
    json.dump(all_listings, outfile)

print("Total listings: ", len(all_listings))
print("COMPLETE")

t1 = time.time()

time_taken = t1-t0
print("Time elapsed:", time_taken)
