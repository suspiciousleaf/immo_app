import os
import time
import math
import json
import concurrent.futures
import re

from pprint import pprint
import grequests    # This must be imported as it is imported with get_gps, and if requests is imported before grequests it will cause recursion error
import requests
from bs4 import BeautifulSoup
import shutil
from unidecode import unidecode

from async_image_downloader import make_photos_dir, dl_comp_photo
from location_fix import fix_location   # This is necessary for Richardson and Ami, as both have poor quality and inconsistent location data
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
    with open("postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
except:
    with open("/home/suspiciousleaf/immo_app/postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)

try:
    try:
        with open("postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
    except:
        with open("/home/suspiciousleaf/immo_app/postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
except:
    print("gps_dict not found")
    gps_dict = []

def ami09_get_listings(host_photos=False):

    t0 = time.time()

    URL = "https://www.ami09.com/immobilier-pays-de-sault/?product-page=1"
    page = requests.get(URL)

    ami09_soup = BeautifulSoup(page.content, "html.parser")

    num_props = int(ami09_soup.find('p', class_="woocommerce-result-count").get_text().split()[-2])
    print("\nAmi Immobilier number of listings:", num_props)
    pages = math.ceil(num_props / 12)
    print("Pages:", pages)

    all_search_pages = [f"https://www.ami09.com/immobilier-pays-de-sault/?product-page={i}" for i in range(1, pages + 1)]

    links = []
    resp = get_data(all_search_pages)
    for item in resp:
        links  += ami09_get_links(item["response"])

    print("Number of unique listing URLs found:", len(links))

    listings = [listing for listing in listings_json if listing["agent"] == "Ami Immobilier"]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Ami Immobilier":
            links_old.append(listing["link_url"])

    links_to_scrape = [link for link in links if link not in links_old]
    print("New listings to add:", len(links_to_scrape))
    # pprint(links_to_scrape)
    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))
    # pprint(links_dead)

    listing_photos_to_delete_local = []

    if links_dead:
        for listing in listings:
            if listing["link_url"] in links_dead:
                listing_photos_to_delete_local.append(listing["ref"])
                listings.remove(listing)

        for listing_ref in listing_photos_to_delete_local:
            try:
                shutil.rmtree(f'{cwd}/static/images/ami/{listing_ref}', ignore_errors=True)
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []
    resp_to_scrape = get_data(links_to_scrape)

    with concurrent.futures.ThreadPoolExecutor() as executor:    
        results = executor.map(get_listing_details, (item["response"] for item in resp_to_scrape), links_to_scrape, [host_photos for x in resp_to_scrape])
        for result in results:
            if type(result) == str:
                failed_scrape_links.append(result)
                counter_fail += 1
            else:
                listings.append(fix_location(result))
                counter_success += 1

    if links_to_scrape:
        print(f"Successfully scraped: {counter_success}/{len(links_to_scrape)}")

    if failed_scrape_links:
        print(f"Failed to scrape: {counter_fail}/{len(links_to_scrape)} \nFailed URLs:")
        pprint(failed_scrape_links)

    listings.sort(key=lambda x: x["price"])
        
    t1 = time.time()

    time_taken = t1-t0
    print(f"Time elapsed for Ami Immobilier: {time_taken:.2f}s")

    return listings

def ami09_get_links(page,):

    ami09_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in ami09_soup.find_all('a'):
            links_raw.add(link.get('href'))
    links_raw.discard(None)
    links = [link for link in links_raw if "https://www.ami09.com/produit" in link]        

    return links

def get_listing_details(page, url, host_photos):
    try:
        agent = "Ami Immobilier"
        soup = BeautifulSoup(page.content, "html.parser")
        link_url = url

        #print("\n\nNext property\n")

        #print(URL)
        # Get type
        types_div = soup.find('h1').get_text()
        types_div_cleaned = types_div.replace("-", ";").replace("–", ";").replace("—", ";")
        if types_div_cleaned.count(";") == 2:
            types = types_div_cleaned.split(";")[1].strip().capitalize()
        else:
            types = "Maison"
        if types[-1] == "s":
            types = types[:-1]
        # print("Type:", types)


        # Get location
        town = None
        top_table_div = soup.find_all("table", class_="main_tableau_acf")[0].contents
        for item in top_table_div:
            if "Lieu:" in item.get_text():
                town = unidecode(item.get_text().replace("Lieu:", "").capitalize())

        location_div = soup.find("h1").get_text().replace("—", "-").replace("–", "-")
        if location_div[-5:].isdigit():
            postcode = location_div[-5:]
            location_div = location_div[:-5]
        else:
            postcode = None
        
        # print("\n", location_div)
        # print("Postcode:", postcode)

        if not town:
            if location_div.count("-") > 0:
                try:
                    town = unidecode(location_div.split("-")[-1].strip().capitalize())
                except:
                    pass
            else:
                town = None

        # print("Town:", town)

        # Get ref
        ref_div = soup.find('table', class_="main_tableau_acf").get_text()
        ref = "".join([num for num in ref_div if num.isdigit()])
        # print("ref:", ref)

        if ref == "":
            ref_div_2 = link_url.split("/")[-2].split("-")[0]
            if ref_div_2.isnumeric():
                ref = ref_div_2
        # print("ref:", ref)

        # Get price
        price_div = soup.find('span', class_="woocommerce-Price-amount").get_text()
        price = int("".join([num for num in price_div if num.isdigit()]))
        # print("Price:", price, "€")

        # Get property details
        details_div = soup.find_all("table", class_="main_tableau_acf")[1].contents
        # print(details_div)
        bedrooms = None
        try:
            for item in details_div:
                if "chambres" in item.get_text():
                    bedrooms = int("".join([num for num in item.get_text() if num.isdigit()]))
        except:
            pass
        # print("Bedrooms:", bedrooms)
                
        # Rooms
        # pprint(details_div)
        rooms = None
        try:
            for item in details_div:
                if "pièces" in item.get_text():
                    rooms = int("".join([num for num in item.get_text() if num.isdigit()]))
        except:
            pass

        # print("Rooms:", rooms)

        # Description

        description_outer = soup.find("div", class_="et_pb_wc_description")
        description = description_outer.find("div", class_="et_pb_module_inner").p.get_text()
        
        # print(description)
        plot = None
        try:
            for item in details_div:
                if "Surface terrain" in item.get_text():
                    plot = int("".join([num for num in item.get_text() if num.isdigit() and num.isascii()]))
        except:
            pass

        # If plot hasn't been found in details_div, the regex below tries to capture it in the description
        if not plot:
            try:
                regex = r"terrain.*?(\d+)m²"

                match = re.search(regex, description, re.IGNORECASE)

                if match:
                    plot = int(match.group(1))
            except:
                pass

        # print("Plot:", plot, "m²")

        #Property size
        size = None
        try:
            for item in details_div:
                if "habitable" in item.get_text():
                    size = int("".join([num for num in item.get_text() if num.isdigit() and num.isascii()]))
        except:
            pass
        # print("Size:", size, "m²")


        # Photos
        photos = []
        photos_div = soup.find("figure", class_="woocommerce-product-gallery__wrapper")
        photos_div = photos_div.find_all("a")
        for element in photos_div:
            photos.append(element.get("href"))

        if host_photos:

            agent_abbr = [i for i in agent_dict if agent_dict[i]==agent][0]

            make_photos_dir(ref, cwd, agent_abbr)

            photos_hosted = []
            photos_failed = []
            i = 0
            failed = 0

            resp = get_data(photos, header=False)
            for item in resp:
                try:
                    photos_hosted.append(dl_comp_photo(item["response"], ref, i, cwd, agent_abbr))
                    i += 1
                except:
                    photos_failed.append(item["link"])
                    failed += 1
            
            if failed:
                print(f"{failed} photos failed to scrape")
                pprint(photos_failed)
        else:
            photos_hosted = photos

        gps = None
       
        listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, photos_hosted, gps)  

        return listing.__dict__
    except Exception as e:
        # print(e)
        return url
    
cwd = os.getcwd()

# get_listing_details(requests.get("https://www.ami09.com/produit/5316-terrains/"), "https://www.ami09.com/produit/5316-terrains/", False)

# get_listing_details(requests.get("https://www.ami09.com/produit/5744-maison-belcaire-11340/"), "https://www.ami09.com/produit/5744-maison-belcaire-11340/", False)

# ami09_get_listings()
#ami09_get_links(1)

# Time elapsed for Ami Immobilier: 24.16s async photo grab
# Time elapsed for Ami Immobilier: 145.64853525161743 multi-threading photo grab

# ami09_listings = ami09_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(ami09_listings, outfile, ensure_ascii=False)
