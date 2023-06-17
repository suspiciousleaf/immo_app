import grequests

# import requests
from bs4 import BeautifulSoup
from pprint import pprint
import json
import time
import concurrent.futures
from unidecode import unidecode
from models import Listing
from utilities.utilities import get_gps, get_data, property_types

proxy = {
    "http": "http://158.160.56.149:8080",
    "http": "http://103.173.128.51:8080",
    "http": "http://201.182.251.142:999",
    "http": "http://95.216.75.78:3128",
    "http": "http://51.79.50.31:9300",
    "http": "http://202.131.159.210:80",
    "http": "http://41.76.145.136:443",
    "http": "http://188.168.25.90:81",
    "http": "http://64.225.8.82:9967",
    "http": "http://47.92.93.39:8888",
    "http": "http://201.184.24.13:999",
    "http": "http://213.52.102.66:80",
    "http": "http://3.132.30.131:80",
    "http": "http://41.76.145.136:3128",
    "http": "http://75.119.129.192:3128",
    "http": "http://161.35.197.118:8080",
    "http": "http://5.161.80.172:8080",
    "http": "http://201.158.48.74:8080",
    "http": "http://41.76.145.136:8080",
    "http": "http://51.159.115.233:3128",
    "http": "http://64.226.110.184:45212",
    "http": "http://65.21.110.128:8080",
    "http": "http://213.52.102.30:10800",
    "http": "http://50.232.250.157:8080",
    "http": "http://18.143.215.49:80",
    "http": "http://190.119.86.66:999",
    "http": "http://180.184.91.187:443",
    "http": "http://95.216.156.131:8080",
    "http": "http://5.78.83.35:8080",
    "http": "http://78.110.195.242:7080",
    "http": "http://213.32.75.88:9300",
    "http": "http://31.186.241.8:8888",
    "http": "http://209.38.250.139:45212",
    "http": "http://51.158.189.189:8080",
}


try:
    try:
        with open("postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/postcodes_gps_dict.json",
            "r",
            encoding="utf8",
        ) as infile:
            gps_dict = json.load(infile)
except:
    print("gps_dict not found")
    gps_dict = []
try:
    try:
        with open("listings.json", "r", encoding="utf8") as infile:
            listings_json = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/listings.json", "r", encoding="utf8"
        ) as infile:
            listings_json = json.load(infile)
except:
    listings_json = []

type_list_raw = ["Terrain", "Immeuble"]
for value in property_types.values():
    type_list_raw.extend(value)
type_list = [item.casefold() for item in type_list_raw]


def get_listing_details(resp_object, link_url):
    prop_soup = BeautifulSoup(resp_object.content, "html.parser")
    agent = "Propriétés Privées"
    link_url = link_url
    # print(link_url)
    price = get_price(prop_soup)
    # print(f"Price: {price} €")
    ref = get_ref(prop_soup)
    # print(f"Ref: {ref}")
    types = get_type(prop_soup)
    # print(f"Type: {types}")
    town = get_town(prop_soup)
    # print(f"Town: {town}")
    postcode = get_postcode(prop_soup)
    # print(f"Postcode: {postcode}")
    details_dict = get_details(prop_soup, types)
    rooms = details_dict["rooms"]
    # print(f"Rooms: {rooms}")
    bedrooms = details_dict["bedrooms"]
    # print(f"Bedrooms: {bedrooms}")
    plot = details_dict["plot"]
    # print(f"Plot: {plot} m²")
    size = details_dict["size"]
    # print(f"Size: {size} m²")
    description = get_description(prop_soup)
    # print(description)
    gps = get_gps_location(town, postcode)
    # print(f"GPS: {gps}")
    photos = get_photos(prop_soup)
    photos_hosted = photos
    # pprint(photos)

    listing = Listing(
        types,
        town,
        postcode,
        price,
        agent,
        ref,
        bedrooms,
        rooms,
        plot,
        size,
        link_url,
        description,
        photos,
        photos_hosted,
        gps,
    )
    return listing.__dict__


def get_price(prop_soup):
    try:
        return int(
            "".join(
                [
                    num
                    for num in prop_soup.find("p", class_="trade-price").get_text()
                    if num.isnumeric()
                ]
            )
        )
    except:
        return 0


def get_ref(prop_soup):
    try:
        ref_string = prop_soup.find("p", class_="trade-reference").get_text()
        return ref_string[ref_string.find(".") + 1 :].strip()
    except:
        return None


def get_type(prop_soup):
    try:
        title_string = unidecode(
            prop_soup.find("h1", class_="trade-title").get_text()
        ).casefold()
        for word in title_string.split():
            if word.casefold() in type_list:
                return word.capitalize()
    except:
        return None


def get_town(prop_soup):
    try:
        town_string = prop_soup.find("p", class_="trade-location").get_text()
        return unidecode(
            town_string[: town_string.find("(")].strip().replace("-", " ")
        ).capitalize()
    except:
        return None


def get_postcode(prop_soup):
    try:
        return "".join(
            [
                num
                for num in prop_soup.find("p", class_="trade-location").get_text()
                if num.isnumeric()
            ]
        )
    except:
        return None


def get_details(prop_soup, types):
    details_list = []
    details_dict = {"rooms": None, "bedrooms": None, "size": None, "plot": None}
    details_div = prop_soup.find("div", class_="trade-details")
    details_divs = details_div.findAll("div", class_="trade-features")
    for div in details_divs:
        for item in div:
            if item.get_text():
                details_list.append(item.get_text())
    for item in details_list:
        if "pièces" in item:
            try:
                details_dict["rooms"] = int(
                    "".join([num for num in item if num.isnumeric()])
                )
            except:
                details_dict["rooms"]
        elif "chambre" in item:
            try:
                details_dict["bedrooms"] = int(
                    "".join([num for num in item if num.isnumeric()])
                )
            except:
                details_dict["bedrooms"] = None
        elif "Terrain" in item:
            try:
                details_dict["plot"] = int(
                    float(
                        "".join(
                            [num for num in item if num.isnumeric() and num.isascii()]
                        )
                    )
                )
            except:
                details_dict["plot"] = None
        elif item.replace(" m²", "").isnumeric():  # WILL CAUSE ERROR WITH DECIMAL
            try:
                details_dict["size"] = int((item.replace(" m²", "")))
            except:
                details_dict["size"] = None

    if types == "Terrain" and details_dict["size"] and not details_dict["plot"]:
        details_dict["plot"] = details_dict["size"]
        details_dict["size"] = None

    return details_dict


def get_description(prop_soup):
    try:
        description = []
        description_raw = prop_soup.find("div", class_="trade-description").p.contents
        for item in description_raw:
            if "SAS PROPRIETES PRIVEES" in item:
                break
            description.append(item)
    except:
        description = []
    return description


def get_gps_location(town, postcode):
    gps = None
    if isinstance(town, str):
        if (
            postcode + ";" + town.casefold()
        ) in gps_dict:  # Check if town is in premade database of GPS locations, if not searches for GPS
            gps = gps_dict[postcode + ";" + town.casefold()]
        else:
            try:
                gps = get_gps(town, postcode)
            except:
                pass
    return gps


def get_photos(prop_soup):
    try:
        photos_raw = prop_soup.find("ol", class_="carousel__track")
        photos_list = photos_raw.findAll("img")
        photos = [photo.get("src") for photo in photos_list]
    except:
        photos = []
    return photos


def privee_get_links(page):
    # page.encoding = "utf-8"
    soup = BeautifulSoup(page.content, "html.parser")
    page_listings = soup.find("div", class_="trades-list")
    props_list = page_listings.find("div", class_="trades")
    raw_listings = props_list.findAll("div", class_="trade")
    links = [
        f"https://www.proprietes-privees.com{prop.a.get('href')}"
        for prop in raw_listings
    ]
    return links


def privee_get_listings():
    """Scrapes www.proprietes-privees.com local properties and returns a list of available listings as dictionaries"""
    t0 = time.perf_counter()

    agent_urls = [
        "https://www.proprietes-privees.com/negociateur/pascal.bourbon",
        "https://www.proprietes-privees.com/negociateur/alban.paumier",
        "https://www.proprietes-privees.com/negociateur/guillaume.ellin",
        "https://www.proprietes-privees.com/negociateur/benjamin.cadiou",
        "https://www.proprietes-privees.com/negociateur/clement.philippe",
        "https://www.proprietes-privees.com/negociateur/charlotte.khoudiacoff",
        "https://www.proprietes-privees.com/negociateur/laurent.vernhet",
        "https://www.proprietes-privees.com/negociateur/samuel.gros",
        "https://www.proprietes-privees.com/negociateur/francois.deseynes",
        "https://www.proprietes-privees.com/negociateur/francois.deseynes",
    ]

    links = []
    resp = get_data(agent_urls, prox=True)
    for item in resp:
        links.extend(privee_get_links(item["response"]))

    print("Number of unique listing URLs found:", len(links))

    listings = [
        listing for listing in listings_json if listing["agent"] == "Propriétés Privées"
    ]

    links_old = []
    for listing in listings:
        links_old.append(listing["link_url"])

    links_to_scrape = [link for link in links if link not in links_old]
    print("New listings to add:", len(links_to_scrape))
    # pprint(links_to_scrape)
    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))
    # pprint(links_dead)

    listing_photos_to_delete_local = []

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []
    resp_to_scrape = get_data(links_to_scrape, prox=True)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            get_listing_details,
            (item["response"] for item in resp_to_scrape),
            links_to_scrape,
        )
        for result in results:
            if isinstance(result, str):
                failed_scrape_links.append(result)
                counter_fail += 1
            else:
                listings.append(result)
                counter_success += 1

    if links_to_scrape:
        print(f"Successfully scraped: {counter_success}/{len(links_to_scrape)}")

    if failed_scrape_links:
        print(f"Failed to scrape: {counter_fail}/{len(links_to_scrape)} \nFailed URLs:")
        pprint(failed_scrape_links)

    listings.sort(key=lambda x: x["price"])

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Time elapsed for Propriétés Privées Immobilier: {time_taken:.2f}s")

    return listings


privee_listings = privee_get_listings()

with open("api.json", "w", encoding="utf-8") as outfile:
    json.dump(privee_listings, outfile, ensure_ascii=False)


# with open(
#     "response.html", mode="w", encoding="utf-8"
# ) as file:  # Set the encoding when opening the file
#     for line in page.text:
#         file.write(line)
