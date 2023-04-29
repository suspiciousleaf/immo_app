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

def sextant_get_listings(host_photos=False):

    t0 = time.time()
    URL = "https://arnaud-masip.sextantfrance.fr/ajax/ListeBien.php?numnego=75011397&page=1&TypeModeListeForm=pict&ope=1&lieu-alentour=0&langue=fr&MapWidth=100&MapHeight=0&DataConfig=JsConfig.GGMap.Liste&Pagination=0"
    page = requests.get(URL)

    sextant_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = sextant_soup.find(string=True)
    num_props = int(num_props_div.split("|")[0])
    print("\nSextant number of listings:", num_props)
    pages = math.ceil(num_props / 12)
    print("Pages:", pages)

    results_pages = [f"https://arnaud-masip.sextantfrance.fr/ajax/ListeBien.php?numnego=75011397&page={i}&TypeModeListeForm=pict&ope=1&lieu-alentour=0&langue=fr&MapWidth=100&MapHeight=0&DataConfig=JsConfig.GGMap.Liste&Pagination=0" for i in range(1, pages + 1)]
    resp = get_data(results_pages)
    links = []
    for item in resp:
        links  += sextant_get_links(item["response"])

    print("Number of unique listing URLs found:", len(links))

    listings = [listing for listing in listings_json if listing["agent"] == "Sextant"]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Sextant":
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
                shutil.rmtree(f'{cwd}/static/images/sextant/{listing_ref}', ignore_errors=True) 
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    with concurrent.futures.ThreadPoolExecutor() as executor:   
        response_objects = executor.map(requests.get, (link for link in links_to_scrape))   # multi-threaded scraping
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
    print(f"Time elapsed for Sextant: {time_taken:.2f}s")

    return listings

def sextant_get_links(page):

    sextant_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in sextant_soup.find_all('a'):
            links_raw.add(link.get('href'))
    links_raw.discard(None)
    links = [link for link in links_raw if "https://www.sextantfrance.fr/fr/annonce/" in link]        
    # pprint(links)
    return links

def get_listing_details(page, url, host_photos):
    
    # try:
        agent = "Sextant"
        soup = BeautifulSoup(page.content, "html.parser")
        link_url = url

        #print("\n\nNext property\n")

        # Get type

        # This dictionary allows access to a script tag that hosts much of the important data. The previous method of scraping these details as used on other agents that use the same template (Jammes, Time & Stone, and other - Adapt Immo) are being left in in case this method proves unreliable. The script tag is just identified as the last script tag in find_all, so might be unreliable when used on all listings. This way each piece of information can be commented in.out if errors are found in listing data.

        key_dict = {
            "type_key": 2,
            "town_key": 4,
            "postcode_key": 5,
            "price_key": 9,
            "rooms_key": 11,
            "bedrooms_key": 12,
            "ref_key": 14
        }

        prop_type_div = soup.find_all("script")[-1].get_text()
        prop_type_div = prop_type_div[prop_type_div.find("'dimension"):prop_type_div.find("});")-7]

        details_dict = {}
        for item in prop_type_div.split(','):
            key, value = item.split(':')
            details_dict[int(key.replace("'", "").replace("dimension", "").strip())] = value.strip().strip("'")
        # pprint(details_dict)

        types = details_dict[key_dict["type_key"]].capitalize()
        ref = details_dict[key_dict["ref_key"]]
        price = int(details_dict[key_dict["price_key"]].replace(" ", ""))
        town = unidecode(details_dict[key_dict["town_key"]]).capitalize().replace("-", " ")
        postcode = details_dict[key_dict["postcode_key"]]
        
        try:
            rooms = int(details_dict[key_dict["rooms_key"]])
        except:
            rooms = None
        try:
            bedrooms = int(details_dict[key_dict["bedrooms_key"]])
        except:
            bedrooms = None
        
        # print(rooms)
        # print(bedrooms)

        # print("Type:", types)

        # Get location
        # location_div = soup.find("h2", class_="detail-bien-ville").get_text()
        # town = unidecode(location_div.split("(")[0]).strip().capitalize().replace("-", " ")
        # postcode = location_div.split("(")[1].replace("(", "").replace(")", "").strip()

        # print("Town:", town)
        # print("Postcode:", postcode)

        # Get price

        # price_div = soup.find('div', class_="detail-bien-prix").get_text()
        # price = int("".join([x for x in price_div if x.isdigit()]))
      
        # print("Price:", price, "€")

        # Get ref

        # Page returns two identical spans with itemprop="productID", one with a hidden ref and one with the 4 digit visible ref. No way to differentiate between the two. The second one has the desired  ref, so I turned it into a list, pulled the second item on the list (with the correct ref), then list comprehension to extract the digits, and join them into a string to get the correct ref.

        # prop_ref_div = soup.find_all('span', itemprop="productID")
        # prop_ref = list(prop_ref_div)
        # ref = "".join([char for char in str(prop_ref[1]) if char.isnumeric()])

        # print("ref:", ref)

        # Get property details
        # This returns a whole chunk of text for the property specs that gets separated to find the number of bedrooms, rooms, house size and land size. 

        details_div = list(soup.find('div', class_="detail-bien-specs"))
        details = str(details_div[1])
        details = details.split("\n")

        #Chambres

        # bedrooms = "".join([cham for cham in details if "chambre(s)" in cham]).split()
        # bedrooms = bedrooms[bedrooms.index("chambre(s)")-1]
        # if bedrooms.isnumeric():
        #     bedrooms = int(bedrooms)
        # else:
        #     bedrooms = None
        # print("Bedrooms:", bedrooms)

        # Rooms

        # rooms = "".join([rooms for rooms in details if "pièce(s)" in rooms]).split()
        # rooms = rooms[rooms.index("pièce(s)")-1]
        # if rooms.isnumeric():
        #     rooms = int(rooms)
        # else:
        #     rooms = None
        # print("Rooms:", rooms)

        # Plot size
        # Property and plot sizes are not available from the script tag dictionary method above, so are scraped as usual.

        plot = "".join([plot for plot in details if "terrain" in plot]).split()
        if plot[-2].isnumeric():
            plot = int(plot[-2])
        else:
            plot = None
        # print("Plot:", plot, "m²")

        #Property size

        size = "".join([size for size in details if "surface" in size]).split()
        if size[-2].isnumeric():
            size = int(size[-2])
        else:
            size = None
        # print("Size:", size, "m²")

        # Description

        description = soup.find("span", itemprop="description").get_text()
        # pprint(description)

        # Photos
        # Finds the links to full res photos for each listing, removes the "amp;" so the links work, and returns them as a list

        photos_div = []
        for link in soup.find_all('img', class_="photo-big"):
            photos_div.append(link)
        photos_div = [str(link) for link in photos_div]
        photos = [link[link.find("data-src=")+10:] for link in photos_div]
        photos = [link.replace("amp;", "") for link in photos]
        photos = [link.replace('"/>', "") for link in photos]
        # pprint(photos)

        if host_photos:

            agent_abbr = [i for i in agent_dict if agent_dict[i]==agent][0]

            make_photos_dir(ref, cwd, agent_abbr)

            photos_hosted = []
            photos_failed = []
            i = 0
            failed = 0

            resp = get_data(photos)
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
    
    # except:
    #     return url
cwd = os.getcwd()

get_listing_details(requests.get("https://www.sextantfrance.fr/fr/annonce/vente-maison-en-pierre-montfort-sur-boulzane-p-r7-75011142962.html"), "https://www.sextantfrance.fr/fr/annonce/vente-maison-en-pierre-montfort-sur-boulzane-p-r7-75011142962.html", False)


# links = []
# for i in range(1, 8):
#     links += sextant_get_links(requests.get(f"https://arnaud-masip.sextantfrance.fr/ajax/ListeBien.php?numnego=75011397&page={i}&TypeModeListeForm=pict&ope=1&lieu-alentour=0&langue=fr&MapWidth=100&MapHeight=0&DataConfig=JsConfig.GGMap.Liste&Pagination=1"))
# print(len(links))

# sextant_get_links(requests.get(f"https://arnaud-masip.sextantfrance.fr/ajax/ListeBien.php?numnego=75011397&page=9&TypeModeListeForm=pict&ope=1&lieu-alentour=0&langue=fr&MapWidth=100&MapHeight=0&DataConfig=JsConfig.GGMap.Liste&Pagination=1"))

# sextant_get_listings(False)

# sextant_listings = sextant_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(sextant_listings, outfile, ensure_ascii=False)

# Time elapsed for Sextant: 17.46s 76 listings without photos. Minimal difference between multi-threading and async
