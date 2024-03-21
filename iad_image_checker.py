import grequests
import requests
from utilities.db_utilities import (
    select_primary_image_url,
    open_SSH_tunnel,
    close_SSH_tunnel,
)

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


def check_image_status_codes(listings: list[dict]) -> list[dict]:
    print("Running check_image_status_codes")
    reqs = [
        grequests.get(listing["photos"], headers=headers, stream=True)
        for listing in listings
    ]
    resp = grequests.map(reqs)

    data = []

    print("Listings:", len(listings))
    print("Responses:", len(resp))

    for listing_url, response in zip(listings, resp):
        if response:
            # if response.status_code != 200:
            print(response.status_code)
            print(response.url)
            print(listing_url["link_url"])

    # for response in resp:
    #     print(response.status_code)
    #     print(response.url)
    #     break

    # data.append({"listing_url": listing_url["link_url"], "response": response})
    # return data


ssh = open_SSH_tunnel()

iad_photo_urls = select_primary_image_url(["IAD Immobilier"])
# urls = [listing["photos"] for listing in iad_photo_urls]

check_image_status_codes(iad_photo_urls)

# reqs = [grequests.get(url, headers=headers, stream=True) for url in urls]
# resp = grequests.map(reqs)


# resp_200 = []
# resp_other = []
# for response in resp:
#     if response.status_code == 200:
#         resp_200.append(response.status_code)
#     else:
#         resp_other.append(response.status_code)
#         # print(response.status_code)

# print(len(urls))
# print(len(resp_200))
# print(len(resp_other))

close_SSH_tunnel(ssh)

# TODO Should have 74 requests for photos, and get 7 404, plus 67 200. Need to get the url for the main listing for each listing that has an image 404, then run the scraper for it to get new photo links, and put those links into the database. Let the main scraper run first to identify any listings that need to be removed entirely, then run the above checker on the listings that remain (excluding the newly scraped ones).
