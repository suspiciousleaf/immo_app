import os
import time
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
from models import Listing
from utilities.utility_holder import get_gps, get_data


try:
    with open("static/data/agent_mapping.json", "r", encoding="utf8") as infile:
        agent_dict = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/static/data/agent_mapping.json",
        "r",
        encoding="utf8",
    ) as infile:
        agent_dict = json.load(infile)

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
    print("gps_dict not found")
    gps_dict = []


def aude_immo_get_listings(old_listing_urls_dict, host_photos=False):
    t0 = time.perf_counter()

    URL = "https://www.audeimmobilier.com/recherche/1"
    page = requests.get(URL)

    aude_immo_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = aude_immo_soup.find("div", class_="resultatFounded")
    # Extracts the digits for number of properties from the HTML
    num_props = int("".join([num for num in str(num_props_div) if num.isnumeric()]))

    print("\nAude Immobilier number of listings:", num_props)
    pages = math.ceil(num_props / 10)
    print("Pages:", pages)

    all_search_pages = [
        f"https://www.audeimmobilier.com/recherche/{i}" for i in range(1, pages + 1)
    ]

    links = []
    resp = get_data(all_search_pages)
    for item in resp:
        links += aude_immo_get_links(item["response"])

    print("Number of unique listing URLs found:", len(links))

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
                    f"{cwd}/static/images/aude/{listing_ref}", ignore_errors=True
                )
            except:
                pass

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

    t1 = time.perf_counter()

    time_taken = t1 - t0
    print(f"Time elapsed for Aude Immobilier: {time_taken:.2f}s")

    return {"listings": listings, "urls_to_remove": links_dead}


def aude_immo_get_links(page):
    aude_immo_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in aude_immo_soup.find_all("a"):
        links_raw.add(link.get("href"))

    links_raw.discard(None)
    links = [
        link for link in links_raw if "https://www.audeimmobilier.com/vente/" in link
    ]

    return links


def get_listing_details(page, url, host_photos):
    try:
        agent = "Aude Immobilier"
        link_url = url
        soup = BeautifulSoup(page.content, "html.parser")

        # Get type

        prop_type_div = soup.find("li", class_="container_ImgSlider_Mdl")
        for child in prop_type_div.descendants:
            if child.name == "img":
                types = child["alt"].split()[1].strip(",")

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
        prop_ref_div = soup.find_all("p", class_="ref")
        prop_ref = "".join([num for num in str(prop_ref_div) if num.isdigit()])
        ref = prop_ref

        # print("ref:", ref)

        # # Get property details
        # # This returns a whole chunk of text for the property specs that gets separated to find the number of bedrooms, rooms, house size and land size. It's done in a janky way that Amy will hate

        # details_div = str(soup.find('div', id="dataContent"))
        # print(details_div)
        # details = details_div.split("\n")
        # pprint(details)

        details_div = soup.find("div", id="dataContent").get_text()
        details = details_div.splitlines()
        # pprint(details)

        # Chambres
        bedrooms = "".join([line for line in details if "chambre(s)" in line])
        bedrooms = "".join([num for num in bedrooms if num.isnumeric()])

        if bedrooms.isnumeric():
            bedrooms = int(bedrooms)
        else:
            bedrooms = None
        # print("Bedrooms:", bedrooms)

        # Rooms
        rooms = "".join([rooms for rooms in details if "pièces" in rooms])
        rooms = "".join([num for num in rooms if num.isnumeric()])

        if rooms.isnumeric():
            rooms = int(rooms)
        else:
            rooms = None
        # print("Rooms:", rooms)

        # # Plot size

        plot = "".join([plot for plot in details if "surface terrain" in plot])
        plot = "".join([plot for plot in plot if plot.isnumeric()])
        plot = plot[:-1]

        if plot.isnumeric():
            plot = int(plot)
        else:
            plot = None
        # print("Plot:", plot, "m²")

        # #Property size
        size = str([size for size in details if "Surface habitable (m²)" in size])
        try:
            #  This converts to "." decimal notation, and rounds to an int
            size = round(float(size[size.index(":") + 2 : -5].replace(",", ".")))
            # print(size)
        except:
            size = None

        # print("Size:", size, "m²")

        # Description
        description = [soup.find("div", class_="offreContent").p.contents[0]]

        # print(description)

        # Photos
        # Finds the links to full res photos for each listing and returns them as a list
        photos = []
        photos_div = soup.find("ul", class_="slider_Mdl")
        # print(photos_div)
        for child in photos_div.descendants:
            if child.name == "img":
                photos.append("https:" + child["data-src"])
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

# test_urls = [
#     "https://www.audeimmobilier.com/vente/11-aude/1-limoux/propriete-de-41-ha-avec-superbe-vue/1258-propriete"
# ]

# for test_url in test_urls:
#     get_listing_details(requests.get(test_url), test_url, False)

# pprint(get_listing_details("https://www.audeimmobilier.com/vente/11-aude/243-bouisse/maison-de-village-renovee-avec-jardin/1215-maison").__dict__)
# get_listing_details("https://www.audeimmobilier.com/vente/11-aude/243-bouisse/maison-de-village-renovee-avec-jardin/1215-maison")

# aude_immo_listings = aude_immo_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf8") as outfile:
#     json.dump(aude_immo_listings, outfile, ensure_ascii=False)

# Time elapsed for Aude Immobilier: 4.56s 47 links without photos
