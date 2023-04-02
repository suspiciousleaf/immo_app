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

def richardson_get_links(URL):
    page = requests.get(URL)
    richardson_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = []
    for link in richardson_soup.find_all('a'):
            links_raw.append("http://www.richardsonimmobilier.com/" + link.get('href'))
    links = [link for link in links_raw if len(link) > 70]   

    return links

def richardson_get_listings():

    richardson_categories = ["vente-villa.cgi?000T", "vente-propriete.cgi?000T", "vente-maison-appartement.cgi?000T", "vente-terrain.cgi?000T", "investissement.cgi?000T"]

    links_inc_duplicates = []
    links = []

    # Richardson only shows properties by category, so code scans through each category in richardson_categories ("Commerces & Locaux" excluded)
    for i in range(len(richardson_categories)):
        URL_full = "http://www.richardsonimmobilier.com/" + richardson_categories[i]

        page = requests.get(URL_full)

        richardson_soup = BeautifulSoup(page.content, "html.parser")
        num_props_div = richardson_soup.find('td', class_="SIZE3-50").b
        num_props = int("".join([num for num in str(num_props_div) if num.isnumeric()]))  # Extracts the digits for number of properties from the HTML
        print("\nRichardson number of listings for category:", num_props)
        pages = math.ceil(num_props / 20)
        print("Pages:", pages)

        for i in range(0, pages):
            URL_page_number = URL_full[:-2] + str(i) + "T"
            links_inc_duplicates += richardson_get_links(URL_page_number)
        #print("Number of unique listing URLs found:", len(links_inc_duplicates))

    unique_listing_set = set()
    for i in range(len(links_inc_duplicates)):  # This code checks for duplicate properties that appear in multiple categories
        if links_inc_duplicates[i][-4:] not in unique_listing_set:
            links.append(links_inc_duplicates[i])
        unique_listing_set.add(links_inc_duplicates[i][-4:])

    # The line below removes and listings which are marked "Sold", "Sous compromis", etc
    links = [link for link in links if bool((BeautifulSoup(requests.get(link).content, "html.parser").find("span", class_="SIZE4"))) == False]

    print("Listings inc unavailable:", len(unique_listing_set))
    print("Number of available listing URLs found:", len(links))


    listings = []
    for i in range(len(links)):
        new_listing = get_listing_details(links[i])
        listings.append(new_listing)
        
    listings.sort(key=lambda x: x.price)
    richardson_listings = [listing.__dict__ for listing in listings]
    

    # for listing in richardson_listings:
    #     pprint(listing)
    #     print("\n")

    return richardson_listings


def get_listing_details(link_url):
    
    URL = link_url
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

    agent = "Richardson Immobilier"
    # Get type
    # print(URL)
    #prop_type_div = soup.find('td', class_="SIZE3-50").b


    prop_type_div = soup.find('td', class_="SIZE3-50").b.contents[0]
    #print(prop_type_div)
    types = str(prop_type_div).split()[0]
    #print("Type:", types)
    
    # Get ref
    ref = "".join([num for num in str(prop_type_div) if num.isdigit()])
    #print("Ref:", ref)

    # for child in prop_type_div.descendants:
    #     if child.name == "img":
    #         types = (child['alt'].split()[1].strip(","))

    # # Get location
    try: 
        town = str(soup.find('div', class_="SIZE3-50").b.contents[0]).replace("EXCLUSIF ", "").replace("SECTEUR ", "")
    except:
        town = None
    postcode = None

    # print("Town:", town)
    # print("Postcode:", postcode)


    # Get price
    price_div = soup.find("span", class_="SIZE4-50").b.contents[0]
    price = int("".join([num for num in str(price_div) if num.isdigit()]))
    # print("Price:", price, "€")

    # Get property details

    description = soup.find("span", class_="SIZE35-51").get_text()
    # print(description, "\n\n")
    # description = str(soup.find("span", class_="SIZE35-51").contents).replace("<br/>", "").replace("</span>", "").replace('<span style="color: #CC0000">', "")


    # Bedroom information not listed, sometimes written in description
    bedrooms = None

    # Rooms
    # Data stored in a table, code below finds the whole table, turns everything with b tag into a list, and removes <b> and <\b>
    areas_div = soup.find("table", class_="W100C0")
    areas_list = list(areas_div.find_all('b'))
    areas_list = [str(element).replace("<b>", "").replace("</b>", "") for element in areas_list]
    rooms = areas_list[1][1:]

    if rooms.isnumeric():
        rooms = int(rooms)
    else:
        rooms = None
    # print("Rooms:", rooms)


    # Plot size

    try:
        plot = areas_list[4].split()[0]
    except:
        plot = "a"
    
    if plot.isnumeric():
        plot = int(plot)
    else:
        plot = None
    # print("Plot:", plot, "m²")

    # # #Property size
    if len(areas_list[3]) > 0:
        size = areas_list[3].split()[0]
    else:
        size = "a"

    if size.isnumeric():
        size = int(size)
    else:
        size = None
    # print("Size:", size, "m²")

    # Terrain listings capture plot size as building size, and first section of price as plot size.
    if types == "Terrain":
        try:
            if size > plot:
                plot = size
        except:
            pass
        size = None


    # Photos
    # Finds the links to full res photos for each listing and returns them as a list
    photos_div = str(soup.find_all("img", class_="photomH")).split()
    photos = ["http://www.richardsonimmobilier.com/" + entry.replace('"', "").replace("src=", "") for entry in photos_div if "src=" in entry]

    if len(photos) > 0:
        pass
    else:
        photos_div = str(soup.find_all("img", class_="photomrH")).split()
        photos = ["http://www.richardsonimmobilier.com/" + entry.replace('"', "").replace("src=", "") for entry in photos_div if "src=" in entry] 

    if town == None:
         gps = None
    else:
        try:
            gps = get_gps(town)
        except:
            gps = None
    #pprint(len(photos))

    listing = Listing(types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, gps)
    return listing

#pprint(richardson_get_links(1))

#get_listing_details("http://www.richardsonimmobilier.com/vente-maison-Haute-Vallee-4044.cgi?00000LQUI4044")
# pprint(get_listing_details("http://www.richardsonimmobilier.com/vente-terrain-Haute-Vallee-3684.cgi?00012LQUI3684").__dict__)
# get_listing_details("http://www.richardsonimmobilier.com/vente-terrain-Haute-Vallee-3684.cgi?00012LQUI3684")

# richardson_get_listings()

