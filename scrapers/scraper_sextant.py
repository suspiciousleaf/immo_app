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
    print("gps_dictnot found")
    gps_dict = []


def sextant_get_listings(old_listing_urls_dict, sold_url_set):
    t0 = time.perf_counter()
    URL = "https://arnaud-masip.sextantfrance.fr/ajax/ListeBien.php?numnego=75011397&page=1&TypeModeListeForm=pict&ope=1&lieu-alentour=0&langue=fr&MapWidth=100&MapHeight=0&DataConfig=JsConfig.GGMap.Liste&Pagination=0"
    page = requests.get(URL)

    sextant_soup = BeautifulSoup(page.content, "html.parser")
    num_props_div = sextant_soup.find(string=True)
    num_props = int(num_props_div.split("|")[0])
    print("\nSextant number of listings:", num_props)
    pages = math.ceil(num_props / 12)
    print("Pages:", pages)

    results_pages = [
        f"https://arnaud-masip.sextantfrance.fr/ajax/ListeBien.php?numnego=75011397&page={i}&TypeModeListeForm=pict&ope=1&lieu-alentour=0&langue=fr&MapWidth=100&MapHeight=0&DataConfig=JsConfig.GGMap.Liste&Pagination=0"
        for i in range(1, pages + 1)
    ]
    links = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        resp = get_data(results_pages)
        results = executor.map(sextant_get_links, (item["response"] for item in resp))
        for result in results:
            links += result
    links = [link for link in links if link not in sold_url_set]

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

    with concurrent.futures.ThreadPoolExecutor() as executor:
        response_objects = executor.map(
            requests.get, (link for link in links_to_scrape)
        )
        results = executor.map(
            get_listing_details,
            (item for item in response_objects),
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
    print(f"Time elapsed for Sextant: {time_taken:.2f}s")

    return {"listings": listings, "urls_to_remove": links_dead}


def sextant_get_links(page):
    sextant_soup = BeautifulSoup(page.content, "html.parser")

    links_raw = set()
    for link in sextant_soup.find_all("a"):
        links_raw.add(link.get("href"))
    links_raw.discard(None)
    links = [
        link for link in links_raw if "https://www.sextantfrance.fr/fr/annonce/" in link
    ]
    # pprint(links)
    return links


def get_listing_details(page, url):
    try:
        agent = "Sextant"
        soup = BeautifulSoup(page.content, "html.parser")
        link_url = url

        # print("\n\nNext property\n")

        # Get type

        # This dictionary allows access to a script tag that hosts much of the important data. The previous method of scraping these details as used on other agents that use the same template (Jammes, Time & Stone, and other - Adapt Immo) are being left in in case this method proves unreliable. The script tag is just identified as the last script tag in find_all, so might be unreliable when used on all listings. This way each piece of information can be commented in.out if errors are found in listing data.

        details_dict_raw = soup.find_all("script")[-1].get_text()
        details_dict_raw = details_dict_raw[
            details_dict_raw.find(", {") + 3 : details_dict_raw.find("'});") - 7
        ]

        if "dimension" in details_dict_raw:
            key_dict = {
                "type_key": "2",
                "town_key": "4",
                "postcode_key": "5",
                "price_key": "9",
                "rooms_key": "11",
                "bedrooms_key": "12",
                "ref_key": "14",
            }
        else:
            key_dict = {
                "type_key": "libelle_famille_bien",
                "town_key": "libelle_ville_bien",
                "postcode_key": "code_postal_bien",
                "price_key": "prix_bien",
                "rooms_key": "pieces_bien",
                "bedrooms_key": "chambres_bien",
                "ref_key": "mandat_bien",
            }

        details_dict = {}
        for item in details_dict_raw.split(","):
            try:
                key, value = item.split(":")
                details_dict[
                    key.replace("'", "").replace("dimension", "").strip()
                ] = value.strip().strip("'")
            except:
                pass

        types = details_dict[key_dict["type_key"]].capitalize()
        ref = details_dict[key_dict["ref_key"]]
        price = int(details_dict[key_dict["price_key"]].replace(" ", ""))
        town = (
            unidecode(details_dict[key_dict["town_key"]]).capitalize().replace("-", " ")
        )
        postcode = details_dict[key_dict["postcode_key"]]

        try:
            rooms = int(details_dict[key_dict["rooms_key"]])
        except:
            rooms = None
        try:
            bedrooms = int(details_dict[key_dict["bedrooms_key"]])
        except:
            bedrooms = None

        # print(rooms)
        # print(bedrooms)

        # print("Type:", types)

        # Get location
        # ! LEAVE THE COMMENTED CODE IN THE FILE - IF THE ABOVE METHOD STOPS WORKING THE BELOW CODE WILL WORK
        # location_div = soup.find("h2", class_="detail-bien-ville").get_text()
        # town = unidecode(location_div.split("(")[0]).strip().capitalize().replace("-", " ")
        # postcode = location_div.split("(")[1].replace("(", "").replace(")", "").strip()

        # print("Town:", town)
        # print("Postcode:", postcode)

        # Get price

        # price_div = soup.find("div", class_="detail-bien-prix").get_text()
        # price = int("".join([x for x in price_div if x.isdigit()]))

        # print("Price:", price, "€")

        # Get ref

        # Page returns two identical spans with itemprop="productID", one with a hidden ref and one with the 4 digit visible ref. No way to differentiate between the two. The second one has the desired  ref, so I turned it into a list, pulled the second item on the list (with the correct ref), then list comprehension to extract the digits, and join them into a string to get the correct ref.

        # prop_ref_div = soup.find_all("span", itemprop="productID")
        # prop_ref = list(prop_ref_div)
        # ref = "".join([char for char in str(prop_ref[1]) if char.isnumeric()])

        # print("ref:", ref)

        # # Get property details
        # # This returns a whole chunk of text for the property specs that gets separated to find the number of bedrooms, rooms, house size and land size.

        details_div_raw = soup.find("div", class_="detail-bien-specs")
        details_div = details_div_raw.findAll("li")
        # pprint(details_div)

        # # Plot size
        # # Property and plot sizes are not available from the script tag dictionary method above, so are scraped as usual.

        plot = None
        size = None

        for item in details_div:
            if "terrain" in str(item):
                try:
                    plot = int(
                        "".join(
                            [
                                num
                                for num in item.get_text()
                                if num.isnumeric() and num.isascii()
                            ]
                        )
                    )
                except:
                    pass
            elif "surface" in str(item):
                try:
                    size = int(
                        float(
                            "".join(
                                [
                                    num
                                    for num in item.get_text()
                                    if num.isnumeric() and num.isascii()
                                ]
                            )
                        )
                    )
                except:
                    pass

        # print("Plot:", plot, "m²")
        # print("Size:", size, "m²")

        # # Chambres

        # bedrooms = "".join([cham for cham in details_div if "chambre(s)" in cham]).split()
        # bedrooms = bedrooms[bedrooms.index("chambre(s)") - 1]
        # if bedrooms.isnumeric():
        #     bedrooms = int(bedrooms)
        # else:
        #     bedrooms = None
        # # print("Bedrooms:", bedrooms)

        # # Rooms

        # rooms = "".join([rooms for rooms in details if "pièce(s)" in rooms]).split()
        # rooms = rooms[rooms.index("pièce(s)") - 1]
        # if rooms.isnumeric():
        #     rooms = int(rooms)
        # else:
        #     rooms = None
        # # print("Rooms:", rooms)

        # Description

        description_raw = (
            soup.find("span", itemprop="description").get_text().split("\r\n")
        )
        description = [
            string.replace("\n", "").strip()
            for string in description_raw
            if string.replace("\n", "").strip()
        ]
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


# test_urls = [
#     "https://www.sextantfrance.fr/fr/annonce/vente-villa-quillan-p-r7-75011147118.html",
#     "https://www.sextantfrance.fr/fr/annonce/vente-maison-de-hameau-puivert-p-r7-75011147116.html",
#     "https://www.sextantfrance.fr/fr/annonce/vente-maison-bessede-de-sault-p-r7-75011147016.html",
#     "https://www.sextantfrance.fr/fr/annonce/vente-maison-quillan-p-r7-75011147115.html",
#     "https://www.sextantfrance.fr/fr/annonce/vente-maison-de-village-puilaurens-p-r7-75011147017.html",
#     "https://www.sextantfrance.fr/fr/annonce/vente-maison-de-caractere-saint-louis-et-parahou-p-r7-75011147117.html",
# ]

# for test_url in test_urls:
#     get_listing_details(requests.get(test_url), test_url)


# sextant_listings = sextant_get_listings()

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(sextant_listings, outfile, ensure_ascii=False)

# Time elapsed for Sextant: 16.68s 76 listings without photos. Minimal difference between multi-threading and async
