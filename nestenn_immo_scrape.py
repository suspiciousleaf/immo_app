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

    listings = []
    for i in range(len(links)):
        new_listing = get_listing_details(links[i])
        listings.append(new_listing)
        
    listings.sort(key=lambda x: x.price)
    nestenn_immo_listings = [listing.__dict__ for listing in listings]
    

#     # for listing in nestenn_immo_listings:
#     #     pprint(listing)
#     #     print("\n")

    return nestenn_immo_listings

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
    bedrooms = 99
    rooms = 99
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

    if town == "Unknown":
         gps = None
    else:
        try:
            gps = get_gps(town)
        except:
            gps = None

    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, gps)
    #pprint(listing.__dict__)
    return listing

#get_listing_details("https://immobilier-lavelanet.nestenn.com/a-vendre-proche-de-foix-maison-de-village-de-116-m2-ref-38030026")
#pprint(get_listing_details("https://immobilier-lavelanet.nestenn.com/terrain-a-vendre-belesta-5245-m2-pour-lotissement-ideal-investisseurs-ref-33828908").__dict__)


#nestenn_immo_get_listings()
#nestenn_immo_get_links(1)