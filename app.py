# Running this program will run all of the scrapers, update the database with new and removed listings, download and process any requested images, and sync the remote image directory with the local one.

# from gevent import monkey

# monkey.patch_all(thread=False, select=False)
import grequests
import json
import time

from pprint import pprint

# This library is used to remove accents from letters (used frequently in French), as some listings use accents correctly and some don't.
from unidecode import unidecode

t0 = time.perf_counter()

from utilities.db_utilities import (
    get_current_listing_urls,
    select_sold_urls,
    add_listings,
    delete_listings_by_url_list,
    add_sold_urls_to_database,
    open_SSH_tunnel,
    close_SSH_tunnel,
)

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
from scrapers.scraper_steph import steph_get_listings
from scrapers.scraper_time_stone import time_stone_get_listings

# Import from json_search must be below scraper imports due to grequests recursion error if imported before requests
from utilities.image_sold_checker import sold_image_check
from utilities.utility_holder import property_types
from utilities.async_image_downloader import sync_local_remote_image_directories


try:
    try:
        with open("times_run_since_last_image_scan_counter.json", "r") as infile:
            times_run_since_last_image_scan = json.load(infile)
        running_local = True
    except:
        running_local = False
        with open(
            "/home/suspiciousleaf/immo_app/times_run_since_last_image_scan_counter.json",
            "r",
        ) as infile:
            times_run_since_last_image_scan = json.load(infile)
except:
    times_run_since_last_image_scan = {"counter": 5}

try:
    with open("static/data/agent_mapping.json", "r", encoding="utf8") as infile:
        agent_dict = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/static/data/agent_mapping.json",
        "r",
        encoding="utf8",
    ) as infile:
        agent_dict = json.load(infile)

# The code below will run the imported scraper for each agent, host_photos will determine if the photos for each listing are downloaded, resized, and compressed for local hosting. Try/except is used to prevent an error with a single scraper causing the whole program to fail to run. Faults are reported to the failed_scrapes list, and finally to the console.


def main():
    if running_local:
        ssh = open_SSH_tunnel()

    old_listing_urls = get_current_listing_urls()
    old_listing_urls_dict = {agent: {} for agent in agent_dict.values()}

    for result in old_listing_urls:
        old_listing_urls_dict[result["agent"]][result["link_url"]] = result["ref"]

    sold_urls_set = select_sold_urls()

    failed_scrapes = {}

    try:
        # Must be True as host website blocks leeching for many photos
        ami09_listings = ami09_get_listings(
            old_listing_urls_dict["Ami Immobilier"], host_photos=True
        )
    except Exception as e:
        ami09_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Ami Immobilier"] = e

    try:
        api_listings = api_get_listings(
            old_listing_urls_dict["A.P.I."], host_photos=False
        )
    except Exception as e:
        api_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["A.P.I."] = e

    try:
        arieg_listings = arieg_get_listings(old_listing_urls_dict["Arieg'Immo"])
    except Exception as e:
        arieg_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Arieg'Immo"] = e

    try:
        arthur_immo_listings = arthur_immo_get_listings(
            old_listing_urls_dict["Arthur Immo"], sold_urls_set, host_photos=False
        )
    except Exception as e:
        arthur_immo_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Arthur Immo"] = e

    try:
        aude_immo_listings = aude_immo_get_listings(
            old_listing_urls_dict["Aude Immobilier"], host_photos=False
        )
    except Exception as e:
        aude_immo_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Aude Immobilier"] = e

    try:
        bac_listings = bac_get_listings(old_listing_urls_dict["BAC Immobilier"])
    except Exception as e:
        bac_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["BAC Immobilier"] = e

    try:
        # host photos option not needed
        beaux_listings = beaux_get_listings(old_listing_urls_dict["Beaux Villages"])
    except Exception as e:
        beaux_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Beaux Villages"] = e

    try:
        c21_listings = c21_get_listings(
            old_listing_urls_dict["Century 21"], host_photos=False
        )
    except Exception as e:
        c21_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Century 21"] = e

    try:
        # host photos not needed due to public API use for Cimm
        cimm_listings = cimm_get_listings(
            old_listing_urls_dict["Cimm Immobilier"], sold_urls_set
        )
    except Exception as e:
        cimm_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Cimm Immobilier"] = e

    try:
        eureka_immo_listings = eureka_immo_get_listings(
            old_listing_urls_dict["Eureka Immobilier"]
        )
    except Exception as e:
        eureka_immo_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Eureka Immobilier"] = e

    try:
        europe_sud_listings = europe_sud_get_listings(
            old_listing_urls_dict["Europe Sud Immobilier"], host_photos=False
        )
    except Exception as e:
        europe_sud_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Europe Sud Immobilier"] = e

    try:
        human_listings = human_get_listings(old_listing_urls_dict["Human Immobilier"])
    except Exception as e:
        human_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Human Immobilier"] = e

    try:
        iad_listings = iad_immo_get_listings(old_listing_urls_dict["IAD Immobilier"])
    except Exception as e:
        iad_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["IAD Immobilier"] = e

    try:
        immo_chez_toit_listings = immo_chez_toit_get_listings(
            old_listing_urls_dict["L'Immo Chez Toit"], host_photos=False
        )
    except Exception as e:
        immo_chez_toit_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["L'Immo Chez Toit"] = e

    try:
        jammes_listings = jammes_get_listings(
            old_listing_urls_dict["Cabinet Jammes"], sold_urls_set, host_photos=False
        )
    except Exception as e:
        jammes_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Cabinet Jammes"] = e

    try:
        mm_immo_listings = mm_immo_get_listings(
            old_listing_urls_dict["M&M Immobilier"], sold_urls_set, host_photos=False
        )
    except Exception as e:
        mm_immo_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["M&M Immobilier"] = e

    try:
        nestenn_listings = nestenn_immo_get_listings(
            old_listing_urls_dict["Nestenn"], host_photos=False
        )
    except Exception as e:
        nestenn_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Nestenn"] = e

    try:
        privee_listings = privee_get_listings(
            old_listing_urls_dict["Propriétés Privées"]
        )
    except Exception as e:
        privee_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Propriétés Privées"] = e

    try:
        # Must be True as host website uses HTTP instead of HTTPS, can't embed images
        richardson_listings = richardson_get_listings(
            old_listing_urls_dict["Richardson Immobilier"], host_photos=True
        )
    except Exception as e:
        richardson_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Richardson Immobilier"] = e

    try:
        # host photos option not needed
        safti_listings = safti_get_listings(
            old_listing_urls_dict["Safti"], sold_urls_set
        )
    except Exception as e:
        safti_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Safti"] = e

    try:
        selection_listings = selection_get_listings(
            old_listing_urls_dict["Selection Habitat"], host_photos=False
        )
    except Exception as e:
        selection_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Selection Habitat"] = e

    try:
        sextant_listings = sextant_get_listings(
            old_listing_urls_dict["Sextant"], sold_urls_set
        )
    except Exception as e:
        sextant_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Sextant"] = e

    try:
        steph_listings = steph_get_listings(old_listing_urls_dict["Stéphane Plaza"])
    except Exception as e:
        steph_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Stéphane Plaza"] = e

    try:
        time_stone_listings = time_stone_get_listings(
            old_listing_urls_dict["Time and Stone Immobilier"],
            sold_urls_set,
            host_photos=False,
        )
    except Exception as e:
        time_stone_listings = {"listings": [], "urls_to_remove": []}
        failed_scrapes["Time and Stone Immobilier"] = e

    # If any of the whole scrapers fail to run, the previously scraped links will be passed through, and the scraper name and exception will be passed into a dictionary. If anything is in the dictionary after they have all run, the below message will be printed.
    if failed_scrapes:
        print(f"\n\nThe following agent(s) failed to scrape entirely:\n")
        pprint(failed_scrapes)

    listing_agents = [
        ami09_listings,
        api_listings,
        arieg_listings,
        arthur_immo_listings,
        aude_immo_listings,
        bac_listings,
        beaux_listings,
        c21_listings,
        cimm_listings,
        eureka_immo_listings,
        europe_sud_listings,
        human_listings,
        iad_listings,
        immo_chez_toit_listings,
        jammes_listings,
        mm_immo_listings,
        nestenn_listings,
        privee_listings,
        richardson_listings,
        safti_listings,
        selection_listings,
        sextant_listings,
        steph_listings,
        time_stone_listings,
    ]

    all_listings = []
    listings_to_remove = []

    for agent in listing_agents:
        all_listings.extend(agent["listings"])
        listings_to_remove.extend(agent["urls_to_remove"])

    # The combined listings have a huge range of property categories, the code below reduces the total categories down to six. House, apartment, multi-lodging buildings, commercial property, empty land, and "other". Any listings that don't fit into the first five are reclassified as "other", and the original type is saved to "types_original" so it can be examined and classified later.

    uncategorized_types = []

    for listing in all_listings:
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

    # Verify if new listings should be added to the database. Can be used to skip if suspicious behaviour has been noticed.
    add_listings_response = None
    while add_listings_response != "y" and add_listings_response != "n":
        add_verify = None
        add_listings_response = input(
            f"\nAdd {len(all_listings)} new listings to database? Y/N: "
        ).lower()
        if add_listings_response == "y":
            add_listings(all_listings)
        elif add_listings_response == "n":
            print("Do not add new listings to the database.")
            while add_verify != "y" and add_verify != "n":
                add_verify = input("Confirm? Y/N: ")
                if add_verify == "n":
                    add_listings_response = None
                elif add_verify == "y":
                    pass

    # This counts up each time the scraper is run, and will run the function that scans main images for "Sold" etc text to remove those listings once every five times the scraper runs

    if times_run_since_last_image_scan["counter"] >= 5:
        try:
            print("\nImage scan function running, this will take approx 90 seconds")
            listing_to_remove_sold_photos = sold_image_check(listings_to_remove)
            if listing_to_remove_sold_photos:
                listings_to_remove.extend(listing_to_remove_sold_photos)
                add_sold_urls_to_database(listing_to_remove_sold_photos)
            times_run_since_last_image_scan["counter"] = 0
            print(
                f"Number of listings removed by image scan: {len(listing_to_remove_sold_photos)}"
            )
        except Exception as e:
            print(f"Image filter failed: {e}")
    else:
        times_run_since_last_image_scan["counter"] += 1

    # Verify whether listings detected as no longer online should be removed from the database.
    if listings_to_remove:
        remove_listings_response = None
        while remove_listings_response != "y" and remove_listings_response != "n":
            delete_verify = None
            remove_listings_response = input(
                f"\nDelete {len(listings_to_remove)} old listings from database? Y/N: "
            ).lower()
            if remove_listings_response == "y":
                delete_listings_by_url_list(listings_to_remove)
            elif remove_listings_response == "n":
                print("Do not delete old listings from the database.")
                while delete_verify != "y" and delete_verify != "n":
                    delete_verify = input("Confirm? Y/N: ")
                    if delete_verify == "n":
                        remove_listings_response = None
                    elif delete_verify == "y":
                        pass

    if running_local:
        close_SSH_tunnel(ssh)
        if add_listings_response == "y" or remove_listings_response == "y":
            sync_local_remote_image_directories()

    # This saves the updated counter for the image scan
    with open("times_run_since_last_image_scan_counter.json", "w") as outfile:
        json.dump(times_run_since_last_image_scan, outfile)

    print("\n\nTotal listings added: ", len(all_listings))
    print("\nTotal listings removed: ", len(listings_to_remove))
    print("\nCOMPLETE")

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Total time elapsed: {time_taken:.2f}s")


if __name__ == "__main__":
    main()


#! Nestenn sold links appearing in search results: https://immobilier-lavelanet.nestenn.com/maison-2012-vue-lac-de-montbel-ref-37611829

# Maybe add: https://www.hdc-immo.com/

# TODO BAC Immo is scraping some property sizes too large, missing decimal places

#! Test Beaux Villages scraper for size and other specs, re scrape everything

#! Move image scan to after database has been updated, so it doesn't try to analyze listings that have been removed. Or update list with urls to remove etc.

# TODO Create functions to make indexes in db_utilities

# 16/11/2023 Number of listings in sold_urls: 324

# TODO Some agents host a new photo when it is sold, so the url changes. If image scanner doesn't find the image, run the scraper again on the url to get the primary image, and then scan that. Safti, Jammes, M&M, Arthur
