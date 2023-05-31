# Running this program will run all of the scrapers. If a listings.json file is found it will add newly found listings and remove ones that are no longer present on the agent websites. If no listings.json file is present, it will build one from scratch. Typical time to run an update is 1 minute, building a new one is around 3 minutes. If no photos are hosted, it can be as little as 90 seconds.

import json
import time

from pprint import pprint

# This library is used frequently to remove accepts from letters (used frequently in French), as some listings use accents correctly and some don't.
from unidecode import unidecode

t0 = time.time()

from utilities.image_sold_checker import sold_image_check
from scrapers.scraper_ami09 import ami09_get_listings
from scrapers.scraper_api import api_get_listings
from scrapers.scraper_arthur_immo import arthur_immo_get_listings
from scrapers.scraper_aude import aude_immo_get_listings
from scrapers.scraper_beaux import beaux_get_listings
from scrapers.scraper_c21 import c21_get_listings
from scrapers.scraper_cimm import cimm_get_listings
from scrapers.scraper_eureka import eureka_immo_get_listings
from scrapers.scraper_europe_sud import europe_sud_get_listings
from scrapers.scraper_iad import iad_immo_get_listings
from scrapers.scraper_immo_chez_toit import immo_chez_toit_get_listings
from scrapers.scraper_jammes import jammes_get_listings
from scrapers.scraper_mm import mm_immo_get_listings
from scrapers.scraper_nestenn import nestenn_immo_get_listings
from scrapers.scraper_richardson import richardson_get_listings
from scrapers.scraper_safti import safti_get_listings
from scrapers.scraper_selection_habitat import selection_get_listings
from scrapers.scraper_sextant import sextant_get_listings
from scrapers.scraper_time_stone import time_stone_get_listings

# The code below will run the imported scraper for each agent, host_photos will determine if the photos for each listing are downloaded, resized, and compressed for local hosting. Try/except is used to prevent an error with a single scraper causing the whole program to fail to run. Faults are reported to the failed_scrapes list, and finally to the console.

try:
    with open(
        "times_run_since_last_image_scan_counter.json", "r", encoding="utf8"
    ) as infile:
        times_run_since_last_image_scan = json.load(infile)
except:
    # If not found, will run the image scan
    times_run_since_last_image_scan = {"counter": 5}

try:
    with open("sold_urls.json", "r", encoding="utf8") as infile:
        sold_urls = json.load(infile)
except:
    sold_urls = {"urls": []}

sold_url_list = sold_urls["urls"]

failed_scrapes = []
try:
    # Must be True as host website blocks leeching for many photos
    ami09_listings = ami09_get_listings(host_photos=True)
except:
    ami09_listings = []
    failed_scrapes.append("Ami Immobilier")
try:
    api_listings = api_get_listings(host_photos=False)
except:
    api_listings = []
    failed_scrapes.append("A.P.I.")
try:
    arthur_immo_listings = arthur_immo_get_listings(sold_url_list, host_photos=False)
except:
    arthur_immo_listings = []
    failed_scrapes.append("Arthur Immo")
try:
    aude_immo_listings = aude_immo_get_listings(host_photos=False)
except:
    aude_immo_listings = []
    failed_scrapes.append("Aude Immobilier")
try:
    # host photos option not needed
    beaux_listings = beaux_get_listings()
except:
    beaux_listings = []
    failed_scrapes.append("Beaux Villages")
try:
    c21_listings = c21_get_listings(host_photos=False)
except:
    c21_listings = []
    failed_scrapes.append("Century 21")
try:
    # host photos not needed due to public API use for Cimm
    cimm_listings = cimm_get_listings(sold_url_list)
except:
    cimm_listings = []
    failed_scrapes.append("Cimm Immobilier")
try:
    eureka_immo_listings = eureka_immo_get_listings(host_photos=False)
except:
    eureka_immo_listings = []
    failed_scrapes.append("Eureka Immobilier")
try:
    europe_sud_listings = europe_sud_get_listings(host_photos=False)
except:
    europe_sud_listings = []
    failed_scrapes.append("Europe Sud Immobilier")
try:
    iad_listings = iad_immo_get_listings(host_photos=False)
except:
    iad_listings = []
    failed_scrapes.append("IAD Immobilier")
try:
    immo_chez_toit_listings = immo_chez_toit_get_listings(host_photos=False)
except:
    immo_chez_toit_listings = []
    failed_scrapes.append("L'Immo Chez Toit")
try:
    jammes_listings = jammes_get_listings(sold_url_list, host_photos=False)
except:
    jammes_listings = []
    failed_scrapes.append("Cabinet Jammes")
try:
    mm_immo_listings = mm_immo_get_listings(sold_url_list, host_photos=False)
except:
    mm_immo_listings = []
    failed_scrapes.append("M&M Immobilier")
try:
    nestenn_listings = nestenn_immo_get_listings(host_photos=False)
except:
    nestenn_listings = []
    failed_scrapes.append("Nestenn")
try:
    # Must be True as host website uses HTTP instead of HTTPS, can't embed images
    richardson_listings = richardson_get_listings(host_photos=True)
except:
    richardson_listings = []
    failed_scrapes.append("Richardson Immobilier")
try:
    # host photos option not needed
    safti_listings = safti_get_listings(sold_url_list)
except:
    safti_listings = []
    failed_scrapes.append("Safti")
try:
    selection_listings = selection_get_listings(host_photos=False)
except:
    selection_listings = []
    failed_scrapes.append("Selection Habitat")
try:
    sextant_listings = sextant_get_listings(sold_url_list, host_photos=False)
except:
    sextant_listings = []
    failed_scrapes.append("Sextant")
try:
    time_stone_listings = time_stone_get_listings(sold_url_list, host_photos=False)
except:
    time_stone_listings = []
    failed_scrapes.append("Time & Stone Immobilier")

if failed_scrapes:
    print(f"The following agent(s) failed to scrape entirely: {failed_scrapes}")

all_listings = (
    ami09_listings
    + api_listings
    + arthur_immo_listings
    + aude_immo_listings
    + beaux_listings
    + c21_listings
    + cimm_listings
    + eureka_immo_listings
    + europe_sud_listings
    + iad_listings
    + immo_chez_toit_listings
    + jammes_listings
    + mm_immo_listings
    + nestenn_listings
    + richardson_listings
    + safti_listings
    + selection_listings
    + sextant_listings
    + time_stone_listings
)

# The combined listings have a huge range of property categories, the code below reduces the total categories down to six. House, apartment, multi-lodging buildings, commercial property, empty land, and "other". Any listings that don't fit into the first five are reclassified as "other", and the original type is saved to "types_original" so it can be examined and classified later.

property_types = {
    "Maison": {
        "Autre",
        "Batiment",
        "Cafe",
        "Chalet",
        "Chambre",
        "Chateau",
        "Domaine",
        "Gite",
        "Grange",
        "Hotel",
        "Investissement",
        "Local",
        "Maison",
        "Mas",
        "Peniche",
        "Propriete",
        "Remise",
        "Restaurant",
        "Villa",
        "Ferme",
        "Longere",
        "Demeure",
        "Pavillon",
        "Corps",
        "Residence",
    },
    "Commerce": {
        "Agence",
        "Ateliers",
        "Bar",
        "Bazar",
        "Tabac",
        "Bergerie",
        "Boucherie",
        "Bureau",
        "Cave",
        "Chocolaterie",
        "Divers",
        "Entrepots",
        "Epicerie",
        "Fleuriste",
        "Fonds",
        "Fonds-de-commerce",
        "Garage",
        "Haras",
        "Locaux",
        "Parking",
        "Pret",
        "Hangar",
        "Atelier",
        "Local commercial",
    },
    "Appartement": {
        "Apartment",
        "Studio",
        "Duplex",
        "Appartment",
        "Appartement",
        "Appart’hôtel",
        "Appart'hotel",
    },
}

uncategorized_types = []

for listing in all_listings:
    listing["types"] = unidecode(listing["types"].capitalize())
    temp_type = listing["types"]
    # Maison is the most common type, and some descriptions have "maison" as the second word (eg jolie maison), so the split line would cause the maison to be lost, leaving the type as jolie in the example
    if "maison" in listing["types"].casefold():
        listing["types"] = "Maison"
    if len(listing["types"].split()) > 1:
        listing["types"] = listing["types"].split()[0]
        # "temp_type" is used to store the type of property. If it is unknown and is corrected to "Other", the original listing type can stll be accessed and categorised later.
        temp_type = listing["types"].split()[0]
    for property_type, values in property_types.items():
        if temp_type in values:
            listing["types"] = property_type
    if listing["types"] not in [
        "Maison",
        "Appartement",
        "Immeuble",
        "Terrain",
        "Commerce",
        "Other",
    ]:
        uncategorized_types.append(
            {"types": listing["types"], "url": listing["link_url"]}
        )
        listing["types_original"] = listing["types"]
        listing["types"] = "Other"

    try:
        # Try/except is used as some listings return a town of None, which errors unidecode
        listing["town"] = unidecode(listing["town"])
    except:
        pass

if uncategorized_types:
    print("\nThe following uncategorized property types were found:")
    pprint(uncategorized_types)

# This counts up each time the scraper is run, and will run the function that scans main images for "Sold" etc text to remove those listings once every five times the scraper runs

number_listings_before_image_scan = len(all_listings)
if times_run_since_last_image_scan["counter"] >= 5:
    try:
        print("\nImage scan function running, this will take approx 90 seconds")
        all_listings = sold_image_check(all_listings)
        times_run_since_last_image_scan["counter"] = 0
        print(
            f"Number of listings removed by image scan: {number_listings_before_image_scan - len(all_listings)}"
        )
    except Exception as e:
        print(f"Image filter failed: {e}")
else:
    times_run_since_last_image_scan["counter"] += 1

# The code below takes the final list of dictionaries and saves it as a json.
with open("listings.json", "w", encoding="utf-8") as outfile:
    json.dump(all_listings, outfile, ensure_ascii=False)

# This saves the updated counter for the image scan
with open(
    "times_run_since_last_image_scan_counter.json", "w", encoding="utf-8"
) as outfile:
    json.dump(times_run_since_last_image_scan, outfile, ensure_ascii=False)

print("\n\nTotal listings: ", len(all_listings))
print("COMPLETE")

t1 = time.time()

time_taken = t1 - t0
print(f"Total time elapsed: {time_taken:.2f}s")
