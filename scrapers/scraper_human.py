# import os
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


def human_get_listings(old_listing_urls_dict):
    t0 = time.perf_counter()

    URL = "https://www.human-immobilier.fr/achat-maison-appartement-terrain-immeuble-aude?quartiers=11439-11441&surface=&sterr=&prix=-100000000&typebien=1-2-3-9&nbpieces=1-2-3-4-5&og=0&where=Aude-__11_&_b=1&_p=1&tyloc=6&neuf=1&ancien=1&ids=11"

    page = requests.get(URL)

    soup = BeautifulSoup(page.content, "html.parser")

    num_props_aude_div = soup.find("span", class_="nb-biens").get_text()
    num_props_aude = int("".join([x for x in num_props_aude_div if x.isnumeric()]))
    num_pages_aude = math.ceil(num_props_aude / 24)

    agencies = ["foix", "lavelanet", "mirepoix", "pamiers", "saverdun", "st-girons"]

    agency_urls = []
    for agency in agencies:
        # Most agencies have 1 or 2 pages of listings, max is 4 pages. Pages beyond range are populated with last page listings so no harm scraping. st-girons has more listings, so 5 pages used
        if agency == "st-girons":
            for i in range(1, 6):
                agency_urls.append(
                    f"https://www.human-immobilier.fr/immobilier-agence-{agency}?page={i}"
                )
        for i in range(1, 4):
            agency_urls.append(
                f"https://www.human-immobilier.fr/immobilier-agence-{agency}?page={i}"
            )

    all_search_pages = [
        f"https://www.human-immobilier.fr/achat-maison-appartement-terrain-immeuble-aude?quartiers=11439-11441&surface=&sterr=&prix=-100000000&typebien=1-2-3-9&nbpieces=1-2-3-4-5&og=0&where=Aude-__11_&_b=1&_p=1&tyloc=6&neuf=1&ancien=1&ids=11&page={i}"
        for i in range(1, num_pages_aude + 1)
    ]

    all_search_pages.extend(agency_urls)

    links = set()

    # Multi threading below saves approx 1 second
    with concurrent.futures.ThreadPoolExecutor() as executor:
        response = get_data(all_search_pages, header=False, prox=True)
        scraped_links = executor.map(
            human_get_links, (link["response"] for link in response)
        )
        for link in scraped_links:
            links.update(link)
    links = list(links)

    print("\nHuman Immobilier number of listings:", len(links))
    # pprint(links)

    # print("Number of unique listing URLs found:", len(links))

    links_old = set(old_listing_urls_dict.keys())

    links_to_scrape = [link for link in links if link not in links_old]
    print("New listings to add:", len(links_to_scrape))
    # pprint(links_to_scrape)
    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))

    counter_success = 0
    counter_fail = 0
    failed_scrape_links = []

    listings = []

    resp_to_scrape = get_data(links_to_scrape, header=False, prox=True)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            get_listing_details,
            (item["response"] for item in resp_to_scrape),
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
    print(f"Time elapsed for Human Immobilier: {time_taken:.2f}s")

    return {"listings": listings, "urls_to_remove": links_dead}


def human_get_links(page):
    soup = BeautifulSoup(page.content, "html.parser")

    list_biens = soup.find("div", id="liste-biens")
    links = list_biens.findAll("div", class_="bottom")

    link_list = []
    for link_div in links:
        link = link_div.find("a")
        if "annonce-achat" in link.get("href") and "Vendu" not in link.get_text():
            link_list.append("https://www.human-immobilier.fr" + link.get("href"))

    return link_list


def get_listing_details(page, url):
    try:
        agent = "Human Immobilier"
        link_url = url
        soup = BeautifulSoup(page.content, "html.parser")

        # Get type

        prop_type_div = soup.find("div", class_="d-block d-sm-block d-md-none")
        types = (
            prop_type_div.find("span", class_="title")
            .get_text()
            .replace(" à vendre", "")
        )

        # print("Type:", types)

        # Get location
        town_div = soup.find("div", class_="d-block d-sm-block d-md-none")
        town = unidecode(
            town_div.find("span", class_="ville").get_text().strip().replace("-", " ")
        ).capitalize()

        # Get postcode from inside brackets in title, if not present match town name with dictionary
        try:
            postcode = soup.title.string[
                soup.title.string.find("(") + 1 : soup.title.string.find(")")
            ]

        except:
            try:
                for key in postcodes_dict:
                    if town.casefold() in postcodes_dict[key]:
                        postcode = key
                        break
            except:
                postcode = None

        # print("Town:", town)
        # print("Postcode:", postcode)

        # Get price
        price_div = soup.find("span", class_="price-format").get_text()
        price_raw = "".join([num for num in price_div if num.isdigit()])
        if price_raw:
            price = int(price_raw)
        else:
            price = 0
        # print("Price:", price, "€")

        # Get ref
        ref = soup.find("span", class_="reference").get_text()[6:]
        # print("Ref:", ref)

        # # Get property details

        # Set defaults to None in case not found
        size = None
        plot = None
        rooms = None
        bedrooms = None
        details_div = soup.find("ul", class_="columns")
        details_div_list = details_div.findAll("li")
        for detail in details_div_list:
            try:
                if "habitable" in detail.get_text():
                    size = detail.get_text().replace("m²", "")
                    # The code below deals with the French use of "," and "." for decimal and thousands and converts to UK convention
                    size = int(
                        float(
                            size[size.index(":") + 1 :]
                            .strip()
                            .replace(".", "")
                            .replace(",", ".")
                        )
                    )
                elif "Superficie terrain" in detail.get_text():
                    plot = detail.get_text().replace("m²", "")
                    # The code below deals with the French use of "," and "." for decimal and thousands and converts to UK convention
                    plot = int(
                        float(
                            plot[plot.index(":") + 1 :]
                            .strip()
                            .replace(".", "")
                            .replace(",", ".")
                            .replace(" ", "")
                        )
                    )
                elif "Pièce(s)" in detail.get_text():
                    rooms = detail.get_text()
                    rooms = int(rooms[rooms.index(":") + 1 :].strip())
                elif "Chambre(s)" in detail.get_text():
                    bedrooms = detail.get_text()
                    bedrooms = int(bedrooms[bedrooms.index(":") + 1 :].strip())
            except:
                pass

        # print("Bedrooms:", bedrooms)
        # print("Rooms:", rooms)
        # print("Plot:", plot, "m²")
        # print("Size:", size, "m²")

        # Description
        description = soup.find("div", class_="descriptif").p.get_text().splitlines()
        description = [line for line in description if line]
        # pprint(description)

        # Photos
        # Finds the links to full res photos for each listing and returns them as a list
        photos = []
        photos_div_raw = soup.find("div", id="gallery")
        photos_div = photos_div_raw.findAll("a", class_="spanPhoto")
        for item in photos_div:
            photos.append(item.get("data-lc-href"))

        # Was returningL
        # https://www.human-immobilier.frhttps://www.human-immobilier.fr//images/513-428_130324113919.jpg?v=20230504
        # Changed photos.append(f"https://www.human-immobilier.fr{item.get('data-lc-href')}") to:
        # photos.append(item.get('data-lc-href'))

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
        return f"{url}: {str(e)}"


# human_listings = human_get_listings()

# test_url = "https://www.human-immobilier.fr/annonce-achat-maison-saverdun_417-743"
# test_response = requests.get(test_url)

# print(test_response.content)

proxy = {
    "http": "http://158.160.56.149:8080",
    "http": "http://103.173.128.51:8080",
    "http": "http://201.182.251.142:999",
    "http": "http://95.216.75.78:3128",
    "http": "http://51.79.50.31:9300",
    "http": "http://202.131.159.210:80",
    "http": "http://41.76.145.136:443",
    "http": "http://188.168.25.90:81",
    "http": "http://64.225.8.82:9967",
    "http": "http://47.92.93.39:8888",
    "http": "http://201.184.24.13:999",
    "http": "http://213.52.102.66:80",
    "http": "http://3.132.30.131:80",
    "http": "http://41.76.145.136:3128",
    "http": "http://75.119.129.192:3128",
    "http": "http://161.35.197.118:8080",
    "http": "http://5.161.80.172:8080",
    "http": "http://201.158.48.74:8080",
    "http": "http://41.76.145.136:8080",
    "http": "http://51.159.115.233:3128",
    "http": "http://64.226.110.184:45212",
    "http": "http://65.21.110.128:8080",
    "http": "http://213.52.102.30:10800",
    "http": "http://50.232.250.157:8080",
    "http": "http://18.143.215.49:80",
    "http": "http://190.119.86.66:999",
    "http": "http://180.184.91.187:443",
    "http": "http://95.216.156.131:8080",
    "http": "http://5.78.83.35:8080",
    "http": "http://78.110.195.242:7080",
    "http": "http://213.32.75.88:9300",
    "http": "http://31.186.241.8:8888",
    "http": "http://209.38.250.139:45212",
    "http": "http://51.158.189.189:8080",
}

# test_url = (
#     "https://www.human-immobilier.fr/annonce-achat-maison-ferrieres-sur-ariege_513-231"
# )
# get_listing_details(requests.get(test_url, proxies=proxy), test_url, False)

# with open("api.json", "w", encoding="utf-8") as outfile:
#     json.dump(human_listings, outfile, ensure_ascii=False)


#######################
# URL = [
#     "https://www.human-immobilier.fr/achat-maison-appartement-terrain-immeuble-aude?quartiers=11439-11441&surface=&sterr=&prix=-100000000&typebien=1-2-3-9&nbpieces=1-2-3-4-5&og=0&where=Aude-__11_&_b=1&_p=1&tyloc=6&neuf=1&ancien=1&ids=11&page=1"
# ]

# with open("response.html", mode="w") as file:
#     for line in test_response.text:
#         file.write(line)
