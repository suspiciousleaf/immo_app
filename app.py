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
from ami_image_download import get_ami_images
import json
import time
from unidecode import unidecode

t0 = time.time()

jammes_listings = jammes_get_listings()
time_stone_listings = time_stone_get_listings()
aude_immo_listings = aude_immo_get_listings()
richardson_listings = richardson_get_listings()
cimm_listings = cimm_get_listings()
arthur_immo_listings = arthur_immo_get_listings()
mm_immo_listings = mm_immo_get_listings()
nestenn_listings = nestenn_immo_get_listings()
api_listings = api_get_listings()
ami09_listings = ami09_get_listings()
immo_chez_toit_listings = immo_chez_toit_get_listings()

all_listings = (jammes_listings + 
                time_stone_listings + 
                aude_immo_listings + 
                richardson_listings + 
                cimm_listings + 
                arthur_immo_listings +
                mm_immo_listings +
                nestenn_listings +
                api_listings +
                ami09_listings + 
                immo_chez_toit_listings)


i = 0

house_catetogies = ['Autre','Batiment','Cafe','Chalet','Chambre','Chateau','Gite','Grange','Hotel','Investissement','Local','Maison','Propriete','Remise','Restaurant','Villa', 'Ferme','Longere','Demeure']

commerce_categories = ['Agence', 'Ateliers', 'Bazar', 'Tabac', 'Bergerie', 'Boucherie', 'Bureau', 'Chocolaterie', 'Entrepots', 'Epicerie', 'Fleuriste', 'Fonds', 'Fonds-de-commerce', 'Garage', 'Locaux', 'Parking', 'Pret']

apartment_categories = ["Apartment", "Studio", "Duplex", "Appartment", "Appartement"]

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

get_ami_images()

print("Total listings: ", len(all_listings))
print("COMPLETE")

t1 = time.time()

time_taken = t1-t0
print("Time elapsed:", time_taken)