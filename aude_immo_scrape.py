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

def aude_immo_get_links(i):
    URL = "https://www.audeimmobilier.com/recherche/" + str(i)
    page = requests.get(URL)

    aude_immo_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in aude_immo_soup.find_all('a'):
            links_raw.add(link.get('href'))

    links_raw.discard(None)
    links = [link for link in links_raw if "https://www.audeimmobilier.com/vente/" in link]        

    return links

def aude_immo_get_listings():

    URL = "https://www.audeimmobilier.com/recherche/1"
    page = requests.get(URL)

    aude_immo_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = aude_immo_soup.find('div', class_="resultatFounded")
    num_props = int("".join([num for num in str(num_props_div) if num.isnumeric()]))  # Extracts the digits for number of properties from the HTML
 
    print("\nAude Immobilier number of listings:", num_props)
    pages = math.ceil(num_props / 10)
    print("Pages:", pages)

    links = []
    for i in range(1, pages + 1):
        links += aude_immo_get_links(i)
    print("Number of unique listing URLs found:", len(links))

    listings = [listing for listing in listings_json if listing["agent"] == "Aude Immobilier"]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Aude Immobilier":
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
                shutil.rmtree(f'{cwd}/static/images/aude/{listing_ref}', ignore_errors=True) 
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



    #print("Number of unique listing URLs found:", len(links))

def get_listing_details(link_url):
    
    agent = "Aude Immobilier"
    URL = link_url
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

    # Get type

    prop_type_div = soup.find('li', class_="container_ImgSlider_Mdl")
    for child in prop_type_div.descendants:
        if child.name == "img":
            types = (child['alt'].split()[1].strip(","))

    # Get location
    location_div = str(soup.find('div', class_="elementDtTitle"))
    location_raw = location_div[location_div.find("<h1>")+4:location_div.find("</h1>")].split()
    postcode = location_raw.pop(-1).strip("(").strip(")")
    town = " ".join(location_raw).replace("La ville de ", "")

    # print("Town:", town)
    # print("Postcode:", postcode)

    # Get price
    price_div = soup.find('p', class_="price")
    price = int("".join([num for num in str(price_div) if num.isdigit()]))
    # print("Price:", price, "€")

    # Get ref
    prop_ref_div = soup.find_all('p', class_="ref")
    prop_ref = "".join([num for num in str(prop_ref_div) if num.isdigit()])
    ref = prop_ref

    # print("ref:", ref)

    # # Get property details
    # # This returns a whole chunk of text for the property specs that gets separated to find the number of bedrooms, rooms, house size and land size. It's done in a janky way that Amy will hate

    # details_div = str(soup.find('div', id="dataContent"))
    # print(details_div)
    # details = details_div.split("\n")
    #pprint(details)

    details_div = soup.find('div', id="dataContent").get_text()
    details = details_div.split("\n")
    # pprint(details)

    # Chambres
    bedrooms = "".join([line for line in details if "chambre(s)" in line])
    bedrooms = "".join([num for num in bedrooms if num.isnumeric()])

    if bedrooms.isnumeric():
        bedrooms = int(bedrooms)
    else:
        bedrooms = None
    # print("Bedrooms:", bedrooms)

    # Rooms
    rooms = "".join([rooms for rooms in details if "pièces" in rooms])
    rooms = "".join([num for num in rooms if num.isnumeric()])

    if rooms.isnumeric():
        rooms = int(rooms)
    else:
        rooms = None
    # print("Rooms:", rooms)


    # # Plot size

    plot = "".join([plot for plot in details if "surface terrain" in plot])
    plot = "".join([plot for plot in plot if plot.isnumeric()])
    plot = plot[:-1]

    if plot.isnumeric():
        plot = int(plot)
    else:
        plot = None
    # print("Plot:", plot, "m²")

    # #Property size
    size = str([size for size in details if "Surface habitable (m²)" in size])
    try:
        size = round(float(size[size.index(":")+2:-5].replace(",", ".")))   #   This converts to "." decimal notation, and rounds to an int
        # print(size)
    except:
        size = None
  
    # The code below was missing decimal points from sizes, changed to the above

    # size = str([size for size in details if "Surface habitable (m²)" in size])
    # size = [size for size in size if size.isnumeric()]
    # size = "".join(size[1:-1])
    # if size.isnumeric():
    #     size = int(size)
    # else:
    #     size = None

    # print("Size:", size, "m²")

    # Description
    description_div = soup.find('div', class_="offreContent")

    for child in description_div.children:
        if child.name == "p":
            description = str(child.contents[0])

    # print(description)

    # Photos
    # Finds the links to full res photos for each listing and returns them as a list
    photos = []
    photos_div = soup.find('ul', class_="slider_Mdl")
    #print(photos_div)
    for child in photos_div.descendants:
        if child.name == "img":
            photos.append("https:" + child['data-src'])
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
    return listing

cwd = os.getcwd()

#pprint(aude_immo_get_links(1))
# pprint(get_listing_details("https://www.audeimmobilier.com/vente/11-aude/243-bouisse/maison-de-village-renovee-avec-jardin/1215-maison").__dict__)
# get_listing_details("https://www.audeimmobilier.com/vente/11-aude/243-bouisse/maison-de-village-renovee-avec-jardin/1215-maison")

# aude_immo_listings = aude_immo_get_listings()

# with open("api.json", "w") as outfile:
#     json.dump(aude_immo_listings, outfile)