# Running this program will run all of the scrapers. If a listings.json file is found it will add newly found listings and remove ones that are no longer present on the agent websites. If no listings.json file is present, it will build one from scratch. Typical time to run an update is 1 minute, building a new one is around 3 minutes. If no photos are hosted, it can be as little as 90 seconds.

import json
import time

from pprint import pprint

# This library is used to remove accents from letters (used frequently in French), as some listings use accents correctly and some don't.
from unidecode import unidecode

t0 = time.perf_counter()

from scrapers.scraper_ami09 import ami09_get_listings
from scrapers.scraper_api import api_get_listings
from scrapers.scraper_arieg import arieg_get_listings
from scrapers.scraper_arthur_immo import arthur_immo_get_listings
from scrapers.scraper_aude import aude_immo_get_listings
from scrapers.scraper_bac import bac_get_listings
from scrapers.scraper_beaux import beaux_get_listings
from scrapers.scraper_c21 import c21_get_listings
from scrapers.scraper_cimm import cimm_get_listings
from scrapers.scraper_eureka import eureka_immo_get_listings
from scrapers.scraper_europe_sud import europe_sud_get_listings
from scrapers.scraper_human import human_get_listings
from scrapers.scraper_iad import iad_immo_get_listings
from scrapers.scraper_immo_chez_toit import immo_chez_toit_get_listings
from scrapers.scraper_jammes import jammes_get_listings
from scrapers.scraper_mm import mm_immo_get_listings
from scrapers.scraper_nestenn import nestenn_immo_get_listings
from scrapers.scraper_privee import privee_get_listings
from scrapers.scraper_richardson import richardson_get_listings
from scrapers.scraper_safti import safti_get_listings
from scrapers.scraper_selection_habitat import selection_get_listings
from scrapers.scraper_sextant import sextant_get_listings
from scrapers.scraper_time_stone import time_stone_get_listings

# Import from json_search must be below scraper imports due to grequests recursion error if imported before requests
from json_search import agent_dict
from utilities.image_sold_checker import sold_image_check
from utilities.utilities import property_types

# The code below will run the imported scraper for each agent, host_photos will determine if the photos for each listing are downloaded, resized, and compressed for local hosting. Try/except is used to prevent an error with a single scraper causing the whole program to fail to run. Faults are reported to the failed_scrapes list, and finally to the console.


def main():
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

    try:
        try:
            with open("listings.json", "r", encoding="utf8") as infile:
                listings = json.load(infile)
        except:
            with open(
                "/home/suspiciousleaf/immo_app/listings.json", "r", encoding="utf8"
            ) as infile:
                listings = json.load(infile)
    except:
        listings = []

    sold_url_list = sold_urls["urls"]

    failed_scrapes = {}
    try:
        # Must be True as host website blocks leeching for many photos
        ami09_listings = ami09_get_listings(host_photos=True)
    except Exception as e:
        ami09_listings = [
            listing for listing in listings if listing["agent"] == "Ami Immobilier"
        ]
        failed_scrapes["Ami Immobilier"] = e
    try:
        api_listings = api_get_listings(host_photos=False)
    except Exception as e:
        api_listings = [listing for listing in listings if listing["agent"] == "A.P.I."]
        failed_scrapes["A.P.I."] = e
    try:
        arieg_listings = arieg_get_listings()
    except Exception as e:
        arieg_listings = [
            listing for listing in listings if listing["agent"] == "Arieg'Immo"
        ]
        failed_scrapes["Arieg'Immo"] = e
    try:
        arthur_immo_listings = arthur_immo_get_listings(
            sold_url_list, host_photos=False
        )
    except Exception as e:
        arthur_immo_listings = [
            listing for listing in listings if listing["agent"] == "Arthur Immo"
        ]
        failed_scrapes["Arthur Immo"] = e
    try:
        aude_immo_listings = aude_immo_get_listings(host_photos=False)
    except Exception as e:
        aude_immo_listings = [
            listing for listing in listings if listing["agent"] == "Aude Immobilier"
        ]
        failed_scrapes["Aude Immobilier"] = e
    try:
        bac_listings = bac_get_listings()
    except Exception as e:
        bac_listings = [
            listing for listing in listings if listing["agent"] == "BAC Immobilier"
        ]
        failed_scrapes["BAC Immobilier"] = e
    try:
        # host photos option not needed
        beaux_listings = beaux_get_listings()
    except Exception as e:
        beaux_listings = [
            listing for listing in listings if listing["agent"] == "Beaux Villages"
        ]
        failed_scrapes["Beaux Villages"] = e
    try:
        c21_listings = c21_get_listings(host_photos=False)
    except Exception as e:
        c21_listings = [
            listing for listing in listings if listing["agent"] == "Century 21"
        ]
        failed_scrapes["Century 21"] = e
    try:
        # host photos not needed due to public API use for Cimm
        cimm_listings = cimm_get_listings(sold_url_list)
    except Exception as e:
        cimm_listings = [
            listing for listing in listings if listing["agent"] == "Cimm Immobilier"
        ]
        failed_scrapes["Cimm Immobilier"] = e
    try:
        eureka_immo_listings = eureka_immo_get_listings(host_photos=False)
    except Exception as e:
        eureka_immo_listings = [
            listing for listing in listings if listing["agent"] == "Eureka Immobilier"
        ]
        failed_scrapes["Eureka Immobilier"] = e
    try:
        europe_sud_listings = europe_sud_get_listings(host_photos=False)
    except Exception as e:
        europe_sud_listings = [
            listing
            for listing in listings
            if listing["agent"] == "Europe Sud Immobilier"
        ]
        failed_scrapes["Europe Sud Immobilier"] = e
    try:
        human_listings = human_get_listings()
    except Exception as e:
        human_listings = [
            listing for listing in listings if listing["agent"] == "Human Immobilier"
        ]
        failed_scrapes["Human Immobilier"] = e
    try:
        iad_listings = iad_immo_get_listings(host_photos=False)
    except Exception as e:
        iad_listings = [
            listing for listing in listings if listing["agent"] == "IAD Immobilier"
        ]
        failed_scrapes["IAD Immobilier"] = e
    try:
        immo_chez_toit_listings = immo_chez_toit_get_listings(host_photos=False)
    except Exception as e:
        immo_chez_toit_listings = [
            listing for listing in listings if listing["agent"] == "L'Immo Chez Toit"
        ]
        failed_scrapes["L'Immo Chez Toit"] = e
    try:
        jammes_listings = jammes_get_listings(sold_url_list, host_photos=False)
    except Exception as e:
        jammes_listings = [
            listing for listing in listings if listing["agent"] == "Cabinet Jammes"
        ]
        failed_scrapes["Cabinet Jammes"] = e
    try:
        mm_immo_listings = mm_immo_get_listings(sold_url_list, host_photos=False)
    except Exception as e:
        mm_immo_listings = [
            listing for listing in listings if listing["agent"] == "M&M Immobilier"
        ]
        failed_scrapes["M&M Immobilier"] = e
    try:
        nestenn_listings = nestenn_immo_get_listings(host_photos=False)
    except Exception as e:
        nestenn_listings = [
            listing for listing in listings if listing["agent"] == "Nestenn"
        ]
        failed_scrapes["Nestenn"] = e
    try:
        privee_listings = privee_get_listings()
    except Exception as e:
        privee_listings = [
            listing for listing in listings if listing["agent"] == "Propriétés Privées"
        ]
        failed_scrapes["Propriétés Privées"] = e
    try:
        # Must be True as host website uses HTTP instead of HTTPS, can't embed images
        richardson_listings = richardson_get_listings(host_photos=True)
    except Exception as e:
        richardson_listings = [
            listing
            for listing in listings
            if listing["agent"] == "Richardson Immobilier"
        ]
        failed_scrapes["Richardson Immobilier"] = e
    try:
        # host photos option not needed
        safti_listings = safti_get_listings(sold_url_list)
    except Exception as e:
        safti_listings = [
            listing for listing in listings if listing["agent"] == "Safti"
        ]
        failed_scrapes["Safti"] = e
    try:
        selection_listings = selection_get_listings(host_photos=False)
    except Exception as e:
        selection_listings = [
            listing for listing in listings if listing["agent"] == "Selection Habitat"
        ]
        failed_scrapes["Selection Habitat"] = e
    try:
        sextant_listings = sextant_get_listings(sold_url_list)
    except Exception as e:
        sextant_listings = [
            listing for listing in listings if listing["agent"] == "Sextant"
        ]
        failed_scrapes["Sextant"] = e
    try:
        time_stone_listings = time_stone_get_listings(sold_url_list, host_photos=False)
    except Exception as e:
        time_stone_listings = [
            listing
            for listing in listings
            if listing["agent"] == "Time & Stone Immobilier"
        ]
        failed_scrapes["Time & Stone Immobilier"] = e

    # If any of the whole scrapers fail to run, the previously scraped links will be passed through, and the scraper name and exception will be passed into a dictionary. If anything is in the dictionary after they have all run, the below message will be printed.
    if failed_scrapes:
        print(f"The following agent(s) failed to scrape entirely:\n")
        pprint(failed_scrapes)

    all_listings = (
        ami09_listings
        + api_listings
        + arieg_listings
        + arthur_immo_listings
        + aude_immo_listings
        + bac_listings
        + beaux_listings
        + c21_listings
        + cimm_listings
        + eureka_immo_listings
        + europe_sud_listings
        + human_listings
        + iad_listings
        + immo_chez_toit_listings
        + jammes_listings
        + mm_immo_listings
        + nestenn_listings
        + privee_listings
        + richardson_listings
        + safti_listings
        + selection_listings
        + sextant_listings
        + time_stone_listings
    )

    # The combined listings have a huge range of property categories, the code below reduces the total categories down to six. House, apartment, multi-lodging buildings, commercial property, empty land, and "other". Any listings that don't fit into the first five are reclassified as "other", and the original type is saved to "types_original" so it can be examined and classified later.

    uncategorized_types = []

    def key_from_value(agent_name_full, agent_dict=agent_dict):
        for agent_name_short, value in agent_dict.items():
            if value == agent_name_full:
                return agent_name_short
        return None

    def create_ref(agent_name_full, ref):
        agent_name_short = key_from_value(agent_name_full)
        if agent_name_short and ref:
            return f"{agent_name_short}-{ref}"
        return None

    for listing in all_listings:
        listing["id"] = create_ref(listing["agent"], listing["ref"])
        try:
            listing["types"] = unidecode(listing["types"].capitalize())
        except:
            listing["types"] = "Other"
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

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Total time elapsed: {time_taken:.2f}s")


if __name__ == "__main__":
    main()


# TODO Remove class use

# Sextant Failed URLs:
# ['https://www.sextantfrance.fr/fr/annonce/vente-villa-quillan-p-r7-75011147118.html',
#  'https://www.sextantfrance.fr/fr/annonce/vente-maison-de-hameau-puivert-p-r7-75011147116.html',
#  'https://www.sextantfrance.fr/fr/annonce/vente-maison-bessede-de-sault-p-r7-75011147016.html',
#  'https://www.sextantfrance.fr/fr/annonce/vente-maison-quillan-p-r7-75011147115.html',
#  'https://www.sextantfrance.fr/fr/annonce/vente-maison-de-village-puilaurens-p-r7-75011147017.html',
#  'https://www.sextantfrance.fr/fr/annonce/vente-maison-de-caractere-saint-louis-et-parahou-p-r7-75011147117.html']

# Safti Failed URLs:
# ['https://www.safti.fr/votre-conseiller-safti/sylvie-jubault']


#! Nestenn sold links appearing in search results: https://immobilier-lavelanet.nestenn.com/maison-2012-vue-lac-de-montbel-ref-37611829

# Maybe add: https://www.stephaneplazaimmobilier.com/
