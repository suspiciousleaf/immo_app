import os
import time
import math
import json
import concurrent.futures

from pprint import pprint
import grequests  # This must be imported as it is imported with get_gps, and if requests is imported before grequests it will cause recursion error
import requests
from bs4 import BeautifulSoup
import shutil
from unidecode import unidecode

from utilities.async_image_downloader import make_photos_dir, dl_comp_photo
from json_search import agent_dict
from models import Listing
from utilities.utilities import get_gps, get_data

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
    with open("ville_list_clean.json", "r", encoding="utf8") as infile:
        town_list = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/ville_list_clean.json", "r", encoding="utf8"
    ) as infile:
        town_list = json.load(infile)

try:
    with open("postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/postcodes_dict.json", "r", encoding="utf8"
    ) as infile:
        postcodes_dict = json.load(infile)


def c21_get_listings(host_photos=False):
    t0 = time.perf_counter()

    URL = "https://www.century21.fr/annonces/f/achat-maison-appartement-terrain-parking-immeuble-divers/d-09_ariege-11_aude/?cible=d-11_aude"
    page = requests.get(URL)

    c21_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = c21_soup.find(
        "div",
        class_="tw-w-full md:tw-w-2/3 tw-text-base tw-font-medium tw-leading-none",
    ).get_text()
    # Extracts the digits for number of properties from the returned string
    num_props = int("".join([num for num in str(num_props_div) if num.isnumeric()]))

    print("\nCentury 21 number of listings:", num_props)
    pages = math.ceil(num_props / 20)
    print("Pages:", pages)

    all_search_pages = [
        "https://www.century21.fr/annonces/f/achat-maison-appartement-terrain-parking-immeuble-divers/d-09_ariege-11_aude/"
    ]
    other_search_pages = [
        f"https://www.century21.fr/annonces/f/achat-maison-appartement-terrain-parking-immeuble-divers/d-09_ariege-11_aude/page-{i}/"
        for i in range(2, pages + 1)
    ]
    all_search_pages.extend(other_search_pages)

    links = []
    resp = get_data(all_search_pages)
    for item in resp:
        links += c21_get_links(item["response"])

    print("Number of unique listing URLs found:", len(links))

    listings = [
        listing for listing in listings_json if listing["agent"] == "Century 21"
    ]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Century 21":
            links_old.append(listing["link_url"])
    # print("Listings found from previous scrape:", len(links_old))

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
                    f"{cwd}/static/images/c21/{listing_ref}", ignore_errors=True
                )
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    # Century 21 will block scraping if you request more than 100 urls in a short period of time. Scraping the search pages for urls uses up appro 20 of these, so if there are more than 75 urls to scrape then the program will so them in serial, which is slow enough to not get blocked. This will likely only be when populating a new listings.json. Every other time can be done asynchronously

    if len(links_to_scrape) < 75:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            resp_to_scrape = get_data(links_to_scrape)
            results = executor.map(
                get_listing_details,
                (item["response"] for item in resp_to_scrape),
                links_to_scrape,
                [host_photos for x in links_to_scrape],
            )
            for result in results:
                if isinstance(result, str):
                    failed_scrape_links.append(result)
                    counter_fail += 1
                else:
                    listings.append(result)
                    counter_success += 1
    else:
        for link in links_to_scrape:
            resp_object = requests.get(link)
            result = get_listing_details(resp_object, link, False)
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
    print(f"Time elapsed for Century 21: {time_taken:.2f}s")

    return listings


def c21_get_links(page):
    c21_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in c21_soup.find_all("a"):
        links_raw.add(link.get("href"))
    links_raw.discard(None)
    links = [
        f"https://www.century21.fr{link}"
        for link in links_raw
        if "/trouver_logement/detail/" in link
    ]

    return links


def get_listing_details(page, url, host_photos):
    try:
        agent = "Century 21"
        soup = BeautifulSoup(page.content, "html.parser")
        link_url = url

        # Get type

        types = soup.find_all("span", itemprop="name")
        for item in types:
            if "Achat" in item.get_text():
                if len(item.get_text().replace("Achat", "").strip()) > 1:
                    types = item.get_text().replace("Achat", "").strip()
                    break

        # print("Type:", types)

        # Description

        description_div = soup.find(
            "div", class_="has-formated-text md:tw-pl-9"
        ).strings
        description = []
        for item in description_div:
            if item:
                description.append(item.replace("\n", "").strip())

        # pprint(description)

        # Get location
        try:
            location_div = soup.find("section", class_="l-article__footer")
            # print(location_div)
            location_div = (
                location_div.find(
                    "span",
                    class_="tw-flex tw-flex-col md:tw-block md:tw-text-center md:tw-flex md:tw-flex-col",
                )
                .get_text()
                .splitlines()
            )
            # pprint(location_div)
            for item in location_div:
                if item:
                    num = False
                    for char in item:
                        if char.isnumeric():
                            num = True
                            break
                    if not num:
                        town = unidecode(
                            item.replace("-", " ").replace(" l ", " l'").capitalize()
                        )
                    elif num:
                        postcode = "".join([x for x in item if x.isnumeric()])
        # approx 3% of listings are missing the location bar at the bottom of the page. The section below goes through the description to see if any recognised town names are present, and sets location based on that. It will still miss hyphenated or multi-word town names, but given the rarity of those cases it's not worth coding in.
        except:
            town = None
            postcode = None
            description_joined = (
                " ".join(description)
                .replace(",", " ")
                .replace(".", " ")
                .replace("campagne", "")
                .split()
            )
            for word in description_joined:
                if unidecode(word.casefold()) in town_list:
                    town = unidecode(word.capitalize())
                    postcode = [
                        i
                        for i in postcodes_dict
                        if town.casefold() in postcodes_dict[i]
                    ][0]
                    break

        # print("Postcode:", postcode)
        # print("Town:", town)

        # Get price
        price = int(
            soup.find("div", class_="tw-flex tw-flex-col")
            .get_text()
            .strip()
            .replace("€", "")
            .replace(" ", "")
        )
        # print("Price:", price, "€")

        # Get ref

        ref_div = soup.find("div", class_="c-text-theme-cta").get_text().strip()
        ref = "".join([num for num in ref_div if num.isnumeric()])

        # print("ref:", ref)

        # Get property details

        details_div = (
            soup.find("section", class_="c-the-property-detail-global-view")
            .get_text()
            .replace(" ", "")
            .split("\n")
        )
        # Removes empty strings in list
        details_div = [unidecode(x.strip()) for x in details_div if x]

        try:
            bedrooms = details_div.count("Chambre")
            if bedrooms == 0:
                bedrooms = None
        except:
            bedrooms = None

        # print("Bedrooms:", bedrooms)

        rooms = None
        plot = None
        size = None
        for item in details_div:
            if "Nombredepieces" in item:
                try:
                    rooms = int("".join([x for x in item if x.isnumeric()]))
                except:
                    pass
            elif "Surfaceterrain" in item:
                try:
                    plot = int(
                        float(
                            item.replace("Surfaceterrain : ", "")
                            .replace("m2", "")
                            .replace(",", ".")
                        )
                    )
                except:
                    pass
            elif "Surfacetotale" in item:
                try:
                    size = int(
                        float(
                            item.replace("Surfacetotale : ", "")
                            .replace("m2", "")
                            .replace(",", ".")
                        )
                    )
                except:
                    pass

        # print("Rooms:", rooms)
        # print("Plot:", plot, "m²")
        # print("Size:", size, "m²")

        # Photos
        photos = []
        photos_div = soup.find_all("div", class_="c-the-detail-images__slides__item")

        for item in photos_div:
            photos.append("https://" + item.get("data-src")[2:])

        photos_hosted = photos

        # pprint(photos)

        gps = None
        if postcode and isinstance(town, str):
            # Check if town is in premade database of GPS locations, if not searches for GPS
            if (postcode + ";" + town.casefold()) in gps_dict:
                gps = gps_dict[postcode + ";" + town.casefold()]
            else:
                try:
                    gps = get_gps(town, postcode)
                except:
                    gps = None
        # print(gps)
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
    except Exception as e:
        # print(e)
        return url


cwd = os.getcwd()

# test_url = "https://www.century21.fr/trouver_logement/detail/2947413780/"
# for test_url in problem_list:

# get_listing_details(requests.get(test_url), test_url, False)


# c21_listings = c21_get_listings()

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(c21_listings, outfile, ensure_ascii=False)
