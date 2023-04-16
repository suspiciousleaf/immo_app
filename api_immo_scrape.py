from pprint import pprint
import requests
from bs4 import BeautifulSoup
import math
from models import Listing
from geopy.geocoders import Nominatim
import json
from json_search import agent_dict
import shutil
from image_downloader import make_photos_dir, dl_comp_photo
import os

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

def api_get_links(i):
    URL = "http://www.pyrenees-immobilier.com/fr/annonces-immobilieres-p-r12-{}.html#page={}".format(i, i)
    page = requests.get(URL)

    api_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in api_soup.find_all('a'):
            links_raw.add(link.get('href'))
    links_raw.discard(None)
    links = [link for link in links_raw if "http://www.pyrenees-immobilier.com/fr/vente" in link]        
    #pprint(links)
    return links

def api_get_listings():

    URL = "http://www.pyrenees-immobilier.com/fr/annonces-immobilieres-p-r12-1.html#page=1"
    page = requests.get(URL)

    api_soup = BeautifulSoup(page.content, "html.parser")

    num_props = int(api_soup.find('span', id="NbBien").get_text())
    print("\nApi Immo number of listings:", num_props)
    pages = math.ceil(num_props / 10)
    print("Pages:", pages)

    links = []
    for i in range(1, pages + 1):
        links += api_get_links(i)
    print("Number of unique listing URLs found:", len(links))

    listings = [listing for listing in listings_json if listing["agent"] == "A.P.I."]

    links_old = []
    for listing in listings:
        if listing["agent"] == "A.P.I.":
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
                shutil.rmtree(f'{cwd}/static/images/api/{listing_ref}', ignore_errors=True)
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
    agent = "A.P.I."
    URL = link_url
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

    #print("\n\nNext property\n")

    # Get type
    types = soup.find('div', class_="type").get_text()
    # print("Type:", types)


    # Get location
    postcode_div = soup.find('h1').get_text()
    postcode_div = postcode_div.split()
    postcode_string = [line for line in postcode_div if "(" in line][0]
    postcode = "".join([num for num in postcode_string if num.isdigit()])
    # print("Postcode:", postcode)

    town = soup.find("div", class_="ville").get_text().capitalize()#.replace("La", "")
    # print("Town:", town)

    # Get price
    price_div = soup.find('div', class_="price-all").get_text()
    price = int("".join([num for num in price_div if num.isdigit()]))
    # print("Price:", price, "€")

    # Get ref

    details_div = soup.find('div', class_="detail-bien-specs").get_text()
    details_div = details_div.split("\n")
    prop_ref = [line for line in details_div if "Ref" in line and len(line) < 10][0]
    ref = "".join([num for num in prop_ref if num.isdigit()])

    # print("ref:", ref)

    # Get property details

    try:
        bedrooms = [line for line in details_div if "Chambres" in line][0]
        bedrooms = int("".join([num for num in bedrooms if num.isdigit()]))
    except:
         bedrooms = None

    # print("Bedrooms:", bedrooms)

    # Rooms
    try:
        rooms = [line for line in details_div if "Pièces" in line][0]
        rooms = int("".join([num for num in rooms if num.isdigit()]))
    except:
         rooms = None

    # print("Rooms:", rooms)

    # Plot size
    try:
        plot = [line for line in details_div if "Terrain" in line and "Type" not in line][0]
        plot = int("".join([num for num in plot if num.isdigit() and num.isascii()]))
    except:
         plot = None

    # print("Plot:", plot, "m²")

    #Property size
    try:
        size = [line for line in details_div if "Surface" in line][0]
        size = int("".join([num for num in size if num.isdigit() and num.isascii()]))
    except:
         size = None

    # print("Size:", size, "m²")

    # Description

    description = soup.find("div", class_="detail-bien-desc-content").get_text()
    description = description.replace("Tweet", "").replace("Nous contacter", "").replace("Être averti d'une baisse de prix", "").replace("\n\n", "")
    # print(description)

    # Photos
    photos = []
    photos_div = soup.find_all("img", class_="photo-large")
    for element in photos_div:
         if "https://assets.adaptimmo.com/" in element.get("src"):
              photos.append(element.get("src"))
    # pprint(photos)

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
   
    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, photos_hosted, gps)
    # pprint(listing.__dict__)
    return listing

cwd = os.getcwd()

#pprint(get_listing_details("http://www.pyrenees-immobilier.com/fr/vente-maison-de-campagne-lasserre-p-r7-0900418119.html").__dict__)
# api_get_listings()
# api_get_links(1)

# api_listings = api_get_listings()

# with open("api.json", "w") as outfile:
#     json.dump(api_listings, outfile)