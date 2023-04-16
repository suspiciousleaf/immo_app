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

try:
    with open("listings.json", "r") as infile:
        listings_json = json.load(infile)
except:
    listings_json = []

def get_gps(town, postcode = ""):
    geolocator = Nominatim(user_agent="property-scraper")
    location = geolocator.geocode(town + " " + postcode + " France")
    gps = [location.latitude, location.longitude]
    return gps

def nestenn_immo_get_links(i):
    URL = "https://immobilier-lavelanet.nestenn.com/?action=listing&transaction=acheter&sort=prix&page={}".format(str(i))
    page = requests.get(URL)

    nestenn_immo_soup = BeautifulSoup(page.content, "html.parser")
  
    links = []
    
    links_raw_div = nestenn_immo_soup.find("div", id="gridPropertyOnly")
    links_raw = links_raw_div.find_all("div", class_="property_title")
    for link in links_raw:
        if "Vendu" in link.get_text():
            pass
        else:
            links.append(link.a.get("href"))

    # pprint(len(links))
    # pprint(links)

    return links

def nestenn_immo_get_listings():

    URL = "https://immobilier-lavelanet.nestenn.com/?action=listing&transaction=acheter&sort=prix&page=1"
    page = requests.get(URL)

    nestenn_immo_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = nestenn_immo_soup.find('div', class_="mt_5rem").get_text()
    num_props = int("".join([num for num in num_props_div if num.isnumeric()]))
    print("\nNestenn Immo number of listings:", num_props)
    pages = math.ceil(num_props / 30)
    print("Pages:", pages)

    links = []
    for i in range(1, pages + 1):
        links += nestenn_immo_get_links(i)

    print("Number of unique listing URLs found:", len(links))
    #pprint(links)

    listings = [listing for listing in listings_json if listing["agent"] == "Nestenn"]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Nestenn":
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
                shutil.rmtree(f'{cwd}/static/images/nestenn/{listing_ref}', ignore_errors=True) 
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []
    for i in range(len(links_to_scrape)):
        try:
            new_listing = get_listing_details(links_to_scrape[i])
            listings.append(new_listing.__dict__)
            counter_success += 1
        except:
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
    agent = "Nestenn"
    URL = link_url
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

    #pprint(soup)
#     #print("\n\nNext property\n")
    #print(URL)
    
    # Get several details from contact form hidden values

    details_div = soup.find('div', class_="box_emailing")
    details_div_2 = details_div.find_all("input")
    #pprint(details_div_2)
    for line in details_div_2:
        if line.get("name") == "type_bien":
            types = line.get("value")
        elif line.get("name") == "prix":
            price = int(line.get("value"))
        elif line.get("name") == "num_mandat":
            ref = line.get("value")
        elif line.get("name") == "localisation":
            postcode = line.get("value")[:line.get("value").find(" ")]
            town = line.get("value")[line.get("value").find(" ")+1:].capitalize()

    # print("Type:", types)
    # print("Town:", town)
    # print("Postcode:", postcode)
    # print("Price:", price, "€")
    #print("ref:", ref)

    # Get description

    description = soup.find("p", class_="square_text_p").get_text()
    description = "".join(description.splitlines()).strip()

    # print(description)

    # Property details
    bedrooms = None
    rooms = None
    plot = None
    size = None
    details_div = soup.find_all("div", class_="icon_property_description")
    details_list = [line.get_text() for line in details_div]
    # pprint(details_list)
    for line in details_list:
        if "pièces" in line:
            rooms = int(line.split()[0])
        elif "chambre" in line:
            bedrooms = int(line.split()[0])
        elif "habitables" in line:
            size = int(float(line.split()[0]))
        elif "terrain" in line:
            plot = line.split("et")[1]
            plot = int("".join([num for num in plot if num.isnumeric() and num.isascii()]))

    # print("Terrain: ", plot, "m²")    
    # print("Bedrooms:", bedrooms)
    # print("Rooms:", rooms)
    # print("Size:", size, "m²")

    # Photos
    # Finds the links to full res photos for each listing which are stored as a single string (sep ";"), splits and returns them as a list. Removes empty string at the end of the list

    photos_div = soup.find('section', class_="section_bien_photo")
    photos_raw_list = photos_div.get("data-photos").split(";")
    photos = [photo for photo in photos_raw_list if len(photo) > 10]
    #pprint(photos)

    agent_abbr = [i for i in agent_dict if agent_dict[i]==agent][0]

    make_photos_dir(ref, cwd, agent_abbr)

    photos_hosted = []
    for i in range(len(photos)):
        try:
            photos_hosted.append(dl_comp_photo(photos[i], ref, i, cwd, agent_abbr))
        except:
            pass

    if town == None:
         gps = None
    else:
        try:
            gps = get_gps(town)
        except:
            gps = None

    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, photos_hosted, gps)
    #pprint(listing.__dict__)
    return listing

cwd = os.getcwd()

#get_listing_details("https://immobilier-lavelanet.nestenn.com/a-vendre-proche-de-foix-maison-de-village-de-116-m2-ref-38030026")
#pprint(get_listing_details("https://immobilier-lavelanet.nestenn.com/terrain-a-vendre-belesta-5245-m2-pour-lotissement-ideal-investisseurs-ref-33828908").__dict__)


#nestenn_immo_get_listings()
#nestenn_immo_get_links(1)

# nestenn_listings = nestenn_immo_get_listings()

# with open("api.json", "w") as outfile:
#     json.dump(nestenn_listings, outfile)