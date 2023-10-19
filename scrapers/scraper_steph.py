import json
import requests
import time

from pprint import pprint
from unidecode import unidecode

from models import Listing

# This holds the type codes used by steph with their corresponding string values
type_dict = {
    "1": "Appartement",
    "2": "Maison",
    "4": "Commerce",
    "6": "Immeuble",
    "9": "Commerce",
    "10": "Terrain",
    "11": "Other",
    "999": "Other",
}


def steph_get_listing_data():
    headers = {
        "method": "GET",
        "path": "/search/buy?target=buy&location[]=11&location[]=9&sort=",
        "scheme": "https",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7",
        "Dnt": "1",
        "X-Requested-With": "XMLHttpRequest",
    }

    listings_url = "https://www.stephaneplazaimmobilier.com/search/buy?target=buy&location[]=11&location[]=9&sort=price_asc&limit=500&page=0"
    page = requests.get(listings_url, headers=headers)
    return json.loads(page.content.decode("utf-8"))["results"]


def steph_create_listing(listing):
    types = type_dict.get(listing["type"], "Other")
    town = unidecode(listing["properties"]["city"].capitalize().replace("-", " "))
    postcode = listing["properties"]["codePostal"]
    price = int("".join([num for num in listing["price"] if num.isnumeric()]))
    agent = "Stéphane Plaza"
    ref = listing["reference"]
    bedrooms = listing["properties"].get("bedroom", None)
    rooms = listing["properties"].get("room", None)
    gps = [
        listing["location"]["lat"],
        listing["location"]["lon"],
    ]
    try:
        size = int(
            float(
                listing["properties"]["surface"]
                .replace("m2", "")
                .replace(" ", "")
                .replace(",", ".")
            )
        )
    except:
        size = None

    # Sometimes exterior space is listed as "surfaceJardin" as well as / instead of "surface-land", so the below adds the two values together, using .get() in case "surfaceJardin" is null, and then checks the final value. If it is 0, for no exterior space, it sets the value to None.
    plot = int(
        float(
            listing["properties"]
            .get("surface-land", "0")
            .replace("m2", "")
            .replace(" ", "")
            .replace(",", ".")
        )
    ) + int(
        float(
            listing["properties"]
            .get("surfaceJardin", "0")
            .replace("m2", "")
            .replace(" ", "")
            .replace(",", ".")
        )
    )
    if plot == 0:
        plot = None

    # Generates the url from the id and slug
    link_url = f"https://www.stephaneplazaimmobilier.com/immobilier-acheter/{listing['id']}/{listing['slug']}"
    description = [line for line in listing["description"].splitlines() if line]

    # Removes the ".mid.jpg" suffi to convert thumbnail url to full size image url
    photos = [url.replace(".mid.jpg", "") for url in listing["thumbnails"]]
    photos_hosted = photos

    return Listing(
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
    ).__dict__


def steph_get_listings(old_listing_urls_dict):
    t0 = time.perf_counter()

    print("\nStarting Stéphane Plaza")

    steph_listings_raw = steph_get_listing_data()

    steph_listings = [steph_create_listing(listing) for listing in steph_listings_raw]

    links = set([listing["link_url"] for listing in steph_listings])

    links_old = set(old_listing_urls_dict.keys())

    links_to_scrape = set([link for link in links if link not in links_old])
    print("New listings to add:", len(links_to_scrape))

    links_dead = [link for link in links_old if link not in links]
    print("Old listings to remove:", len(links_dead))

    listings_to_return = [
        listing for listing in steph_listings if listing["link_url"] in links_to_scrape
    ]

    t1 = time.perf_counter()
    time_taken = t1 - t0
    print(f"Time elapsed for Stéphane Plaza: {time_taken:.2f}s")

    return {"listings": listings_to_return, "urls_to_remove": links_dead}
