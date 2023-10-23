# This scraper works a bit differently to the others. The company has many individual agents with their own listings pages. I have selected 16 that cover the area of interest. The main listing page for each agent has json data for each property inside the main listing page. So the scraper scrapes the data from each of the 16 agent pages, and extracts all property data from thos 16 pages instead of scraping the url for each listing. The exact url for each listing is generated from the property details, as the url isn't present on the agent page data scraped.
# This means it's quite fast to get all data, approx 7 seconds for 200 listings, but it means that it's necessary to do the full scrape each time, rather than just the new properties required (since this is done via the url of each listing, and the url isn't known until the property has already been scraped).

import os
import time
import json
import concurrent.futures

# This must be imported as it is imported with get_gps, and if requests is imported before grequests it will cause recursion error
# import grequests
# import requests
from pprint import pprint
from bs4 import BeautifulSoup

# import shutil
from unidecode import unidecode

from models import Listing
from utilities.utility_holder import get_data

try:
    try:
        with open("postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/postcodes_gps_dict.json",
            "r",
            encoding="utf8",
        ) as infile:
            gps_dict = json.load(infile)
except:
    print("gps_dict not found")
    gps_dict = []


def safti_get_listings(old_listing_urls_dict, sold_url_set):
    t0 = time.perf_counter()

    unwanted_listings = sold_url_set.union(set(old_listing_urls_dict.keys()))

    print("\nSafti scraper beginning...")

    links_to_scrape = [
        "https://www.safti.fr/votre-conseiller-safti/denis-rousset",
        "https://www.safti.fr/votre-conseiller-safti/jean-cannet",
        "https://www.safti.fr/votre-conseiller-safti/jean-philippe-magrino",
        "https://www.safti.fr/votre-conseiller-safti/karine-mas",
        "https://www.safti.fr/votre-conseiller-safti/sebastien-perennes",
        "https://www.safti.fr/votre-conseiller-safti/sylvie-jubault",
        "https://www.safti.fr/votre-conseiller-safti/margot-garcia",
        "https://www.safti.fr/votre-conseiller-safti/aurelie-vega",
        "https://www.safti.fr/votre-conseiller-safti/melanie-ferreira",
        "https://www.safti.fr/votre-conseiller-safti/daniela-big",
        "https://www.safti.fr/votre-conseiller-safti/nicolas-goudenege",
        "https://www.safti.fr/votre-conseiller-safti/sabine-ladouce",
        "https://www.safti.fr/votre-conseiller-safti/pascal-campos",
        "https://www.safti.fr/votre-conseiller-safti/nathalie-francois",
        "https://www.safti.fr/votre-conseiller-safti/dany-pabou",
    ]

    new_listings = []
    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    resp_to_scrape = get_data(links_to_scrape)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            get_listing_details,
            (item["response"] for item in resp_to_scrape),
            links_to_scrape,
        )
        for result in results:
            if isinstance(result, str):
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
    new_listings_urls = [listing["link_url"] for listing in new_listings]

    listings = [
        listing
        for listing in new_listings
        if listing["link_url"] not in unwanted_listings
    ]

    # If more than a single page fails to scrape, no listings will be removed from the database. On rare occasions most or all can fail one one run, and then succeed the next day without any change in the code.
    if counter_fail > 1:
        links_dead = []
    else:
        links_dead = [
            link
            for link in old_listing_urls_dict.keys()
            if link not in new_listings_urls
        ]

    print("New listings to add:", len(listings))
    print("Old listings to remove:", len(links_dead))

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Time elapsed for Safti: {time_taken:.2f}s")

    return {"listings": listings, "urls_to_remove": links_dead}


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
                town = (
                    unidecode(item["city"])
                    .casefold()
                    .replace("l' ", "l'")
                    .replace("-", " ")
                    .capitalize()
                )
                url_town = item["city"].casefold().replace(" ", "-")
                link_url = f"https://www.safti.fr/annonces/achat/{types}/{url_town}-{postcode}/{ref}"
                size = item["propertySurface"]
                plot = item["areaSurface"]
                rooms = item["roomNumber"]
                price = item["price"]
                bedrooms = item["bedroomNumber"]
                description_raw = (
                    item["description"].replace("<br/>", "\n").replace("<br />", "\n")
                ).splitlines()
                description = [
                    string.replace("\n", "").strip()
                    for string in description_raw
                    if string.replace("\n", "").strip()
                ]
                photos = [list_item["urlPhotoLarge"] for list_item in item["photos"]]
                photos_hosted = photos
                gps = [item["lat"], item["lng"]]

                if "ommerc" in types:
                    types = "Commerce"

                # print("property scraped")
                listing = Listing(
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
                )

                listings.append(listing.__dict__)

            else:
                pass

        return listings
    except Exception as e:
        return f"{url}: {str(e)}"


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

# test_url = "https://www.safti.fr/votre-conseiller-safti/sylvie-jubault"

# get_listing_details(requests.get(test_url), test_url)

# safti_listings = safti_get_listings()

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(safti_listings, outfile, ensure_ascii=False)
