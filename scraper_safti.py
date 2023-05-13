# This scraper works a bit differently to the others. The company has many individual agents with their own listings pages. I have selected 16 that cover the area of interest. The main listing page for each agent has json data for each property inside the main listing page. So the scraper scrapes the data from each of the 16 agent pages, and extracts all property data from thos 16 pages instead of scraping the url for each listing. The exact url for each listing is generated from the property details, as the url isn't present on the agent page data scraped. 
# This means it's quite fast to get all data, approx 7 seconds for 200 listings, but it means that it's necessary to do the full scrape each time, rather than just the new properties required (since this is done via the url of each listing, and the url isn't known until the property has already been scraped).

import os
import time
import math
import json
import concurrent.futures

from pprint import pprint
import grequests    # This must be imported as it is imported with get_gps, and if requests is imported before grequests it will cause recursion error
import requests
from bs4 import BeautifulSoup
import shutil
from unidecode import unidecode

from async_image_downloader import make_photos_dir, dl_comp_photo
from json_search import agent_dict
from models import Listing
from utilities import get_gps, get_data

try:
    try:
        with open("listings.json", "r", encoding="utf8") as infile:
            listings_json = json.load(infile)
    except:
        with open("/home/suspiciousleaf/immo_app/listings.json", "r", encoding="utf8") as infile:
            listings_json = json.load(infile)
except:
    listings_json = []

try:
    try:
        with open("postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict= json.load(infile)
    except:
        with open("/home/suspiciousleaf/immo_app/postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict= json.load(infile)
except:
    print("gps_dictnot found")
    gps_dict= []    

def safti_get_listings():

    t0 = time.time()

    print("\nSafti scraper beginning...")

    links_to_scrape = ["https://www.safti.fr/votre-conseiller-safti/denis-rousset", "https://www.safti.fr/votre-conseiller-safti/jean-cannet","https://www.safti.fr/votre-conseiller-safti/jean-philippe-magrino","https://www.safti.fr/votre-conseiller-safti/karine-mas","https://www.safti.fr/votre-conseiller-safti/sebastien-perennes","https://www.safti.fr/votre-conseiller-safti/sylvie-jubault","https://www.safti.fr/votre-conseiller-safti/margot-garcia","https://www.safti.fr/votre-conseiller-safti/aurelie-vega","https://www.safti.fr/votre-conseiller-safti/melanie-ferreira","https://www.safti.fr/votre-conseiller-safti/daniela-big","https://www.safti.fr/votre-conseiller-safti/nicolas-goudenege","https://www.safti.fr/votre-conseiller-safti/sabine-ladouce", "https://www.safti.fr/votre-conseiller-safti/pascal-campos","https://www.safti.fr/votre-conseiller-safti/nathalie-francois","https://www.safti.fr/votre-conseiller-safti/dany-pabou","https://www.safti.fr/votre-conseiller-safti/andrea-oustric"]

    new_listings = []
    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    resp_to_scrape = get_data(links_to_scrape)

    with concurrent.futures.ThreadPoolExecutor() as executor:    
        results = executor.map(get_listing_details, (item["response"] for item in resp_to_scrape), links_to_scrape)
        for result in results:
            if type(result) == str:
                failed_scrape_links.append(result)
                counter_fail += 1
            else:
                new_listings += result
                counter_success += 1
  
    if links_to_scrape:
        print(f"Agents successfully scraped: {counter_success}/{len(links_to_scrape)}")

    if failed_scrape_links:
        print(f"Failed to scrape: {counter_fail}/{len(links_to_scrape)} \nFailed URLs:")
        pprint(failed_scrape_links)

    new_listings = remove_duplicates(new_listings)

    print(f"Listings found: {len(new_listings)}")

    new_listings.sort(key=lambda x: x["price"])
        
    t1 = time.time()

    time_taken = t1-t0
    print(f"Time elapsed for Safti: {time_taken:.2f}s")

    return new_listings

def get_listing_details(page, url):

    try:
        safti_soup = BeautifulSoup(page.content, "html.parser")
        scraped_script = safti_soup.find("script", id="__NEXT_DATA__").contents[0]

        raw_json = json.loads(scraped_script)

        properties_json = raw_json["props"]["pageProps"]["properties"]
        listings = []
    
        for item in properties_json:
            if item["underCompromise"] == False and item["sold"] == False:
                agent = "Safti"
                ref = str(item["propertyReference"])
                types = item["propertyType"].capitalize()
                postcode = item["postCode"]
                town = unidecode(item["city"]).casefold().replace("l' ", "l'").replace("-", " ").capitalize()
                url_town = item["city"].casefold().replace(" ", "-")
                link_url = f"https://www.safti.fr/annonces/achat/{types}/{url_town}-{postcode}/{ref}"
                size = item["propertySurface"]
                plot = item["areaSurface"]
                rooms = item["roomNumber"]
                price = item["price"]
                bedrooms = item["bedroomNumber"]
                description = item["description"].replace("<br/>", "\n").replace("<br />", "\n")
                photos = [list_item["urlPhotoLarge"] for list_item in item["photos"]]
                photos_hosted = photos
                gps = [item["lat"], item["lng"]]

                if "ommerc" in types:
                    types = "Commerce"

                # print("property scraped")
            else:
                pass

            listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, photos_hosted, gps)

            listings.append(listing.__dict__)

        return listings
    except:
        return url

def remove_duplicates(listings):
    # Safti duplicates some results, this puts the urls into a set to remove duplicates, then returns a new list with a single listing for each url from the set.
    safti_urls = set()
    for listing in listings:
        safti_urls.add(listing["link_url"])

    new_listings = []
    for link in safti_urls:
        for listing in listings:
            if link in listing.values():
                new_listings.append(listing)
                break
    return new_listings


cwd = os.getcwd()

# safti_listings = safti_get_listings()

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(safti_listings, outfile, ensure_ascii=False)

