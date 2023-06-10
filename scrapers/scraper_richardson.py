import os
import time
import re
import math
import json
import concurrent.futures

# This must be imported as it is imported with get_gps, and if requests is imported before grequests it will cause recursion error
import grequests
import requests
from pprint import pprint
from bs4 import BeautifulSoup
import shutil
from unidecode import unidecode

from utilities.async_image_downloader import make_photos_dir, dl_comp_photo

# This is necessary for Richardson and Ami, as both have poor quality and inconsistent location data
from utilities.location_fix import fix_location
from json_search import agent_dict
from models import Listing
from utilities.utilities import get_gps, get_data

try:  # listings.json
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

try:  # postcodes_gps_dict
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

try:  # town_list
    with open("ville_list_clean.json", "r", encoding="utf8") as infile:
        town_list = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/ville_list_clean.json", "r", encoding="utf8"
    ) as infile:
        town_list = json.load(infile)

try:  # postcodes_dict
    with open("postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/postcodes_dict.json", "r", encoding="utf8"
    ) as infile:
        postcodes_dict = json.load(infile)

num_dict = {
    "un": "1",
    "deux": "2",
    "trois": "3",
    "quatre": "4",
    "cinq": "5",
    "sept": "7",
    "huit": "8",
    "neuf": "9",
    "dix": "10",
    "t2": "a 1 chambre",
    "t3": "a 2 chambre",
    "t4": "a 3 chambre",
    "t5": "a 4 chambre",
    "t6": "a 5 chambre",
    "t7": "a 6 chambre",
    "t8": "a 7 chambre",
}


# This is necessary with this agent as bedroom info isn't consistently listed. This isn't perfect, but better than nothing
def find_chamb(string):
    string = unidecode(string).casefold()

    # Checks description for instances of numbers as words and replaces with digits
    for key in num_dict.keys():
        string = string.replace(key, num_dict[key])

    # identifies all patterns of "X chambre" and "X xxxx chambre" and returns each X in a list
    pattern = r"(\d+)\s\w*\s*chambre"
    chambres = 0
    matches = re.findall(pattern, string)

    for match in matches:
        chambres += int(match)

    return chambres


def richardson_get_listings(host_photos=False):
    t0 = time.perf_counter()

    richardson_categories = [
        "vente-villa.cgi?000T",
        "vente-propriete.cgi?000T",
        "vente-maison-appartement.cgi?000T",
        "vente-terrain.cgi?000T",
        "investissement.cgi?000T",
        "vente-commerce.cgi?000T",
    ]

    all_search_pages = []

    url_full = [
        "http://www.richardsonimmobilier.com/" + richardson_categories[i]
        for i in range(len(richardson_categories))
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        response_objects = executor.map(requests.get, (link for link in url_full))
        for page in response_objects:
            richardson_soup = BeautifulSoup(page.content, "html.parser")
            num_props_div = richardson_soup.find("td", class_="SIZE3-50").b
            num_props = int(
                "".join([num for num in str(num_props_div) if num.isnumeric()])
            )
            # print("\nRichardson number of listings for category:", num_props)
            pages = math.ceil(num_props / 20)
            # print("Pages:", pages)

            search_pages = [(page.url[:-2] + str(i) + "T") for i in range(pages)]
            for link in search_pages:
                all_search_pages.append(link)

    resp = get_data(all_search_pages)
    links_inc_duplicates = []
    for item in resp:
        links_inc_duplicates += richardson_get_links(item["response"])

    links_inc_sold = []
    unique_listing_set = set()
    # This code checks for duplicate properties that appear in multiple categories
    for i in range(len(links_inc_duplicates)):
        if links_inc_duplicates[i][-4:] not in unique_listing_set:
            links_inc_sold.append(links_inc_duplicates[i])
        unique_listing_set.add(links_inc_duplicates[i][-4:])

    # The line below removes and listings which are marked "Sold", "Sous compromis", etc
    links = []
    resp_to_scrape = []
    resp_sold = get_data(links_inc_sold)
    for object in resp_sold:
        if (
            bool(
                (
                    BeautifulSoup(object["response"].content, "html.parser").find(
                        "span", class_="SIZE4"
                    )
                )
            )
            == False
        ):
            links.append(object["link"])
            # Save response objects to parse, to avoid scraping twice
            resp_to_scrape.append(object)
    print("\nRichardson number of available listings found:", len(links))

    try:
        listings = [
            listing
            for listing in listings_json
            if listing["agent"] == "Richardson Immobilier"
        ]
    except:
        listings = []

    links_old = []
    for listing in listings:
        if listing["agent"] == "Richardson Immobilier":
            links_old.append(listing["link_url"])

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
                shutil.rmtree(
                    f"{cwd}/static/images/richardson/{listing_ref}", ignore_errors=True
                )
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            get_listing_details,
            (item["response"] for item in resp_to_scrape),
            links_to_scrape,
            [host_photos for x in links_to_scrape],
        )
        for result in results:
            if type(result) == str:
                failed_scrape_links.append(result)
                counter_fail += 1
            else:
                listings.append(fix_location(result))
                counter_success += 1

    if links_to_scrape:
        print(f"Successfully scraped: {counter_success}/{len(links_to_scrape)}")

    if failed_scrape_links:
        print(f"Failed to scrape: {counter_fail}/{len(links_to_scrape)} \nFailed URLs:")
        pprint(failed_scrape_links)

    listings.sort(key=lambda x: x["price"])

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Time elapsed for Richardson Immobilier: {time_taken:.2f}s")

    return listings


def richardson_get_links(page):
    richardson_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = []
    for link in richardson_soup.find_all("a"):
        links_raw.append("http://www.richardsonimmobilier.com/" + link.get("href"))
    links = [link for link in links_raw if len(link) > 70]

    return links


def get_listing_details(page, url, host_photos):
    try:
        agent = "Richardson Immobilier"
        soup = BeautifulSoup(page.content, "html.parser", from_encoding="UTF-8")
        link_url = url

        # Get type
        # print(URL)

        prop_type_div = soup.find("td", class_="SIZE3-50").b.contents[0]
        # print(prop_type_div)
        types = str(prop_type_div).split()[0]
        # print("Type:", types)

        # Get ref
        ref = "".join([num for num in str(prop_type_div) if num.isdigit()])
        # print("Ref:", ref)

        # # Get location
        try:
            town = unidecode(
                str(soup.find("div", class_="SIZE3-50").b.contents[0])
                .replace("EXCLUSIF ", "")
                .replace("SECTEUR ", "")
                .replace("St", "saint")
                .capitalize()
            )
        except:
            town = None
        postcode = None
        if town:
            try:
                if town.casefold() in town_list:
                    postcode = [
                        key
                        for key in postcodes_dict.keys()
                        if town.casefold() in postcodes_dict[key]
                    ][0]
            except:
                pass

        # print(town)
        # print(postcode)
        # print(ref)

        # Get price
        price_div = soup.find("span", class_="SIZE4-50").b.contents[0]
        price = int("".join([num for num in str(price_div) if num.isdigit()]))
        # print("Price:", price, "€")

        # Get property details

        description = soup.find("span", class_="SIZE35-51").get_text()
        # print(description, "\n\n")

        # Bedroom information not listed, sometimes written in description
        try:
            bedrooms = find_chamb(description)
            if bedrooms == 0:
                bedrooms = None
        except:
            bedrooms = None
        # print(bedrooms)

        # Rooms
        # Data stored in a table, code below finds the whole table, turns everything with b tag into a list, and removes <b> and <\b>
        areas_div = soup.find("table", class_="W100C0")
        areas_list = list(areas_div.find_all("b"))
        areas_list = [
            str(element).replace("<b>", "").replace("</b>", "")
            for element in areas_list
        ]
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

        photos_div = str(soup.find_all("td", class_="CENTERT")).split()
        # print(photos_div)
        photos = [
            "http://www.richardsonimmobilier.com/"
            + entry.replace('"', "").replace("src=", "")
            for entry in photos_div
            if "src=" in entry
        ]
        # print(photos)
        if photos:  # len(photos) > 0:
            pass
        else:
            photos_div = str(soup.find_all("img", class_="photomH")).split()
            # print(photos_div)
            photos = [
                "http://www.richardsonimmobilier.com/"
                + entry.replace('"', "").replace("src=", "")
                for entry in photos_div
                if "src=" in entry
            ]

            if photos:  # len(photos) > 0:
                pass
            else:
                photos_div = str(soup.find_all("img", class_="photomrH")).split()
                photos = [
                    "http://www.richardsonimmobilier.com/"
                    + entry.replace('"', "").replace("src=", "")
                    for entry in photos_div
                    if "src=" in entry
                ]
        photos = sorted(list(set(photos)))
        # print("\n", link_url, " ")
        # pprint(photos)

        if host_photos:
            agent_abbr = [i for i in agent_dict if agent_dict[i] == agent][0]

            make_photos_dir(ref, cwd, agent_abbr)

            photos_hosted = []
            photos_failed = []
            i = 0
            failed = 0

            resp = get_data(photos, header=False)
            for item in resp:
                try:
                    photos_hosted.append(
                        dl_comp_photo(item["response"], ref, i, cwd, agent_abbr)
                    )
                    i += 1
                except:
                    photos_failed.append(item["link"])
                    failed += 1

            if failed:
                print(f"{failed} photos failed to scrape")
                pprint(photos_failed)
        else:
            photos_hosted = photos

        gps = None
        if type(postcode) == str and type(town) == str:
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
        return listing.__dict__

    except:
        return url


cwd = os.getcwd()

# pprint(richardson_get_links(1))

# failed_urls = [
#     "http://www.richardsonimmobilier.com/vente-maison-Haute-Vallee-3750.cgi?00518LQUI3750"
# ]

# for test_url in failed_urls:
#     get_listing_details(requests.get(test_url), test_url, False)

# richardson_listings = richardson_get_listings()

# with open("api.json", "w", encoding='utf8') as outfile:
#     json.dump(richardson_listings, outfile, ensure_ascii=False)

# Time elapsed for Richardson Immobilier: 10.44s 104 listings excluding photos
