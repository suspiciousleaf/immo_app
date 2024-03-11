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
    with open("static/data/agents.json", "r", encoding="utf8") as infile:
        agent_dict = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/static/data/agents.json", "r", encoding="utf8"
    ) as infile:
        agent_dict = json.load(infile)

try:
    try:
        with open(
            "static/data/postcodes_gps_dict.json", "r", encoding="utf8"
        ) as infile:
            gps_dict = json.load(infile)
    except:
        with open(
            "/home/suspiciousleaf/immo_app/static/data/postcodes_gps_dict.json",
            "r",
            encoding="utf8",
        ) as infile:
            gps_dict = json.load(infile)
except:
    print("gps_dict not found")
    gps_dict = []


def arthur_immo_get_listings(old_listing_urls_dict, sold_url_list, host_photos=False):
    t0 = time.perf_counter()

    URL = "https://www.lavelanet-arthurimmo.com/recherche,basic.htm?transactions=acheter&page=1"
    page = requests.get(URL)

    arthur_immo_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = arthur_immo_soup.find("div", class_="font-semibold").contents
    # Extracts the digits for number of properties from the HTML
    num_props = int("".join([num for num in str(num_props_div) if num.isnumeric()]))

    print("\nArthur Immobilier number of listings:", num_props)
    pages = math.ceil(num_props / 15)
    print("Pages:", pages)

    all_search_pages = [
        f"https://www.lavelanet-arthurimmo.com/recherche,basic.htm?transactions=acheter&page={i}"
        for i in range(1, pages + 1)
    ]

    links = []
    resp = get_data(all_search_pages)
    for item in resp:
        links += arthur_immo_get_links(item["response"])

    links = [link for link in links if link not in sold_url_list]

    print("Number of unique listing URLs found:", len(links))

    links_old = set(old_listing_urls_dict.keys())

    # print("Listings found from prevous scrape:", len(links_old))

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
                    f"{cwd}/static/images/arthur/{listing_ref}", ignore_errors=True
                )
            except:
                pass

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    listings = []

    resp_to_scrape = get_data(links_to_scrape)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            get_listing_details,
            (item["response"] for item in resp_to_scrape),
            links_to_scrape,
            [host_photos for _ in resp_to_scrape],
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
    print(f"Time elapsed for Arthur Immo: {time_taken:.2f}s")

    return {"listings": listings, "urls_to_remove": links_dead}


def arthur_immo_get_links(page):
    arthur_immo_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in arthur_immo_soup.find_all("a"):
        links_raw.add(link.get("href"))

    links_raw.discard(None)
    links = [
        link
        for link in links_raw
        if "https://www.lavelanet-arthurimmo.com/annonces/achat/" in link
    ]

    return links


def get_photos(page):
    """Returns a list of image urls for the listing, scraped from a different page to the main listing

    Args:
        page (response object from listing request)

    Returns:
        images(list)
    """
    parent_url = page.url
    photo_page_url = parent_url.replace(".htm", "/photos.htm")
    photo_page = requests.get(photo_page_url)
    soup = BeautifulSoup(photo_page.content, "html.parser")

    images_raw = soup.find_all("img")
    images = []
    for image in images_raw:
        image_url = image.get("src")
        if (
            "media.studio" in image_url
            and "width" not in image_url
            and image_url not in images
        ):
            images.append(image_url)

    return images


def get_listing_details(page, url, host_photos):
    try:
        agent = "Arthur Immo"
        link_url = url
        soup = BeautifulSoup(page.content, "html.parser")

        # Get type

        parent_ul = soup.find("ul", class_="lg:flex")
        find_li = parent_ul.find_all("li", class_=None, recursive=False)
        find_li_clean = [
            str(line).replace("<li>", "").replace("</li>", "") for line in find_li
        ]
        correct_line = [line for line in find_li_clean if line.find("href") == -1][0]

        types = correct_line.split()[0]

        postcode = correct_line.split()[-1][1:-1]
        # print("Postcode:", postcode)

        # Identifies a line in find_li that contains the town and postcode as a string, and removes the postcode
        for line in find_li:
            if line.a:
                if postcode in str(line.a):
                    postcode_line = str(line.a)[str(line.a).find(">") + 1 :]
        town = postcode_line[: postcode_line.find(postcode) - 2]
        town = unidecode(town.replace("-", " "))

        # print("Town:", town)

        # Get price
        price_div = soup.find("div", class_="text-4xl").contents[0]
        price = int(str(price_div).replace("€", "").replace(" ", ""))
        # print("Price:", price, "€")

        # Get ref
        details_div = soup.find("ul", class_="lg:grid-cols-2").contents
        ref = None
        for line in details_div:
            if "Référence" in line.get_text():
                ref = "".join([num for num in line.get_text() if num.isdigit()])
                break
        # print("ref:", ref)

        # Chambres
        bedrooms = None
        try:
            for line in details_div:
                if "chambres" in str(line):
                    bedrooms = (
                        str(line).replace("text-gray-400", "").replace("1e2022", "")
                    )
            bedrooms = int("".join([num for num in bedrooms if num.isdigit()]))
        except:
            pass

        # print("Bedrooms:", bedrooms)

        # Rooms
        rooms = None
        try:
            for line in details_div:
                if "pièces" in str(line):
                    rooms = str(line).replace("text-gray-400", "").replace("1e2022", "")
            rooms = int("".join([num for num in rooms if num.isdigit()]))
        except:
            pass

        # print("Rooms:", rooms)

        # Plot size

        plot = None
        for line in details_div:
            if "terrain" in str(line):
                plot = str(line).replace("text-gray-400", "").replace("1e2022", "")
        try:
            plot = int(
                "".join([num for num in plot if num.isnumeric() and num.isascii()])
            )
        except:
            pass

        # print("Plot:", plot, "m²")

        # Property size
        size = None
        for line in details_div:
            if "habitable" in str(line):
                size = str(line).replace("text-gray-400", "").replace("1e2022", "")
        try:
            size = int(
                "".join([num for num in size if num.isnumeric() and num.isascii()])
            )
        except:
            pass

        # print("Size:", size, "m²")

        # Description
        description_div = soup.find("div", class_="text-[#969A9D]").p.contents
        description_list = []
        for item in description_div:
            if len(item.get_text()) > 3:
                description_list.extend(item.get_text().splitlines())

        description = [elem.strip() for elem in description_list if elem.strip()]

        # Photos
        # Photos are stored on a different page and hosted on another website. This finds the website and generates the links without visiting the main image page, or hosting website.
        # Listings with 5 or fewer photos don't have a separate page to host them, so the try/except tries the method for more than 5 images, if that fails, then scrapes the listing page for the photos available.

        # photos = []
        # try:
        #     total_number_photos = 5 + int(
        #         soup.find("p", class_="lg:text-2xl").contents[0][1:]
        #     )
        #     photo_links_div = soup.find("img", class_="object-cover")
        #     photo_raw_link = photo_links_div.get("src").split("/0/")

        #     for i in range(
        #         total_number_photos
        #     ):  # Might need to add .jpg to the end of links to make it work
        #         photos.append(
        #             photo_raw_link[0] + "/" + str(i) + "/" + photo_raw_link[1]
        #         )
        # except:
        #     photo_links_div = soup.find_all("img", class_="object-cover")
        #     for child in photo_links_div:
        #         if "backgrounds" not in child.get("src"):
        #             photos.append(child.get("src"))

        try:
            photos = get_photos(page)
        except:
            photos = []

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
#     "https://www.lavelanet-arthurimmo.com/annonces/achat/maison/lavelanet-09300/28476286.htm"
# ]

# for test_url in test_urls:
#     print(get_listing_details(requests.get(test_url), test_url, False))


# try:
#     with open("sold_urls.json", "r", encoding="utf8") as infile:
#         sold_url_list = json.load(infile)
# except:
#     sold_url_list = {"urls": []}

# arthur_listings = arthur_immo_get_listings(sold_url_list, host_photos=False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(arthur_listings, outfile, ensure_ascii=False)

# Time elapsed for Arthur Immo: 97.84s async 158 links with photos, down from 1.5+ hours
# Time elapsed for Arthur Immo: 24.02s 157 links without photos
