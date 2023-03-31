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

    listings = []
    for i in range(len(links)):
        new_listing = get_listing_details(links[i])
        listings.append(new_listing)
        
    listings.sort(key=lambda x: x.price)
    api_listings = [listing.__dict__ for listing in listings]
    

    # for listing in api_listings:
    #     pprint(listing)
    #     print("\n")

    return api_listings

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

    if town == None:
         gps = None
    else:
        try:
            gps = get_gps(town)
        except:
            gps = None
    # print(gps)
    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, gps)
    # pprint(listing.__dict__)
    return listing

#pprint(get_listing_details("http://www.pyrenees-immobilier.com/fr/vente-maison-de-campagne-lasserre-p-r7-0900418119.html").__dict__)
# api_get_listings()
# api_get_links(1)