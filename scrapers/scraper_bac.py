import time
import math
import json
import concurrent.futures

# This must be imported as it is imported with get_gps, and if requests is imported before grequests it will cause recursion error
import grequests
import requests
from pprint import pprint
from bs4 import BeautifulSoup
from unidecode import unidecode

from models import Listing
from utilities.utility_holder import get_gps, get_data

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


def bac_get_listings(old_listing_urls_dict):
    t0 = time.perf_counter()

    URL = "https://www.bac-immobilier.com/vente/1"
    page = requests.get(URL)

    bac_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = bac_soup.find("div", class_="resultatFounded")
    # Extracts the digits for number of properties from the HTML
    num_props = int("".join([num for num in str(num_props_div) if num.isnumeric()]))

    print("\nBAC Immobilier number of listings:", num_props)
    pages = math.ceil(num_props / 10)
    print("Pages:", pages)

    all_search_pages = [
        f"https://www.bac-immobilier.com/vente/{i}" for i in range(1, pages + 1)
    ]

    links = []
    resp = get_data(all_search_pages)
    for item in resp:
        links += bac_get_links(item["response"])

    print("Number of unique listing URLs found:", len(links))
    # pprint(links)

    links_old = set(old_listing_urls_dict.keys())

    # print("Listings found from prevous scrape:", len(links_old))

    links_to_scrape = [link for link in links if link not in links_old]
    print("New listings to add:", len(links_to_scrape))
    # pprint(links_to_scrape)
    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))
    # pprint(links_dead)

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    resp_to_scrape = get_data(links_to_scrape)

    listings = []

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

    listings_duplicates_removed = []
    ref_list = []
    for listing in listings:
        if listing["ref"] not in ref_list:
            ref_list.append(listing["ref"])
            listings_duplicates_removed.append(listing)

    print(f"Total listings without duplicates: {len(listings_duplicates_removed)}")
    t1 = time.perf_counter()
    time_taken = t1 - t0
    print(f"Time elapsed for BAC Immobilier: {time_taken:.2f}s")

    return {"listings": listings_duplicates_removed, "urls_to_remove": links_dead}


def bac_get_links(page):
    bac_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in bac_soup.find_all("a"):
        links_raw.add(link.get("href"))

    links_raw.discard(None)
    links = [
        link for link in links_raw if "https://www.bac-immobilier.com/vente/" in link
    ]

    return links


def get_listing_details(page, url):
    try:
        agent = "BAC Immobilier"
        link_url = url
        page.encoding = "utf-8"
        soup = BeautifulSoup(page.content, "html.parser")

        # Get type

        prop_type_div = soup.find("li", class_="container_ImgSlider_Mdl")
        for child in prop_type_div.descendants:
            if child.name == "img":
                types = child["alt"].split()[1].strip(",")

        # print(f"Type: {types}")

        # Get location
        location_div = str(soup.find("div", class_="elementDtTitle"))
        location_raw = location_div[
            location_div.find("<h1>") + 4 : location_div.find("</h1>")
        ].split()
        postcode = location_raw.pop(-1).strip("(").strip(")")
        town = " ".join(location_raw).replace("La ville de ", "")
        town = unidecode(town.replace("-", " ")).capitalize()

        # print("Town:", town)
        # print("Postcode:", postcode)

        # Get price
        price_div = soup.find("p", class_="price")
        price = int("".join([num for num in str(price_div) if num.isdigit()]))
        # print("Price:", price, "€")

        # Get ref
        ref_div = soup.find("p", class_="ref").get_text().split("-")[0]
        ref = "".join([num for num in ref_div if num.isnumeric()])

        # print("ref:", ref)

        # # Get property details
        # # This returns a whole chunk of text for the property specs that gets separated to find the number of bedrooms, rooms, house size and land size.
        bedrooms = None
        rooms = None
        size = None
        plot = None

        details_div = soup.find("div", id="dataContent", class_="bien-des-info")
        details_list = details_div.findAll("li", class_="data")
        for line in details_list:
            line = line.get_text(strip=True)
            if "chambre(s)" in line:
                try:
                    bedrooms = int("".join([num for num in line if num.isnumeric()]))
                except:
                    pass
            elif "pièces" in line:
                try:
                    rooms = int("".join([num for num in line if num.isnumeric()]))
                except:
                    pass
            elif "habitable" in line:
                try:
                    size = int(
                        "".join(
                            [num for num in line if num.isnumeric() and num.isascii()]
                        )
                    )
                except:
                    pass
            elif "terrain" in line:
                try:
                    plot = int(
                        "".join(
                            [num for num in line if num.isnumeric() and num.isascii()]
                        )
                    )
                except:
                    pass
                if "ha" in line:
                    plot *= 10000

        # print("Bedrooms:", bedrooms)
        # print("Rooms:", rooms)
        # print("Size:", size, "m²")
        # print("Plot:", plot, "m²")

        # Description
        description = soup.find("div", class_="offreContent").p.get_text().splitlines()
        description = [line for line in description if line]

        # print(description)

        # Photos
        # Finds the links to full res photos for each listing and returns them as a list
        photos = []
        photos_div = soup.find("ul", class_="slider_Mdl")
        # print(photos_div)
        for child in photos_div.descendants:
            if child.name == "img":
                if "bacimmobilier.staticlbi.com" in child["data-src"]:
                    photos.append("https:" + child["data-src"])
        # pprint(photos)

        photos_hosted = photos

        gps = None
        if isinstance(town, str):
            # Check if town is in premade database of GPS locations, if not searches for GPS
            if (postcode + ";" + town.casefold()) in gps_dict:
                gps = gps_dict[postcode + ";" + town.casefold()]
            else:
                try:
                    gps = get_gps(town, postcode)
                except:
                    gps = None

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
        # pprint(listing.__dict__)
        return listing.__dict__

    except Exception as e:
        return f"{url}: {str(e)}"


# test_urls = [
#     "https://www.bac-immobilier.com/vente/11-aude/710-limoux/limoux-centre-ville-maison-50-m2/10078-maison"
# ]

# for test_url in test_urls:
#     get_listing_details(requests.get(test_url), test_url)

# pprint(get_listing_details("https://www.audeimmobilier.com/vente/11-aude/243-bouisse/maison-de-village-renovee-avec-jardin/1215-maison").__dict__)
# get_listing_details("https://www.audeimmobilier.com/vente/11-aude/243-bouisse/maison-de-village-renovee-avec-jardin/1215-maison")

# bac_listings = bac_get_listings()

# with open("api.json", "w", encoding="utf8") as outfile:
#     json.dump(bac_listings, outfile, ensure_ascii=False)

# Time elapsed for Aude Immobilier: 4.56s 47 links without photos
