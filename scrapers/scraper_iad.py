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
from json_search import agent_dict
from models import Listing
from utilities.utilities import get_gps, get_data

headers = {
    "authority": "www.iadfrance.com",
    "cache-control": "max-age=0",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "referer": "https://www.iadfrance.fr/",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9,tr-TR;q=0.8,tr;q=0.7",
}

try:
    try:
        with open("api.json", "r", encoding="utf8") as infile:
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


def iad_immo_get_listings(host_photos=False):
    t0 = time.perf_counter()

    s = requests.Session()
    s.headers.update(headers)

    URL = "https://www.iadfrance.fr/annonces/lavelanet-09300/vente?distance=20&locations%5B0%5D=Locality_43165&locations%5B1%5D=Locality_60619&locations%5B2%5D=Locality_56899&locations%5B3%5D=Locality_60477&locations%5B4%5D=Locality_45768&page=1"
    page = s.get(URL)
    iad_immo_soup = BeautifulSoup(page.content, "html.parser")

    num_props_div = iad_immo_soup.find("p", class_="text-center").get_text()
    num_props = int(num_props_div.split()[5])
    print("\nIAD Immo number of listings:", num_props)
    pages = math.ceil(num_props / 30)
    print("Pages:", pages)

    all_search_pages = [
        f"https://www.iadfrance.fr/annonces/lavelanet-09300/vente?distance=20&locations%5B0%5D=Locality_43165&locations%5B1%5D=Locality_60619&locations%5B2%5D=Locality_56899&locations%5B3%5D=Locality_60477&locations%5B4%5D=Locality_45768&page={i}"
        for i in range(1, pages + 1)
    ]

    links = []

    for link in all_search_pages:
        links += iad_get_links(link, s)

    print("Number of unique listing URLs found:", len(links))

    listings = [
        listing for listing in listings_json if listing["agent"] == "IAD Immobilier"
    ]

    links_old = []
    for listing in listings:
        if listing["agent"] == "IAD Immobilier":
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
                    f"{cwd}/static/images/iad/{listing_ref}", ignore_errors=True
                )
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    resp_to_scrape = get_data(links_to_scrape)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            get_listing_details,
            (item["response"] for item in resp_to_scrape),
            links_to_scrape,
            [host_photos for x in resp_to_scrape],
        )
        for result in results:
            if type(result) == str:
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
    print(f"Time elapsed for IAD Immobilier: {time_taken:.2f}s")

    return listings


def iad_get_links(URL, s):
    page = s.get(URL)
    iad_immo_soup = BeautifulSoup(page.content, "html.parser")

    links = set()

    links_raw_div = iad_immo_soup.find_all("a")
    for line in links_raw_div:
        link = line.get("href")
        if link:
            if "/annonce/" in link:
                links.add("https://www.iadfrance.fr" + line.get("href"))
    return links


def get_listing_details(page, url, host_photos):
    try:
        agent = "IAD Immobilier"
        link_url = url
        soup = BeautifulSoup(page.content, "html.parser")
        # print(soup)
        # Price
        price = int(
            soup.find("div", class_="adPrice text-darkblue text-h3")
            .get_text()
            .replace("€", "")
            .replace(" ", "")
        )

        # These are set to None here in case they aren't included in the listing details
        size = None
        rooms = None
        bedrooms = None
        plot = None

        # Many divs use the below class, so this search is done first to isolate the stat bar
        details_div = soup.find("div", class_="adBadges flex mt-md wrap")
        details_div = details_div.find_all("div", class_="i-badge--label-right")
        for item in details_div:
            if "m²" in item.get_text() and "terrain" not in item.get_text():
                size = int(
                    float(
                        (
                            "".join(
                                [
                                    x
                                    for x in item.get_text()
                                    if x.isnumeric() and x.isascii()
                                ]
                            )
                        )
                    )
                )
            elif "pièces" in item.get_text():
                rooms = int("".join([x for x in item.get_text() if x.isnumeric()]))
            elif "chambre" in item.get_text():
                bedrooms = int("".join([x for x in item.get_text() if x.isnumeric()]))
            elif "m²" in item.get_text() and "terrain" in item.get_text():
                plot = int(
                    float(
                        (
                            "".join(
                                [
                                    x
                                    for x in item.get_text()
                                    if x.isnumeric() and x.isascii()
                                ]
                            )
                        )
                    )
                )
        if plot:
            pass
        else:
            try:
                plot_div = soup.find_all("div", class_="adfeature")
                for result in plot_div:
                    div_contents = result.get_text().strip()
                    if "terrain" in div_contents:
                        # isnumeric and isascii removes all letters and superscript numbers, ie m²
                        plot = int(
                            "".join(
                                [
                                    x
                                    for x in div_contents
                                    if x.isnumeric() and x.isascii()
                                ]
                            )
                        )
                        break
            except:
                pass

        location_div = soup.find("div", class_="addescription")
        location_div = location_div.find("h2", class_="text-h3").get_text()
        postcode = location_div[location_div.index("(") + 1 : location_div.index(")")]

        # Town
        # The town is always written as part of a string as a sub heading, with the town name all upper case, followed by the postcode in brackets. The code below identifies the index of the first upper case character (skipping the first letter of the sentence), and takes the string from there until the first "(" of the postcode as the town name.
        for x in location_div[2:]:
            if x.isupper():
                first_upper_index = location_div[2:].find(x)
                break
        town = (
            unidecode(location_div[first_upper_index + 2 : location_div.find("(") - 1])
            .replace("-", " ")
            .capitalize()
        )

        ref = (
            soup.find("div", class_="mt-md text-grey-2 text-weight-medium")
            .get_text()
            .replace("Réf:", "")
            .strip()
        )
        types = (
            link_url.replace("https://www.iadfrance.fr/annonce/", "")
            .split("-")[0]
            .capitalize()
        )

        # print("Type:", types)
        # print("Town:", town)
        # print("Postcode:", postcode)
        # print("Price:", price, "€")
        # print("ref:", ref)

        # # Get description

        description = soup.find(
            "div", class_="js-translatable-slots-content"
        ).get_text()
        # print(description)

        # # Property details

        # print("Terrain: ", plot, "m²")
        # print("Bedrooms:", bedrooms)
        # print("Rooms:", rooms)
        # print("Size:", size, "m²")

        # Photos

        photos = set()
        photos_div = soup.find_all("a", class_="picturelink")
        for result in photos_div:
            photos.add("https://www.iadfrance.fr" + result.get("href"))
        photos = list(photos)

        # pprint(photos)

        if host_photos:
            agent_abbr = [i for i in agent_dict if agent_dict[i] == agent][0]

            make_photos_dir(ref, cwd, agent_abbr)

            photos_hosted = []
            photos_failed = []
            i = 0
            failed = 0

            with concurrent.futures.ThreadPoolExecutor() as executor:
                response_objects = executor.map(requests.get, (link for link in photos))
                for result in response_objects:
                    try:
                        photos_hosted.append(
                            dl_comp_photo(result, ref, i, cwd, agent_abbr)
                        )
                        i += 1
                    except:
                        photos_failed.append(result.url)
                        print("HTTP status code:", result.status_code, result.url)
                        failed += 1

            if failed:
                print(f"{failed} photos failed to scrape")
                pprint(photos_failed)
        else:
            photos_hosted = photos

        gps = None
        if type(town) == str:
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
        # print(listing.__dict__)
        return listing.__dict__

    except:
        return url


cwd = os.getcwd()

# pprint(
# get_listing_details(requests.get("https://www.iadfrance.fr/annonce/terrain-vente-0-piece-la-cassaigne-435m2/r1216294", headers=headers), "https://www.iadfrance.fr/annonce/terrain-vente-0-piece-la-cassaigne-435m2/r1216294", False)#)
# pprint(get_listing_details("https://immobilier-lavelanet.iad.com/terrain-a-vendre-belesta-5245-m2-pour-lotissement-ideal-investisseurs-ref-33828908").__dict__)

# iad_get_links()

# iad_listings = iad_immo_get_listings(host_photos=False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(iad_listings, outfile, ensure_ascii=False)
