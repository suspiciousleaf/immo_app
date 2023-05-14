# This is a little utility program that will make a set of "Types" for all listings present in the json opened.

import json
from pprint import pprint

with open("listings.json", "r", encoding="utf-8") as infile:
    listings = json.load(infile)

types = set()

for listing in listings:
    types.add(listing["types"])

print("\n", types, sep="")


# Code below checks for duplicate listings in listings.json
urls = []
for listing in listings:
    urls.append(listing["link_url"])
url_set = set(urls)

if len(urls) == len(url_set):
    print("\nNo duplicates found.")
elif len(urls) > len(url_set):
    print("Duplicate listings found.")