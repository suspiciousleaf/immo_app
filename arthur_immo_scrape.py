from pprint import pprint
import requests
from bs4 import BeautifulSoup
import math
from models import Listing
from unidecode import unidecode
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

def arthur_immo_get_links(i):
    URL = "https://www.lavelanet-arthurimmo.com/recherche,basic.htm?transactions=acheter&page=" + str(i)
    page = requests.get(URL)

    arthur_immo_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in arthur_immo_soup.find_all('a'):
            links_raw.add(link.get('href'))

    links_raw.discard(None)
    links = [link for link in links_raw if "https://www.lavelanet-arthurimmo.com/annonces/achat/" in link]        

    return links

def arthur_immo_get_listings():

    URL = "https://www.lavelanet-arthurimmo.com/recherche,basic.htm?transactions=acheter&page=1"
    page = requests.get(URL)

    arthur_immo_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = arthur_immo_soup.find('div', class_="font-semibold").contents
    num_props = int("".join([num for num in str(num_props_div) if num.isnumeric()]))  # Extracts the digits for number of properties from the HTML
 
    print("\nArthur Immobilier number of listings:", num_props)
    pages = math.ceil(num_props / 15)
    print("Pages:", pages)

    links = []
    for i in range(1, pages + 1):
        links += arthur_immo_get_links(i)
    print("Number of unique listing URLs found:", len(links))

    listings = [listing for listing in listings_json if listing["agent"] == "Arthur Immo"]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Arthur Immo":
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
                shutil.rmtree(f'{cwd}/static/images/arthur/{listing_ref}', ignore_errors=True) 
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
    
    agent = "Arthur Immo"
    URL = link_url
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

    # Get type

    parent_ul = soup.find('ul', class_="lg:flex")
    find_li = parent_ul.find_all("li", class_=None, recursive=False)
    find_li_clean = [str(line).replace("<li>", "").replace("</li>", "") for line in find_li]
    correct_line = [line for line in find_li_clean if line.find("href") == -1][0]
    #pprint(correct_line)
    types = correct_line.split()[0]
    #print("Type:", types)
    postcode = correct_line.split()[-1][1:-1]
    #print("Postcode:", postcode)

    for line in find_li:    # Identifies a line in find_li that contains the town and postcode as a string, and removes the postcode
        if line.a:
            if postcode in str(line.a):    
                postcode_line = str(line.a)[str(line.a).find(">")+1 :]
    town = postcode_line[:postcode_line.find(postcode)-2]

    #print("Town:", town)

    # Get price
    price_div = soup.find('div', class_="text-4xl").contents[0]
    price = int(str(price_div).replace("€", "").replace(" ", ""))
    #print("Price:", price, "€")

    # Get ref
    details_div = soup.find('ul', class_="lg:grid-cols-2").contents
    for line in details_div:
        if "Ref internal" in str(line):
            ref = str(line).replace("text-gray-400", "").replace("1e2022", "")
    
    ref = "".join([num for num in ref if num.isdigit()])
    # print("ref:", ref)

    # Chambres
    bedrooms = None
    try:
        for line in details_div:
            if "chambres" in str(line):
                bedrooms = str(line).replace("text-gray-400", "").replace("1e2022", "")
        bedrooms = int("".join([num for num in bedrooms if num.isdigit()]))
    except:
        pass

    #print("Bedrooms:", bedrooms)

    # Rooms
    rooms = None
    try:
        for line in details_div:
            if "pièces" in str(line):
                rooms = str(line).replace("text-gray-400", "").replace("1e2022", "")
        rooms = int("".join([num for num in rooms if num.isdigit()]))
    except:
        pass

    #print("Rooms:", rooms)

    # Plot size

    plot = None
    for line in details_div:
        if "terrain" in str(line):
            plot = str(line).replace("text-gray-400", "").replace("1e2022", "")
    try:
        plot = int("".join([num for num in plot if num.isnumeric() and num.isascii()]))
    except:
        pass

    # print("Plot:", plot, "m²")

    # Property size
    size = None
    for line in details_div:
        if "habitable" in str(line):
            size = str(line).replace("text-gray-400", "").replace("1e2022", "")
    try:
        size = int("".join([num for num in size if num.isnumeric() and num.isascii()]))
    except:
        pass

    #print("Size:", size, "m²")

    # Description
    # Finds the main block, removes all the <b> etc tags, split and join to remove excess whitespace, and unidecode to remove accents
    description_div = str(soup.find('div', class_="text-[#969A9D]"))
    description = description_div[description_div.find("<b>")+3:description_div.find("</p>")]
    description = description.replace("<b>", "").replace("<br>", "").replace("</b>", "").replace("<br/>", "").replace("</br>", "")
    description = unidecode(" ".join(description.split()))
    #print(description)

    # Photos
    # Photos are stored on a different page and hosted on another website. This finds the website and generates the links without visiting the main image page, or hosting website.
    # Listings with 5 or fewer photos don't have a separate page to host them, so the try/except tries the method for more than 5 images, if that fails, then scrapes the listing page for the photos available.

    photos = []
    try:
        total_number_photos = 5 + int(soup.find('p', class_="lg:text-2xl").contents[0][1:])
        photo_links_div = soup.find('img', class_="object-cover")
        photo_raw_link = photo_links_div.get("src").split("/0/")

        for i in range(total_number_photos):  # Might need to add .jpg to the end of links to make it work
            photos.append(photo_raw_link[0] + "/" + str(i) + "/" + photo_raw_link[1])
    except:
        photo_links_div = soup.find_all('img', class_="object-cover")
        for child in photo_links_div:
            if "backgrounds" not in child.get("src"):
                photos.append(child.get("src"))

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
            gps = get_gps(town, postcode)
        except:
            gps = None

    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, photos_hosted, gps)
    return listing

cwd = os.getcwd()


# #pprint(arthur_immo_get_links(1))
# print(get_listing_details("https://www.arthurimmobilier.com/vente/11-arthur/78-bram/belle-maison-vigneronne-avec-piscine-et-jardin-prestige/)1249-maison"))

# arthur_immo_get_listings()

# pprint(get_listing_details("https://www.lavelanet-arthurimmo.com/annonces/achat/terrain/dalou-09120/26609674.htm").__dict__)
# pprint(get_listing_details("https://www.lavelanet-arthurimmo.com/annonces/achat/terrain/mazeres-sur-salat-31260/22388518.htm").__dict__)

# arthur_listings = arthur_immo_get_listings()

# with open("api.json", "w") as outfile:
#     json.dump(arthur_listings, outfile)