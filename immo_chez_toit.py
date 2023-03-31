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

    partial_page = False
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

    listings = []
    for i in range(len(links)):
        new_listing = get_listing_details(links[i])
        listings.append(new_listing)
        
    listings.sort(key=lambda x: x.price)
    immo_chez_toit_listings = [listing.__dict__ for listing in listings]
    

    # for listing in time_stome_listings:
    #     pprint(listing)
    #     print("\n")

    return immo_chez_toit_listings



    #print("Number of unique listing URLs found:", len(links))

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

    if town == None:
         gps = None
    else:
        try:
            gps = get_gps(town)
        except:
            gps = None

    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, gps)
    # pprint(listing.__dict__)
    return listing

#pprint(immo_chez_toit_get_links(1))
get_listing_details("https://www.limmocheztoit.fr/3252-ideal-grande-famille-ou-investisseurs.html")
# get_listing_details("https://www.limmocheztoit.fr/1531-vous-voulez-profitez-d-une-agreable-maison-sur-les-hauteurs.html")

# immo_chez_toit_get_listings()