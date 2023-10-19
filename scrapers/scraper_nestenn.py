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
from utilities.agent_dict import agent_dict

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


def nestenn_immo_get_listings(old_listing_urls_dict, host_photos=False):
    t0 = time.perf_counter()

    URL = "https://immobilier-lavelanet.nestenn.com/?action=listing&transaction=acheter&sort=prix&page=1"
    page = requests.get(URL)

    nestenn_immo_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = nestenn_immo_soup.find("div", class_="mt_5rem").get_text()
    num_props = int("".join([num for num in num_props_div if num.isnumeric()]))
    print("\nNestenn Immo number of listings:", num_props)
    pages = math.ceil(num_props / 30)
    print("Pages:", pages)

    all_search_pages = [
        f"https://immobilier-lavelanet.nestenn.com/?action=listing&transaction=acheter&sort=prix&page={i}"
        for i in range(1, pages + 1)
    ]

    links = []
    resp = get_data(all_search_pages)
    for item in resp:
        links += nestenn_get_links(item["response"])

    print("Number of unique listing URLs found:", len(links))
    # pprint(links)

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
                    f"{cwd}/static/images/nestenn/{listing_ref}", ignore_errors=True
                )
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    listings = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        response_objects = executor.map(
            requests.get, (link for link in links_to_scrape)
        )
        results = executor.map(
            get_listing_details,
            (item for item in response_objects),
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
    print(f"Time elapsed for Nestenn: {time_taken:.2f}s")

    return {"listings": listings, "urls_to_remove": links_dead}


def nestenn_get_links(page):
    nestenn_immo_soup = BeautifulSoup(page.content, "html.parser")

    links = []

    links_raw_div = nestenn_immo_soup.find("div", id="gridPropertyOnly")
    links_raw = links_raw_div.find_all("div", class_="property_title")
    for link in links_raw:
        if "Vendu" in link.get_text():
            pass
        else:
            links.append(link.a.get("href"))

    return links


def get_listing_details(page, url, host_photos):
    try:
        agent = "Nestenn"
        link_url = url
        soup = BeautifulSoup(page.content, "html.parser")

        # Get several details from contact form hidden values

        details_div = soup.find("div", class_="box_emailing")
        details_div_2 = details_div.find_all("input")
        # pprint(details_div_2)
        for line in details_div_2:
            if line.get("name") == "type_bien":
                types = line.get("value")
            elif line.get("name") == "prix":
                price = int(line.get("value"))
            elif line.get("name") == "localisation":
                postcode = line.get("value")[: line.get("value").find(" ")]
                town = unidecode(
                    line.get("value")[line.get("value").find(" ") + 1 :]
                    .capitalize()
                    .replace("d olmes", "d'olmes")
                )

        ref = soup.find("div", class_="property_ref").get_text(strip=True)[-4:]

        # print("Type:", types)
        # print("Town:", town)
        # print("Postcode:", postcode)
        # print("Price:", price, "€")
        # print("ref:", ref)

        # Get description

        description_raw = soup.find("p", class_="square_text_p").get_text().splitlines()
        description = [string.strip() for string in description_raw if string.strip()]

        # print(description)

        # Property details
        bedrooms = None
        rooms = None
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
                plot = int(
                    "".join([num for num in plot if num.isnumeric() and num.isascii()])
                )

        # print("Terrain: ", plot, "m²")
        # print("Bedrooms:", bedrooms)
        # print("Rooms:", rooms)
        # print("Size:", size, "m²")

        # Photos
        # Finds the links to full res photos for each listing which are stored as a single string (sep ";"), splits and returns them as a list. Removes empty string at the end of the list

        photos_div = soup.find("section", class_="section_bien_photo")
        photos_raw_list = photos_div.get("data-photos").split(";")
        photos = [photo for photo in photos_raw_list if len(photo) > 10]
        # pprint(photos)

        if host_photos:
            agent_abbr = [i for i in agent_dict if agent_dict[i] == agent][0]

            make_photos_dir(ref, cwd, agent_abbr)

            photos_hosted = []
            photos_failed = []
            i = 0
            failed = 0

            # Time elapsed for Nestenn: 142.65392637252808 with rate limiting to reduce server blocking
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response_objects = executor.map(requests.get, (link for link in photos))
                for result in response_objects:
                    # time.sleep(0.6)   Uncomment when running with no listings fil and photos present to reduce errors, also below comment section
                    try:
                        photos_hosted.append(
                            dl_comp_photo(result, ref, i, cwd, agent_abbr)
                        )
                        i += 1
                    except:
                        # time.sleep(1)
                        # try:
                        #     photos_hosted.append(dl_comp_photo(result, ref, i, cwd, agent_abbr))
                        # except:
                        photos_failed.append(result.url)
                        print("HTTP status code:", result.status_code, result.url)
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

# get_listing_details(requests.get("https://immobilier-lavelanet.nestenn.com/appartement-en-duplex-avec-terrasse-sans-vis-a-vis-ref-38307147"), "https://immobilier-lavelanet.nestenn.com/appartement-en-duplex-avec-terrasse-sans-vis-a-vis-ref-38307147")
# pprint(get_listing_details("https://immobilier-lavelanet.nestenn.com/terrain-a-vendre-belesta-5245-m2-pour-lotissement-ideal-investisseurs-ref-33828908").__dict__)


# nestenn_immo_get_listings()
# nestenn_immo_get_links(1)

# nestenn_listings = nestenn_immo_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(nestenn_listings, outfile, ensure_ascii=False)
