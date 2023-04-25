# Running this program will run all of the scrapers. If a listings.json file is found it will add newly found listings and remove ones that are no longer present on the agent websites. If no listings.json file is present, it will build one from scratch. Typical time to run an update is 1 minute, building a new one is around 6-10 minutes. If no photos are hosted, it can be as little as 90 seconds.

import json
import time

from unidecode import unidecode # This library is used frequently to remove accepts from letters (used frequently in French), as some listings use accents correctly and some don't. 

from scraper_jammes import jammes_get_listings
from scraper_time_stone import time_stone_get_listings
from scraper_aude import aude_immo_get_listings
from scraper_richardson import richardson_get_listings
from scraper_cimm import cimm_get_listings
from scraper_arthur_immo import arthur_immo_get_listings
from scraper_mm import mm_immo_get_listings
from scraper_nestenn import nestenn_immo_get_listings
from scraper_api import api_get_listings
from scraper_ami09 import ami09_get_listings
from scraper_immo_chez_toit import immo_chez_toit_get_listings


t0 = time.time()

# The code below will run the imported scraper for each agent, host_photos will determine if the photos for each listing are downloaded, resized, and compressed for local hosting. Try/except is used to prevent an error with a single scraper causing the whole program to fail to run. Faults are reported to the failed_scrapes list, and finally to the console.

failed_scrapes = []
try:
    ami09_listings = ami09_get_listings(host_photos=True) # Must be True as host website blocks leeching for many photos
except:
    ami09_listings = []
    failed_scrapes.append("Ami Immobilier")
try:
    api_listings = api_get_listings(host_photos=False)
except:
    api_listings = []
    failed_scrapes.append("A.P.I.")
try:
    arthur_immo_listings = arthur_immo_get_listings(host_photos=False)
except:
    arthur_immo_listings = []
    failed_scrapes.append("Arthur Immo")
try:
    aude_immo_listings = aude_immo_get_listings(host_photos=False)
except:
    aude_immo_listings = []
    failed_scrapes.append("Aude Immobilier")
try:
    cimm_listings = cimm_get_listings() # host photos not needed due to public API use for Cimm
except:
    cimm_listings = []
    failed_scrapes.append("Cimm Immobilier")
try:
    immo_chez_toit_listings = immo_chez_toit_get_listings(host_photos=False)
except:
    immo_chez_toit_listings = []
    failed_scrapes.append("L'Immo Chez Toit")
try:    
    jammes_listings = jammes_get_listings(host_photos=False)
except:
    jammes_listings = []
    failed_scrapes.append("Cabinet Jammes")
try:
    mm_immo_listings = mm_immo_get_listings(host_photos=False)
except:
    mm_immo_listings = []
    failed_scrapes.append("M&M Immobilier")
try:
    nestenn_listings = nestenn_immo_get_listings(host_photos=False)
except:
    nestenn_listings = []
    failed_scrapes.append("Nestenn")
try:
    richardson_listings = richardson_get_listings(host_photos=True) # Must be True as host website uses HTTP instead of HTTPS, can't embed images
except:
    richardson_listings = []
    failed_scrapes.append("Richardson Immobilier")
try:
    time_stone_listings = time_stone_get_listings(host_photos=False)
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

# The combined listings have a huge range of property categories, the code below reduces the total categories down to five. House, apartment, multi-lodging buildings, commercial property, and empty land. It also adds a sequential ID number to each listing, reset for all listings each time the program is run.

house_catetogies = ['Autre','Batiment','Cafe','Chalet','Chambre','Chateau','Gite','Grange','Hotel','Investissement','Local','Maison','Propriete','Remise','Restaurant','Villa', 'Ferme','Longere','Demeure', 'Pavillon', 'Corps']

commerce_categories = ['Agence', 'Ateliers', 'Bazar', 'Tabac', 'Bergerie', 'Boucherie', 'Bureau', 'Chocolaterie', 'Entrepots', 'Epicerie', 'Fleuriste', 'Fonds', 'Fonds-de-commerce', 'Garage', 'Locaux', 'Parking', 'Pret', 'Hangar', 'Atelier']

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
        listing["town"] = unidecode(listing["town"])    # Try/except is used as some listings return a town of None, which errors unidecode
    except:
        pass

# The code below takes the final list of dictionaries and saves it as a json.

with open("listings.json", "w") as outfile:
    json.dump(all_listings, outfile)

print("Total listings: ", len(all_listings))
print("COMPLETE")

t1 = time.time()

time_taken = t1-t0
print(f"Total time elapsed: {time_taken:.2f}s")

# Time elapsed: 156.5646300315857 Full scrape with blank listings.json, not including photos

# Agents to possibly add: Sphere, https://beauxvillages.com/, https://www.europe-sud-immobilier.com/, https://www.selectionhabitat.com/fr/annonces/lavelanet-p-r301-0-17747-1.html, Sextant

# Use OCR on primary photos to check if sold etc. Needed for M&M, Cimm, Jammes, Arthur, maybe others
# Deal with multiple towns that have the same name. Search sends "belesta" but no postcode
# Improve GPS dictionary building program and rebuild dictionary