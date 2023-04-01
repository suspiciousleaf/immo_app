from pprint import pprint
import requests
from bs4 import BeautifulSoup
import re
import math
from models import Listing
from geopy.geocoders import Nominatim

def get_gps(town, postcode = ""):
    geolocator = Nominatim(user_agent="property-scraper")
    location = geolocator.geocode(town + " " + postcode + " France")
    gps = [location.latitude, location.longitude]
    return gps


def mm_immo_get_links(i):
    URL = "https://www.mmimmobilier.com/fr/annonces/acheter-p-r70-4-{}.html".format(str(i))
    page = requests.get(URL)

    mm_immo_soup = BeautifulSoup(page.content, "html.parser")
    links_raw = set()
    for link in mm_immo_soup.find_all('a'):
            links_raw.add(link.get('href'))

    links_raw.discard(None)
    links = [link for link in links_raw if "https://www.mmimmobilier.com/fr/annonce/vente" in link]
    #pprint(links)

    return links

def mm_immo_get_listings():

    URL = "https://www.mmimmobilier.com/fr/annonces/acheter-p-r70-4-1.html"
    page = requests.get(URL)

    mm_immo_soup = BeautifulSoup(page.content, "html.parser")

    num_props_div = mm_immo_soup.find('span', class_="NbBien")
    num_props = int(num_props_div.find(string=True))
    print("\nM&M Immo number of listings:", num_props)
    pages = math.ceil(num_props / 10)
    print("Pages:", pages)

    links = []
    for i in range(1, pages + 1):
        links += mm_immo_get_links(i)

    print("Number of unique listing URLs found:", len(links))
    #pprint(links)

    listings = []
    for i in range(len(links)):
        new_listing = get_listing_details(links[i])
        listings.append(new_listing)
        
    listings.sort(key=lambda x: x.price)
    mm_immo_listings = [listing.__dict__ for listing in listings]
    

    # for listing in mm_immo_listings:
    #     pprint(listing)
    #     print("\n")

    return mm_immo_listings

def get_listing_details(link_url):
    agent = "M&M Immobilier"
    URL = link_url
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

    #print("\n\nNext property\n")

    # Get type
    prop_type_div = soup.find('h1', class_="detail-bien-type")
    prop_type = prop_type_div.find(string=True)
    #print("Type:", prop_type)
    types = prop_type

    # Get location
    location_div = soup.find('h2', class_="detail-bien-ville")
    location_raw = location_div.find(string=True).strip().split()
    location_postcode = location_raw.pop(-1).strip("(").strip(")")
    location_town = " ".join(location_raw).capitalize()
    town = location_town.replace("Region ", "").replace(" centre ville", "")
    postcode = location_postcode

    #print("Town:", town)
    #print("Postcode:", postcode)

    # Get price
    price_div = soup.find('div', class_="detail-bien-prix")
    price = price_div.find(string=re.compile("€"))
    price = int(price.replace(" ", "").strip("€"))
    #print("Price:", price, "€")

    # Get ref

    #This is all copied from Jammes, comments could be incorrect
    # Page returns two identical spans with itemprop="productID", one with a hidden ref and one with the 4 digit visible ref. No way to differentiate between the two. The second one has the desired  ref, so I turned it into a list, pulled the second item on the list (with the correct ref), then list comprehension to extract the digits, and join them into a string to get the correct ref.

    prop_ref_div = soup.find_all('span', itemprop="productID")
    prop_ref = list(prop_ref_div)
    prop_ref = "".join([char for char in str(prop_ref[1]) if char.isnumeric()])
    ref = prop_ref

    #print("ref:", ref)

    # Get description

    description = soup.find("span", itemprop="description").get_text()
    description = "".join(description.splitlines())

    #print(description)

    # Property details

    details_div = soup.find("div", class_="detail-bien-specs")
    details_div = details_div.find_all("li")

    #Chambres
    try:
      for bedrooms_line in details_div:
          if "chambre(s)" in bedrooms_line.get_text():
                bedrooms = int(bedrooms_line.get_text().split()[0])
    except:
         bedrooms = 99

    #print("Bedrooms:", bedrooms)

#     # Rooms
    try:
      for rooms_line in details_div:
          if "pièce(s)" in rooms_line.get_text():
                rooms = int(rooms_line.get_text().split()[0])
    except:
         rooms = 99

    #print("Rooms:", rooms)

    # Plot size

    try:
      for plot_line in details_div:
          if "terrain" in str(plot_line):
                plot = int(plot_line.get_text().split()[0])
    except:
         plot = None

    #print("Plot:", plot, "m²")

    # Property size
    try:
      for size_line in details_div:
          if "surface" in str(size_line):
                size = int(size_line.get_text().split()[0])
    except:
         size = None
    #print("Size:", size, "m²")

    # Photos
    # Finds the links to full res photos for each listing, removes the "amp;" so the links work, and returns them as a list

    photos = []
    photos_div = soup.find('div', class_="large-flap-container")
    photos_div = photos_div.find_all("img")
    for child in photos_div:
        if "anti-cheat" not in child.get("src"):
            if "www.mmimmobilier.com" not in child.get("src"):
                photos.append(child.get("src"))

    if town == None:
         gps = None
    else:
        try:
            gps = get_gps(town)
        except:
            gps = None
    #pprint(photos)

    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, gps)
    #pprint(listing.__dict__)
    # print(gps)
    return listing

# pprint(get_listing_details("https://www.mmimmobilier.com/fr/annonce/vente-maison-individuelle-villefort-p-r7-110271658.html").__dict__)


#pprint(mm_immo_get_links(1))     
# pprint(len(mm_immo_get_links(1)))

# mm_immo_get_listings()