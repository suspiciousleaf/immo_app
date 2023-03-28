from pprint import pprint
import requests
from bs4 import BeautifulSoup
import re
import math
from models import Listing
from geopy.geocoders import Nominatim

def get_gps(town):
    geolocator = Nominatim(user_agent="property-scraper")
    location = geolocator.geocode(town + " France")
    gps = [location.latitude, location.longitude]
    return gps

def jammes_get_links(i):
    URL = "https://www.cabinet-jammes.com/fr/liste.htm?page=" + str(i)
    page = requests.get(URL)

    jammes_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in jammes_soup.find_all('a'):
            links_raw.add(link.get('href'))

    links_raw.discard(None)
    links = [link for link in links_raw if "https://www.cabinet-jammes.com/fr/detail.htm" in link]        

    return links

def jammes_get_listings():

    URL = "https://www.cabinet-jammes.com/fr/liste.htm?page=1"
    page = requests.get(URL)

    jammes_soup = BeautifulSoup(page.content, "html.parser")

    num_props_div = jammes_soup.find('span', class_="NbBien")
    num_props = int(num_props_div.find(string=True))
    print("\nJammes Immo number of listings:", num_props)
    pages = math.ceil(num_props / 12)
    print("Pages:", pages)

    links = []
    for i in range(1, pages + 1):
        links += jammes_get_links(i)

    print("Number of unique listing URLs found:", len(links))

    listings = []
    for i in range(len(links)):
        new_listing = get_listing_details(links[i])
        listings.append(new_listing)
        
    listings.sort(key=lambda x: x.price)
    jammes_listings = [listing.__dict__ for listing in listings]
    

    # for listing in jammes_listings:
    #     pprint(listing)
    #     print("\n")

    return jammes_listings

def get_listing_details(link_url):
    agent = "Cabinet Jammes"
    URL = link_url
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

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
    town = location_town.capitalize()
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

    if town == "Unknown":
         gps = None
    else:
        try:
            gps = get_gps(town)
        except:
            gps = None

    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, gps)
    # pprint(listing.__dict__)
    return listing

#get_listing_details("https://www.cabinet-jammes.com/fr/detail.htm?cle=11036111&monnaie=2")

# jammes_get_listings()