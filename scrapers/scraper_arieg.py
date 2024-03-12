import time
import math
import json
import concurrent.futures
import re

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
        with open("static/data/town_gps_mapping.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/static/data/town_gps_mapping.json",
            "r",
            encoding="utf8",
        ) as infile:
            gps_dict = json.load(infile)
except:
    print("gps_dictnot found")
    gps_dict = []

try:
    try:
        with open("static/data/postcode_mapping.json", "r", encoding="utf8") as infile:
            postcodes_dict = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/static/data/postcode_mapping.json",
            "r",
            encoding="utf8",
        ) as infile:
            postcodes_dict = json.load(infile)
except:
    postcodes_dict = []

try:
    with open("static/data/ville_list_clean.json", "r", encoding="utf8") as infile:
        town_list = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/static/data/ville_list_clean.json",
        "r",
        encoding="utf8",
    ) as infile:
        town_list = json.load(infile)


def arieg_get_listings(old_listing_urls_dict):
    t0 = time.perf_counter()
    URL = "https://www.ariegimmo.com/fr/liste.htm?page=1&TypeModeListeForm=text&tdp=all&lieu-alentour=0#page=1&TypeModeListeForm=text&tdp=all"
    page = requests.get(URL)

    arieg_soup = BeautifulSoup(page.content, "html.parser")
    num_props = int(arieg_soup.find("span", class_="NbBien").get_text())
    print("\nArieg'Immo number of listings:", num_props)
    pages = math.ceil(num_props / 12)
    print("Pages:", pages)

    results_pages = [
        f"https://www.ariegimmo.com/fr/liste.htm?page={i}&TypeModeListeForm=text&tdp=all&lieu-alentour=0#page={i}&TypeModeListeForm=text&tdp=all"
        for i in range(1, pages + 1)
    ]
    resp = get_data(results_pages)
    links = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(arieg_get_links, (item["response"] for item in resp))
        for result in results:
            links += result

    print("Number of unique listing URLs found:", len(links))

    links_old = set(old_listing_urls_dict.keys())

    links_to_scrape = [link for link in links if link not in links_old]
    print("New listings to add:", len(links_to_scrape))
    # pprint(links_to_scrape)
    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))
    # pprint(links_dead)

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    listings = []

    response_objects = get_data(links_to_scrape)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            get_listing_details,
            (item["response"] for item in response_objects),
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

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Time elapsed for Arieg'Immo: {time_taken:.2f}s")

    return {"listings": listings, "urls_to_remove": links_dead}


def arieg_get_links(page):
    arieg_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in arieg_soup.find_all("a"):
        links_raw.add(link.get("href"))
    links_raw.discard(None)
    links = [
        link for link in links_raw if "https://www.ariegimmo.com/fr/detail" in link
    ]
    # pprint(links)
    return links


def get_listing_details(page, url):
    try:
        agent = "Arieg'Immo"
        soup = BeautifulSoup(page.content, "html.parser")
        link_url = url

        # print("\n\nNext property\n")

        details_list = []
        details_div = soup.find("div", class_="detail-bien-specs")
        details_div = details_div.find_all("li")
        details_list = [element.get_text() for element in details_div]
        # pprint(details_list)

        town = None
        rooms = None
        bedrooms = None
        plot = None
        size = None
        postcode = None
        ref = None
        types = None

        for element in details_list:
            if "Type" in element:
                types = (
                    element.replace("Type ", "")
                    .replace("agricole", "")
                    .replace("constructible", "")
                    .strip()
                )
                if types == "Type":
                    types = None
            elif "Pièce(s)" in element:
                try:
                    rooms = int("".join([num for num in element if num.isnumeric()]))
                except:
                    pass
            elif "Chambre(s)" in element:
                try:
                    bedrooms = int("".join([num for num in element if num.isnumeric()]))
                except:
                    pass
            elif "Surface" in element:
                try:
                    size = int(
                        float(element.replace("Surface", "").replace("m²", "").strip())
                    )  # Float/int used in case of decimals
                except:
                    pass
            elif "Terrain" in element:
                try:
                    if "Hectare(s)" in element:
                        plot = int(
                            float(
                                element.replace("Hectare(s)", "")
                                .replace("Terrain", "")
                                .strip()
                            )
                            * 10000
                        )
                    else:
                        plot = int(
                            float(
                                element.replace("Terrain", "").replace("m²", "").strip()
                            )
                        )
                except:
                    pass

        location_div = soup.find("h2", class_="detail-bien-ville").get_text()
        # This ensures we capture a 5 digit string inside brackets, that begins with either 09, 11, or 66
        regex_pattern = r"\((?=[09|11|66]\d{3})(\d{5})\)"
        postcode = re.search(regex_pattern, location_div).group(1)

        town = (
            unidecode(location_div[: location_div.find("(")].capitalize())
            .strip()
            .replace("-", " ")
        )

        if town.casefold() not in town_list:
            try:
                town = postcodes_dict[postcode][0].capitalize()
            except:
                pass

        price_raw = soup.find("div", "detail-bien-prix").get_text()
        price = int("".join([num for num in price_raw if num.isnumeric()]))

        types = soup.find("h2", class_="detail-bien-type").get_text()

        ref_raw = soup.findAll("div", class_="detail-bien-ref")
        for elem in ref_raw:
            if len(elem.get_text(strip=True).replace("Réf.", "")) < 9:
                ref = elem.get_text(strip=True).replace("Réf.", "")

        # print("Type:", types)
        # print("Town:", town)
        # print("Rooms:", rooms)
        # print("Bedrooms:", bedrooms)
        # print("Price:", price)
        # print("Plot:", plot, "m²")
        # print("Size:", size, "m²")
        # print("Ref:", ref)
        # print("Postcode:", postcode)

        # Description

        description = None
        description_div = soup.find("div", class_="detail-bien-desc-content")
        description_div = description_div.find_all("p")
        for desc in description_div:
            if len(desc.get_text()) > 200:
                description_raw = desc.get_text().replace("\r", "").splitlines()
                description = [
                    string.strip() for string in description_raw if string.strip()
                ]
                break
        # pprint(description)

        # Photos
        # Finds the links to full res photos for each listing, removes the "amp;" so the links work, and returns them as a list

        photos_div = []
        for link in soup.find_all("img", class_="photo-big"):
            photos_div.append(link)
        photos_div = [str(link) for link in photos_div]
        photos = [link[link.find("data-src=") + 10 :] for link in photos_div]
        photos = [link.replace("amp;", "") for link in photos]
        photos = [link.replace('"/>', "") for link in photos]
        # pprint(photos)

        photos_hosted = photos

        gps = None
        if isinstance(town, str):
            try:
                # Check if town is in premade database of GPS locations, if not searches for GPS
                if (postcode + ";" + town.casefold()) in gps_dict:
                    gps = gps_dict[postcode + ";" + town.casefold()]
            except:
                pass
            if (postcode + ";" + town.casefold()) not in gps_dict:
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


# test_url = "https://www.ariegimmo.com/fr/detail.htm?cle=0900780048&monnaie=2"

# get_listing_details(requests.get(test_url), test_url)


# arieg_listings = arieg_get_listings()

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(arieg_listings, outfile, ensure_ascii=False)
