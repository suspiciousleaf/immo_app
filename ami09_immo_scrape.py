from pprint import pprint
import requests
from bs4 import BeautifulSoup
import math
from models import Listing
from geopy.geocoders import Nominatim
import json
import os
from json_search import agent_dict
import shutil
from image_downloader import make_photos_dir, dl_comp_photo
from location_fix import fix_location

try:
    with open("listings.json", "r") as infile:
        listings_json = json.load(infile)
except:
    listings_json = []

def get_gps(town):
    geolocator = Nominatim(user_agent="property-scraper")
    location = geolocator.geocode(town + " France")
    gps = [location.latitude, location.longitude]
    return gps

def ami09_get_links(i):
    URL = "https://www.ami09.com/immobilier-pays-de-sault/?product-page={}".format(i)
    page = requests.get(URL)

    ami09_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in ami09_soup.find_all('a'):
            links_raw.add(link.get('href'))
    links_raw.discard(None)
    links = [link for link in links_raw if "https://www.ami09.com/produit" in link]        
    #pprint(links)
    return links

def ami09_get_listings():

    URL = "https://www.ami09.com/immobilier-pays-de-sault/?product-page=1"
    page = requests.get(URL)

    ami09_soup = BeautifulSoup(page.content, "html.parser")

    num_props = int(ami09_soup.find('p', class_="woocommerce-result-count").get_text().split()[-2])
    print("\nAmi Immobilier number of listings:", num_props)
    pages = math.ceil(num_props / 12)
    print("Pages:", pages)

    links = []
    for i in range(1, pages + 1):
        links += ami09_get_links(i)
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
    for i in range(len(links_to_scrape)):
        try:
            new_listing = get_listing_details(links_to_scrape[i])
            listings.append(fix_location(new_listing.__dict__))
            counter_success += 1
        except:
            # print(f"Failed to scrape listing {links_to_scrape[i]}")
            failed_scrape_links.append(links_to_scrape[i])
            counter_fail += 1

    if links_to_scrape:
        print(f"Successfully scraped: {counter_success}/{len(links_to_scrape)}")

    if failed_scrape_links:
        print(f"Failed to scrape: {counter_fail}/{len(links_to_scrape)} \nFailed URLs:")
        pprint(failed_scrape_links)

    listings.sort(key=lambda x: x["price"])
        
    # for listing in listings:
    #     pprint(listing)
    #     print("\n")

    return listings

def get_listing_details(link_url):
    agent = "Ami Immobilier"
    URL = link_url
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

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
    location_div = soup.find("h1").get_text()
    if location_div[-5:].isdigit():
         postcode = location_div[-5:]
         location_div = location_div[:-5]
    else:
         postcode = None
    
    # print("Postcode:", postcode)

    if location_div.count("-") > 0:
         town = location_div.split("-")[-1].strip().capitalize()
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
    bedrooms = None
    try:
        for item in details_div:
            if "chambres" in item.get_text():
                  bedrooms = int("".join([num for num in item.get_text() if num.isdigit()]))
    except:
         pass
    # print("Bedrooms:", bedrooms)
              
#     # Rooms
    # pprint(details_div)
    rooms = None
    try:
        for item in details_div:
            if "pièces" in item.get_text():
                  rooms = int("".join([num for num in item.get_text() if num.isdigit()]))
    except:
         pass

    # print("Rooms:", rooms)

    # Parcel size not privided in listings
    plot = None

    try:
        for item in details_div:
            if "Surface terrain" in item.get_text():
                  plot = int("".join([num for num in item.get_text() if num.isdigit() and num.isascii()]))
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

#     # Description

    description_outer = soup.find("div", class_="et_pb_wc_description")
    description = description_outer.find("div", class_="et_pb_module_inner").p.get_text()
    
    # print(description)

    # Photos
    photos = []
    photos_div = soup.find("figure", class_="woocommerce-product-gallery__wrapper")
    photos_div = photos_div.find_all("a")
    for element in photos_div:
         photos.append(element.get("href"))

    agent_abbr = [i for i in agent_dict if agent_dict[i]==agent][0]

    make_photos_dir(ref, cwd, agent_abbr)

    photos_hosted = []
    for i in range(len(photos)):
        photos_hosted.append(dl_comp_photo(photos[i], ref, i, cwd, agent_abbr))
    
    if town == None:
         gps = None
    else:
        try:
            gps = get_gps(town)
        except:
            gps = None

    # pprint(photos_hosted)
    
    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, photos_hosted, gps)  

    # pprint(listing.__dict__)
    return listing

cwd = os.getcwd()

# pprint(get_listing_details("https://www.ami09.com/produit/5316-terrains/").__dict__)
# get_listing_details("https://www.ami09.com/produit/5316-terrains/")
# get_listing_details("https://www.ami09.com/produit/5701-maison-lavelanet/")
# ami09_get_listings()
#ami09_get_links(1)

# ami09_listings = ami09_get_listings()

# with open("api.json", "w") as outfile:
#     json.dump(ami09_listings, outfile)