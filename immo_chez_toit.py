from pprint import pprint
import requests
from bs4 import BeautifulSoup
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

def immo_chez_toit_get_links(i):
    URL = "https://www.limmocheztoit.fr/a-vendre/" + str(i)
    page = requests.get(URL)

    immo_chez_toit_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in immo_chez_toit_soup.find_all('button', class_="btn-listing btn-primary"):
            links_raw.add("https://www.limmocheztoit.fr" + link.get('onclick').replace("'", "").replace("location.href=", ""))

    # pprint(links_raw)

    links = list(links_raw)       

    return links

def immo_chez_toit_get_listings():

    # Total number of listings isn't given on the page, so scans through pages until a page returns fewer than 10 listings, then stops

    partial_page = False    # Website doesn't give the total listing number, so it's done like this instead
    links = []
    page = 1
    while partial_page == False:
        new_links = immo_chez_toit_get_links(page)
        links += new_links
        if len(new_links) % 10 != 0:
             partial_page = True
        page += 1
    #pprint(links)

    pages = page - 1
    print("\nL'Immo Chez Toit number of listings:", len(links))
    print("Pages:", pages)
    print("Number of unique listing URLs found:", len(links))

    listings = [listing for listing in listings_json if listing["agent"] == "L'Immo Chez Toit"]

    links_old = []
    for listing in listings:
        if listing["agent"] == "L'Immo Chez Toit":
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
                shutil.rmtree(f"{cwd}/static/images/l'immo/{listing_ref}", ignore_errors=True) 
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
    
    # print(link_url)
    agent = "L'Immo Chez Toit"
    URL = link_url
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

    # Get type

    prop_type_div = soup.find('div', class_="bienTitle",).h1
    prop_type_div = prop_type_div.get_text().replace("  ", "").split()
    types = prop_type_div[0].strip()

    # print("\nType:", types)

    # Get location
    postcode = soup.find('span', class_="valueInfos").get_text().strip()
    town_div = soup.find('ol', class_="breadcrumb")
    town_div = town_div.find_all("li")
    for item in town_div:
         if "ville" in str(item):
              town = item.get_text()

    # print("Town:", town)
    # print("Postcode:", postcode)

    # Get price
    price_div = soup.find('span', itemprop="price").get_text()
    price = int("".join([num for num in str(price_div) if num.isdigit()]))
    # print("Price:", price, "€")

    # Get ref
    prop_ref_div = soup.find('span', itemprop="productID").get_text()
    ref = prop_ref_div.replace("Ref ", "")

    # print("ref:", ref)

    # # Get property details
    # # This returns a whole chunk of text for the property specs that gets separated to find the number of bedrooms, rooms, house size and land size. It's done in a janky way that Amy will hate

    details_div = soup.find('div', id="dataContent")
    details = details_div.find_all("p", class_="data")
    # pprint(details_div)

    # Chambres
    bedrooms = "".join([line.get_text() for line in details if "chambre(s)" in str(line)])
    bedrooms = "".join([num for num in bedrooms if num.isnumeric()])

    if bedrooms.isnumeric():
        bedrooms = int(bedrooms)
    else:
        bedrooms = None
    # print("Bedrooms:", bedrooms)

    # # Rooms
    rooms = "".join([rooms.get_text() for rooms in details if "pièces" in str(rooms)])
    rooms = "".join([num for num in rooms if num.isnumeric()])

    if rooms.isnumeric():
        rooms = int(rooms)
    else:
        rooms = None
    # print("Rooms:", rooms)


    # # Plot size

    plot_raw = "".join([plot.get_text() for plot in details if "surface terrain" in str(plot)]).replace("surface terrain", "").strip().replace(",", ".")

    if "ha" in plot_raw:
         plot = float(plot_raw.replace("ha", "").strip())
         plot = str(int(plot * 10000))
         #print(plot)
    else:
        plot = "".join([plot for plot in plot_raw if plot.isdecimal()])

    if plot.isnumeric():
        plot = int(plot)
    else:
        plot = None
    # print("Plot:", plot, "m²")

    # #Property size
    try:
        size_raw = "".join([size.get_text().replace("Surface habitable (m²)", "") for size in details if "Surface habitable (m²)" in size.get_text()])
        size_raw = size_raw.replace("\n", "").replace("m²", "").strip()
        if "," in size_raw:
            size = int(float(size_raw.replace(",", ".")))
        else:
            size = int(size_raw)
        #print(size)
    except:
        size = None
    # print("Size:", size, "m²")

    # Description
    description = soup.find('p', itemprop="description").get_text()

    # print(description)

    # Photos
    # Finds the links to full res photos for each listing and returns them as a list
    photos = []
    photos_div = soup.find('ul', class_="imageGallery")
    # print(photos_div)
    for child in photos_div.descendants:
        if child.name == "img":
            photos.append("https:" + child['src'])
    # pprint(photos)

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
    # pprint(listing.__dict__)
    return listing


cwd = os.getcwd()

# get_listing_details("https://www.limmocheztoit.fr/3267-vous-recherchez-un-bien-dans-un-village-dynamique.html")
# get_listing_details("https://www.limmocheztoit.fr/1531-vous-voulez-profitez-d-une-agreable-maison-sur-les-hauteurs.html")

# immo_listings = immo_chez_toit_get_listings()

# with open("api.json", "w") as outfile:
#     json.dump(immo_listings, outfile)

# Runs alternate between running correctly, and trying to add a delisted property, and remove a valid property. Following run is correct again.