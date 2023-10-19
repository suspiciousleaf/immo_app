import os
import time
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
from models import Listing
from utilities.utility_holder import get_gps, get_data, agent_dict

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


def europe_sud_get_listings(old_listing_urls_dict, host_photos=False):
    t0 = time.perf_counter()

    search_pages = [
        f"https://www.europe-sud-immobilier.com/a-vendre/{i}" for i in range(1, 15)
    ]
    response_objects = get_data(search_pages)
    links = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            europe_sud_get_links, (item["response"] for item in response_objects)
        )
        for result in results:
            links += result

    # Used to remove duplicates if present
    links = list(set(links))

    print("\nEurope Sud Immobilier unique listing URLs found:", len(links))

    links_old = set(old_listing_urls_dict.keys())

    links_to_scrape = [link for link in links if link not in links_old]
    print("New listings to add:", len(links_to_scrape))
    # pprint(links_to_scrape)
    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))
    # pprint(links_dead)

    listing_photos_to_delete_local = []

    if links_dead and host_photos:
        for link in links_dead:
            listing_photos_to_delete_local.append(old_listing_urls_dict[link])

        for listing_ref in listing_photos_to_delete_local:
            try:
                shutil.rmtree(
                    f"{cwd}/static/images/europe/{listing_ref}", ignore_errors=True
                )
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    if links_to_scrape:
        resp_to_scrape = get_data(links_to_scrape)

        listings = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(
                get_listing_details,
                (item["response"] for item in resp_to_scrape),
                links_to_scrape,
                [host_photos for x in resp_to_scrape],
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
    print(f"Time elapsed for Europe Sud Immobilier: {time_taken:.2f}s")

    return {"listings": listings, "urls_to_remove": links_dead}


def europe_sud_get_links(page):
    europe_sud_soup = BeautifulSoup(page.content, "html.parser")
    links = [
        "https://www.europe-sud-immobilier.com" + link.get("href")
        for link in europe_sud_soup.find_all("a")
        if link.get("href")[1:5].isnumeric()
    ]

    return links


def get_listing_details(page, url, host_photos):
    try:
        agent = "Europe Sud Immobilier"
        link_url = url
        soup = BeautifulSoup(page.content, "html.parser")

        # Get type

        prop_type_div = soup.find("h2").get_text().split("-")[0]
        # This will capture everything until the first number
        type_index = re.search(r"\d", prop_type_div).start()
        types = prop_type_div[:type_index].strip()
        # print("\nType:", types)

        # Get location
        town_div = soup.find("ol", class_="breadcrumb")
        town_div = town_div.find_all("li")
        for item in town_div:
            if "ville" in str(item):
                town = unidecode(item.get_text().replace("-", " ")).capitalize()

        # Description
        description_raw = soup.find("p", itemprop="description").get_text().splitlines()
        description = [string.strip() for string in description_raw if string.strip()]
        # pprint(description)

        postcode_div = soup.find("h2").get_text()
        # The pattern below will identify a string of 5 numbers inside brackets that begins with any of the 5 chosen groups. Group 1 then returns the whole string of numbers
        regex_pattern = r"\((?=[09|11|66|31|34]\d{3})(\d{5})\)"
        postcode = re.search(regex_pattern, postcode_div).group(1)
        # print("Town:", town)
        # print("Postcode:", postcode)

        # Get price
        price_div = soup.find("span", itemprop="price").get_text()
        price = int("".join([num for num in str(price_div) if num.isdigit()]))
        # print("Price:", price, "€")

        # Get ref
        prop_ref_div = soup.find("span", itemprop="productID").get_text()
        ref = prop_ref_div.replace("Ref ", "")

        # print("Ref:", ref)

        # # # Get property details

        details_div = soup.find("div", id="dataContent")
        details = details_div.find_all("p", class_="data")
        # pprint(details_div)

        # Chambres
        bedrooms = "".join(
            [beds.get_text() for beds in details if "chambre(s)" in str(beds)]
        )
        bedrooms = "".join([num for num in bedrooms if num.isnumeric()])

        if bedrooms.isnumeric():
            bedrooms = int(bedrooms)
        else:
            bedrooms = None
        # print("Bedrooms:", bedrooms)

        # # Rooms
        rooms = "".join(
            [rooms.get_text() for rooms in details if "pièces" in str(rooms)]
        )
        rooms = "".join([num for num in rooms if num.isnumeric()])

        if rooms.isnumeric():
            rooms = int(rooms)
        else:
            rooms = None
        # print("Rooms:", rooms)

        # Property size
        try:
            size_raw = "".join(
                [
                    size.get_text().replace("Surface habitable (m²)", "")
                    for size in details
                    if "Surface habitable (m²)" in size.get_text()
                ]
            )
            size_raw = size_raw.replace("\n", "").replace("m²", "").strip()
            if "," in size_raw:
                size = int(float(size_raw.replace(",", ".")))
            else:
                size = int(size_raw)
        except:
            size = None
        # print("Size:", size, "m²")

        # Plot size

        plot = None
        try:
            plot_pattern = (
                r"\b(\d+(?:[\., ]\d+)*\s*(?:h(?:ectares)?|m2|m²|a(?:r|re)?|ca))\b"
            )
            plot_string_list = description.split(".")
            for string in plot_string_list:
                if ("terrain" or "parc") in string.casefold():
                    match = re.search(plot_pattern, string.casefold())
                    if match:
                        plot_raw = match.group(1)
                        if "m2" or "m²" in plot_raw:
                            plot = plot_raw.replace("m2", "").replace("m²", "")
                            plot = int("".join([x for x in plot if x.isnumeric()]))
                        if "h" in plot_raw:
                            plot = (
                                int("".join([x for x in plot_raw if x.isnumeric()]))
                                * 10000
                            )
                    break
        except:
            pass
        if plot == size:
            plot = None
        if plot:
            if size:
                if plot < size:
                    plot = None
        # print("Plot:", plot, "m²")

        # print(description)

        # Photos
        # Finds the links to full res photos for each listing and returns them as a list
        photos = []
        photos_div = soup.find("ul", class_="imageGallery")
        # print(photos_div)
        for child in photos_div.descendants:
            if child.name == "img":
                photos.append("https:" + child["src"])
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
    except Exception as e:
        return f"{url}: {str(e)}"


cwd = os.getcwd()

# get_listing_details(
#     requests.get(
#         "https://www.europe-sud-immobilier.com/1786-chateau-de-caractere.html"
#     ),
#     "https://www.europe-sud-immobilier.com/1786-chateau-de-caractere.html",
#     False,
# )

# europe_sud_listings = europe_sud_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(europe_sud_listings, outfile, ensure_ascii=False)

# Time elapsed for Europe Sud Immobilier: 7.57s 86 listings without photos
