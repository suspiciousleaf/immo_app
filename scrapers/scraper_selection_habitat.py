import os
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
    print("gps_dictnot found")
    gps_dict = []

try:
    try:
        with open("postcodes_dict.json", "r", encoding="utf8") as infile:
            postcodes_dict = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/postcodes_dict.json", "r", encoding="utf8"
        ) as infile:
            postcodes_dict = json.load(infile)
except:
    postcodes_dict = []

try:
    with open("ville_list_clean.json", "r", encoding="utf8") as infile:
        town_list = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/ville_list_clean.json", "r", encoding="utf8"
    ) as infile:
        town_list = json.load(infile)


def selection_get_listings(host_photos=False):
    t0 = time.perf_counter()
    URL = "https://www.selectionhabitat.com/ajax/ListeBien.php?ope=1&page=1&ListeViewBienForm=text&lieu=D%C2%A411%C2%A4Aude+(11)%C2%A40.7517563608706%C2%A40.0415626093272%C2%A40%7CD%C2%A409%C2%A4Ari%C3%A8ge+(09)%C2%A40.7493157360778%C2%A40.0251932867004%C2%A40%7CD%C2%A466%C2%A4Pyr%C3%A9n%C3%A9es-Orientales+(66)%C2%A40.7435327970408%C2%A40.0443244340435%C2%A40&lieu-alentour=0&langue=fr&MapWidth=100&MapHeight=394&DataConfig=JsConfig.GGMap.Liste&Pagination=0"
    page = requests.get(URL)

    selection_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = selection_soup.find(string=True)
    num_props = int(num_props_div.split("|")[0])
    print("\nSelection Habitat number of listings:", num_props)
    pages = math.ceil(num_props / 10)
    print("Pages:", pages)

    results_pages = [
        f"https://www.selectionhabitat.com/ajax/ListeBien.php?ope=1&page={i}&ListeViewBienForm=text&lieu=D%C2%A411%C2%A4Aude+(11)%C2%A40.7517563608706%C2%A40.0415626093272%C2%A40%7CD%C2%A409%C2%A4Ari%C3%A8ge+(09)%C2%A40.7493157360778%C2%A40.0251932867004%C2%A40%7CD%C2%A466%C2%A4Pyr%C3%A9n%C3%A9es-Orientales+(66)%C2%A40.7435327970408%C2%A40.0443244340435%C2%A40&lieu-alentour=0&langue=fr&MapWidth=100&MapHeight=394&DataConfig=JsConfig.GGMap.Liste&Pagination=0"
        for i in range(1, pages + 1)
    ]
    resp = get_data(results_pages)
    links = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(selection_get_links, (item["response"] for item in resp))
        for result in results:
            links += result

    print("Number of unique listing URLs found:", len(links))

    listings = [
        listing for listing in listings_json if listing["agent"] == "Selection Habitat"
    ]

    links_old = []
    for listing in listings:
        if listing["agent"] == "Selection Habitat":
            links_old.append(listing["link_url"])
    # print("Listings found from prevous scrape:", len(links_old))

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
                    f"{cwd}/static/images/selection/{listing_ref}", ignore_errors=True
                )
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    response_objects = get_data(links_to_scrape)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            get_listing_details,
            (item["response"] for item in response_objects),
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

    if links_to_scrape:
        print(f"Successfully scraped: {counter_success}/{len(links_to_scrape)}")

    if failed_scrape_links:
        print(f"Failed to scrape: {counter_fail}/{len(links_to_scrape)} \nFailed URLs:")
        pprint(failed_scrape_links)

    listings.sort(key=lambda x: x["price"])

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Time elapsed for selection: {time_taken:.2f}s")

    return listings


def selection_get_links(page):
    selection_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in selection_soup.find_all("a"):
        links_raw.add(link.get("href"))
    links_raw.discard(None)
    links = [
        link
        for link in links_raw
        if "https://www.selectionhabitat.com/fr/annonce/" in link
    ]
    # pprint(links)
    return links


def get_listing_details(page, url, host_photos):
    try:
        agent = "Selection Habitat"
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
            elif "Ville" in element:
                town = unidecode(
                    element.casefold()
                    .replace("ville ", "")
                    .replace("-", " ")
                    .replace("proche", "")
                    .strip()
                ).capitalize()
            elif "Pièces" in element:
                try:
                    rooms = int(element.replace("Pièces ", "").strip())
                except:
                    pass
            elif "Chambres" in element:
                try:
                    bedrooms = int(element.replace("Chambres ", "").strip())
                except:
                    pass
            elif "Surface" in element:
                try:
                    size = int(
                        float(element.replace("Surface ", "").replace("m²", "").strip())
                    )  # Float/int used in case of decimals
                except:
                    pass
            elif "Terrain" in element:
                try:
                    if "Hectare(s)" in element:
                        plot = int(
                            float(
                                element.replace("Terrain ", "")
                                .replace("m²", "")
                                .replace("Hectare(s)", "")
                                .strip()
                            )
                            * 10000
                        )
                    else:
                        plot = int(
                            float(
                                element.replace("Terrain ", "")
                                .replace("m²", "")
                                .strip()
                            )
                        )
                except:
                    pass
            elif "Prix" in element:
                price = int("".join([num for num in element if num.isnumeric()]))
            elif "Ref" in element:
                if len(element.replace("Ref ", "").strip()) < 7:
                    ref = element.replace("Ref ", "").strip()

        postcode_div = soup.find("h1", class_="heading1").get_text()
        # This ensures we capture a 5 digit string inside brackets, that begins with either 09, 11, or 66
        regex_pattern = r"\((?=[09|11|66]\d{3})(\d{5})\)"
        postcode = re.search(regex_pattern, postcode_div).group(1)

        if town.casefold() not in town_list:
            try:
                town = postcodes_dict[postcode][0].capitalize()
            except:
                pass

        # print("Type:", types)
        # print("Town:", town)
        # print("Rooms:", rooms)
        # print("Bedrooms:", bedrooms)
        # print("Price:", price)
        # print("Plot:", plot)
        # print("Size:", size)
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

        if host_photos:
            agent_abbr = [i for i in agent_dict if agent_dict[i] == agent][0]

            make_photos_dir(ref, cwd, agent_abbr)

            photos_hosted = []
            photos_failed = []
            i = 0
            failed = 0

            resp = get_data(photos)
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
        # print(e)
        return url


cwd = os.getcwd()

# test_url = "https://www.selectionhabitat.com/fr/annonce/vente-chateau-carcassonne-p-r7-1201218826.html"

# get_listing_details(requests.get(test_url), test_url, False)


# selection_get_links(requests.get(f"https://www.selectionhabitat.com/fr/annonces-immobilieres-p-r12-1.html#ope=1&page=1&ListeViewBienForm=text&lieu=D%C2%A411%C2%A4Aude+(11)%C2%A40.7517563608706%C2%A40.0415626093272%C2%A40|D%C2%A409%C2%A4Ari%C3%A8ge+(09)%C2%A40.7493157360778%C2%A40.0251932867004%C2%A40|D%C2%A466%C2%A4Pyr%C3%A9n%C3%A9es-Orientales+(66)%C2%A40.7435327970408%C2%A40.0443244340435%C2%A40"))

# # selection_get_listings(False)

# selection_listings = selection_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(selection_listings, outfile, ensure_ascii=False)

# Time elapsed for selection: 19.17s 153 listings without photos.
