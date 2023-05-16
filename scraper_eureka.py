import os
import time
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
            gps_dict = json.load(infile)
    except:
        with open("/home/suspiciousleaf/immo_app/postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
except:
    print("gps_dict not found")
    gps_dict = []

try:
    with open("ville_list_clean.json", "r", encoding="utf8") as infile:
        town_list = json.load(infile)
except:
    with open("/home/suspiciousleaf/immo_app/ville_list_clean.json", "r", encoding="utf8") as infile:
        town_list = json.load(infile)

try:
    with open("postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
except:
    with open("/home/suspiciousleaf/immo_app/postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)

def eureka_immo_get_listings(host_photos=False):

    t0 = time.time()
    # Total number of listings isn't given on the page, but is around 90 listings. This wouldequate to 9 pages of listings. The code below will scrape 15 pages of listings at ocne rather than counting through pages until the listings stop. This takes appprox 1 second instead of 3 seconds. If the total listings scraped approaches 15 pages worth, a note will be printed to "pages" can be adjusted.


    pages = 15
    all_search_pages = [f"https://www.eureka-immo11.com/a-vendre/{i}" for i in range(1, pages+1)]

    links = []
    resp = get_data(all_search_pages)
    for item in resp:
        links  += eureka_immo_get_links(item["response"])

    print("\nEureka Immobilier number of listings:", len(links))

    if len(links) > (pages*10 - 20):
        print("Eureka Immo increase 'pages' variable")

    listings = [listing for listing in listings_json if listing["agent"] == "Eureka Immobilier"]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Eureka Immobilier":
            links_old.append(listing["link_url"])
    # print("Listings found from prevous scrape:", len(links_old))

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
                shutil.rmtree(f'{cwd}/static/images/eureka/{listing_ref}', ignore_errors=True) 
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []


    with concurrent.futures.ThreadPoolExecutor() as executor: 
        resp_to_scrape = get_data(links_to_scrape)  
        results = executor.map(get_listing_details, (item["response"] for item in resp_to_scrape), links_to_scrape, [host_photos for x in links_to_scrape])
        for result in results:
            if type(result) == str:
                failed_scrape_links.append(result)
                counter_fail += 1
            else:
                listings.append(result)
                counter_success += 1

    if links_to_scrape:
        print(f"Successfully scraped: {counter_success}/{len(links_to_scrape)}")

    if failed_scrape_links:
        print(f"Failed to scrape: {counter_fail}/{len(links_to_scrape)} \nFailed URLs:")
        pprint(failed_scrape_links)

    listings.sort(key=lambda x: x["price"])
        
    t1 = time.time()

    time_taken = t1-t0
    print(f"Time elapsed for Eureka Immobilier: {time_taken:.2f}s")

    return listings

def eureka_immo_get_links(page):
  
    eureka_immo_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in eureka_immo_soup.find_all('button', class_="btn-listing btn-primary"):
            links_raw.add("https://www.eureka-immo11.com" + link.get('onclick').replace("'", "").replace("location.href=", ""))

    links = list(links_raw)       

    return links

def get_listing_details(page, url, host_photos):
    try:
        agent = "Eureka Immobilier"
        link_url = url
        soup = BeautifulSoup(page.content, "html.parser")

        # Get type

        types = unidecode(soup.find("div", class_="bienTitle themTitle").get_text(strip=True).split(" ")[0].replace("\n", ""))
        # print("Type:", types)

        # Get price
        try:
            price = int(soup.find("span", itemprop="price").get_text().replace(" ", ""))
        except:
            price = 0
        # print("Price:", price, "€")

        # Get ref
        ref_div = soup.find("span", class_="ref", itemprop="productID").get_text()
        ref = "".join([num for num in ref_div if num.isnumeric()])
        # print("ref:", ref)

        # Get property details

        bedrooms = None
        rooms = None
        size = None
        plot = None
        details_div = soup.find('div', id="dataContent")
        details_list = details_div.find_all("p", class_="data")
        for item in details_list:
            item_parsed = item.get_text("|", strip=True).split("|")
            if "Nombre de chambre(s)" in item_parsed:
                bedrooms = int(item_parsed[1])
            elif "Nombre de pièces" in item_parsed:
                rooms = int(item_parsed[1])
            elif "Surface habitable (m²)" in item_parsed:
                size = int(float(item_parsed[1].replace("m²", "").replace(" ", "").replace(",", ".")))
            elif "surface terrain" in item_parsed:
                if "ha" in item_parsed[1].casefold():
                    plot = 10000 * int(float("".join([num for num in item_parsed[1] if num.isnumeric()])))
                else:    
                    plot = int(float(item_parsed[1].replace("m²", "").replace(" ", "").replace(",", ".")))
            elif "Code postal" in item_parsed:
                postcode = item_parsed[1]

        # print("Bedrooms:", bedrooms)
        # print("Rooms:", rooms)
        # print("Plot:", plot, "m²")
        # print("Size:", size, "m²")

        # Get location

        # Town information is stored inconsistently. This first checks the links at the top, if no luck then checks the h1 tag, and if still no luck will use the postcode (which is stored more consistently) to set the town as the top result for that postcode
        location_div = soup.find("ol", class_="breadcrumb").contents
        town = unidecode([item.get_text() for item in location_div if item != "\n"][1].replace("-", " "))
        if town.casefold() not in town_list:
            town_div = soup.find("div", class_="bienTitle themTitle").h1
            for item in town_div.strings:
                town_raw = item.splitlines()
                break
            town_div_list = [item.strip() for item in town_raw if item.strip()]
            town = unidecode(town_div_list[-1]).capitalize().replace("-", " ")
            if town.casefold() not in town_list:
                town = postcodes_dict[postcode][0]

        # print("Town:", town)
        # print("Postcode:", postcode)

        # Description
        description = soup.find("p", itemprop="description").get_text(strip=True).replace("\xa0\n", "")
        # print(description)

        # Photos
        # Finds the links to full res photos for each listing and returns them as a list
        photos = []
        photos_div = soup.find("ul", class_="imageGallery")
        photos_list = photos_div.find_all("li")
        for item in photos_list:
            photos.append("https:" + item.get("data-src"))

        photos_hosted = photos
        # pprint(photos)

        gps = None
        if type(town) == str:
            if (postcode + ";" + town.casefold()) in gps_dict:  # Check if town is in premade database of GPS locations, if not searches for GPS
                gps = gps_dict[postcode + ";" + town.casefold()]
            else:
                try:
                    gps = get_gps(town, postcode)
                except:
                    gps = None

        listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, photos_hosted, gps)
        return listing.__dict__
    except:
        return url

cwd = os.getcwd()


# pprint(get_listing_details("https://www.audeimmobilier.com/vente/11-aude/243-bouisse/maison-de-village-renovee-avec-jardin/1215-maison").__dict__)

# failed_urls = ['https://www.eureka-immo11.com/449-a-vendre-villa-de-plain-pied-jardin-garage-piscine-limoux.html',
#  'https://www.eureka-immo11.com/448-a-vendre-garage-centre-ville-limoux.html']
# for test_url in failed_urls:
# test_url = "https://www.eureka-immo11.com/353-terrain-eco-lieu-de-7-hectares-sur-les-hauteurs-de-limoux.html"
# get_listing_details(requests.get(test_url), test_url, False)

# eureka_immo_listings = eureka_immo_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf8") as outfile:
#     json.dump(eureka_immo_listings, outfile, ensure_ascii=False)

# Fix location scraping, search api.json "cabbage" for failed results. Get title h1 without the price inside the span tag

