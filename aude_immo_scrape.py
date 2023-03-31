from pprint import pprint
import requests
from bs4 import BeautifulSoup
import math
from models import Listing
from geopy.geocoders import Nominatim

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

    listings = []
    for i in range(len(links)):
        new_listing = get_listing_details(links[i])
        listings.append(new_listing)
        
    listings.sort(key=lambda x: x.price)
    aude_immo_listings = [listing.__dict__ for listing in listings]
    

    # for listing in time_stome_listings:
    #     pprint(listing)
    #     print("\n")

    return aude_immo_listings



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

    details_div = str(soup.find('div', id="dataContent"))
    details = details_div.split("\n")
    #pprint(details)

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
    size = [size for size in size if size.isnumeric()]
    size = "".join(size[1:-1])

    if size.isnumeric():
        size = int(size)
    else:
        size = None
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

    if town == None:
         gps = None
    else:
        try:
            gps = get_gps(town)
        except:
            gps = None

    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, gps)
    return listing

#pprint(aude_immo_get_links(1))
#get_listing_details("https://www.audeimmobilier.com/vente/11-aude/252-axat/maison-de-village-a-renover-avec-terres-eparses/1248-maison")

# aude_immo_get_listings()