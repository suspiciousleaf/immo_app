import os
import time
import re
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

def jammes_get_listings(host_photos=False):

    t0 = time.time()
    URL = "https://www.cabinet-jammes.com/fr/liste.htm?page=1"
    page = requests.get(URL)

    jammes_soup = BeautifulSoup(page.content, "html.parser")

    num_props_div = jammes_soup.find('span', class_="NbBien")
    num_props = int(num_props_div.find(string=True))
    print("\nJammes Immo number of listings:", num_props)
    pages = math.ceil(num_props / 12)
    print("Pages:", pages)

    results_pages = ["https://www.cabinet-jammes.com/fr/liste.htm?page=" + str(i) for i in range(1, pages + 1)]
    resp = get_data(results_pages)
    links = []
    for item in resp:
        links  += jammes_get_links(item["response"])

    print("Number of unique listing URLs found:", len(links))

    listings = [listing for listing in listings_json if listing["agent"] == "Cabinet Jammes"]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Cabinet Jammes":
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
                shutil.rmtree(f'{cwd}/static/images/jammes/{listing_ref}', ignore_errors=True) 
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    with concurrent.futures.ThreadPoolExecutor() as executor:   
        response_objects = executor.map(requests.get, (link for link in links_to_scrape))   # Threaded scraping
        results = executor.map(get_listing_details, (item for item in response_objects), links_to_scrape, [host_photos for x in links_to_scrape]) # Threaded parsing w/photo scraping
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
    print(f"Time elapsed for Cabinet Jammes: {time_taken:.2f}s")

    return listings

def jammes_get_links(page):

    jammes_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in jammes_soup.find_all('a'):
            links_raw.add(link.get('href'))
    links_raw.discard(None)
    links = [link for link in links_raw if "https://www.cabinet-jammes.com/fr/detail.htm" in link]        

    return links

def get_listing_details(page, url, host_photos):
    
    try:
        agent = "Cabinet Jammes"
        soup = BeautifulSoup(page.content, "html.parser")
        link_url = url

        #print("\n\nNext property\n")

        # Get type
        prop_type_div = soup.find('h2', class_="detail-bien-type")
        prop_type = prop_type_div.find(string=True)
        #print("Type:", prop_type)
        types = prop_type

        # Get location
        location_div = soup.find('h2', class_="detail-bien-ville")
        location_raw = location_div.find(string=True).strip().split()
        location_postcode = location_raw.pop(-1).strip("(").strip(")")
        location_town = " ".join(location_raw)
        town = unidecode(location_town.capitalize().replace("-", " "))
        postcode = location_postcode

        #print("Town:", location_town)
        #print("Postcode:", location_postcode)

        # Get price
        price_div = soup.find('div', class_="detail-bien-prix")
        price = price_div.find(string=re.compile("€"))
        price = int(price.replace(" ", "").strip("€"))
        #print("Price:", price, "€")

        # Get ref

        # Page returns two identical spans with itemprop="productID", one with a hidden ref and one with the 4 digit visible ref. No way to differentiate between the two. The second one has the desired  ref, so I turned it into a list, pulled the second item on the list (with the correct ref), then list comprehension to extract the digits, and join them into a string to get the correct ref.

        prop_ref_div = soup.find_all('span', itemprop="productID")
        prop_ref = list(prop_ref_div)
        prop_ref = "".join([char for char in str(prop_ref[1]) if char.isnumeric()])
        ref = prop_ref

        #print("ref:", prop_ref)

        # Get property details
        # This returns a whole chunk of text for the property specs that gets separated to find the number of bedrooms, rooms, house size and land size. It's done in a janky way that Amy will hate

        details_div = list(soup.find('div', class_="detail-bien-specs"))
        details = str(details_div[1])
        details = details.split("\n")

        #Chambres

        bedrooms = "".join([cham for cham in details if "chambre(s)" in cham]).split()
        bedrooms = bedrooms[bedrooms.index("chambre(s)")-1]
        # if not bedrooms.isnumeric():
        #     bedrooms = "Unknown"
        if bedrooms.isnumeric():
            bedrooms = int(bedrooms)
        else:
            bedrooms = None
        #print("Bedrooms:", bedrooms)

        # Rooms

        rooms = "".join([rooms for rooms in details if "pièce(s)" in rooms]).split()
        rooms = rooms[rooms.index("pièce(s)")-1]
        # if not rooms.isnumeric():
        #     rooms = "Unknown"
        if rooms.isnumeric():
            rooms = int(rooms)
        else:
            rooms = None
        #print("Rooms:", rooms)

        # Plot size

        plot = "".join([plot for plot in details if "terrain" in plot]).split()
        if plot[-2].isnumeric():
            plot = int(plot[-2])
        else:
            plot = None
        #print("Plot:", plot, "m²")

        #Property size

        size = "".join([size for size in details if "surface" in size]).split()
        if size[-2].isnumeric():
            size = int(size[-2])
        else:
            size = None

        # Description

        description = soup.find("span", itemprop="description").get_text()
        description = "".join(description.splitlines())
        #pprint(description)

        # Photos
        # Finds the links to full res photos for each listing, removes the "amp;" so the links work, and returns them as a list

        photos_div = []
        for link in soup.find_all('img', class_="photo-big"):
            photos_div.append(link)
        photos_div = [str(link) for link in photos_div]
        photos = [link[link.find("data-src=")+10:] for link in photos_div]
        photos = [link.replace("amp;", "") for link in photos]
        photos = [link.replace('"/>', "") for link in photos]

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

# jammes_listings = jammes_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(jammes_listings, outfile, ensure_ascii=False)


# Time elapsed for Cabinet Jammes: 14.5 Double threading, no photos
# Time elapsed for Cabinet Jammes: 172.85744714736938 Single threading with photos
# Time elapsed for Cabinet Jammes: 89.54897403717041 Async with photos
# Time elapsed for Cabinet Jammes: 98.5943374633789 Double threading with photos