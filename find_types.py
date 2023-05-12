# This is a little utility program that will make a set of "Types" for all listings present in the json opened.

import json
from pprint import pprint

with open("listings.json", "r", encoding="utf-8") as infile:
    listings = json.load(infile)

types = set()

for listing in listings:
    types.add(listing["types"])

pprint(types)


