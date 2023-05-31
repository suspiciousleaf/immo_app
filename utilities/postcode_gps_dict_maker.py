# This program is used to build the dictionary of postcodes with their GPS coordinates, output is postcodes_gps_dict.json

import json

from pprint import pprint
from unidecode import unidecode

# from geopy.geocoders import Nominatim

from utilities.utilities import get_gps

# import requests

# This is a text file with town names and postcodes scraped from gov site
with open("ville_list.txt", "r", encoding="utf-8-sig") as infile:
    postcodes = infile.readlines()

postcodes = [
    unidecode(line.strip()).replace("Code Postal ", "").replace("-", " ").casefold()
    for line in postcodes
]
# print(postcodes)


# This will make a json withe postcodes as keys to town names as values
def postcode_dict_maker():
    breaks = []
    for i in range(len(postcodes)):
        if postcodes[i].isnumeric():
            breaks.append(i)

    postcode_list = []

    for i in range(len(breaks) - 1):
        postcode_list.append(postcodes[breaks[i] : breaks[i + 1]])

    postcode_dict = {lst[0]: lst[1:] for lst in postcode_list}

    with open("postcodes_dict.json", "w", encoding="utf-8") as outfile:
        json.dump(postcode_dict(), outfile, ensure_ascii=False)


# postcode_dict_maker()


# This will make a json file with all town names only
def create_town_list():
    town_list = [item for item in postcodes if item.isnumeric() == False]

    with open("ville_list_clean.json", "w", encoding="utf-8") as outfile:
        json.dump(town_list, outfile, ensure_ascii=False)


# create_town_list()

try:
    with open("postcodes_dict.json", "r", encoding="utf8") as infile:
        town_postcode_dict = json.load(infile)
except:
    print(
        "postcodes_dict.json not found, please run postcode_dict_maker() to create a new one first."
    )


# Run this to create a dictionary with postcode;town, GPS as key, value and export as json
def create_gps_dict():
    failed_list = []
    postcode_list = []
    i = 0

    for key in town_postcode_dict.keys():
        for value in town_postcode_dict[key]:
            # ; is used as a seperator to make postcode;town a string, so it can be serialized as json
            postcode_list.append(f"{key};{value}")
    postcode_dict = {}

    for pc in postcode_list:
        i += 1
        try:
            postcode_dict[pc] = get_gps(pc.split(";")[1], pc.split(";")[0])
            print(f"Number: {i} success.")
        except:
            postcode_dict[pc] = None
            failed_list.append(pc)
            print(f"Number: {i} failed.")
    if failed_list:
        # This will return any towns that failed to find a GPS coordinate, so it can be done manuall afterwards.
        pprint(failed_list)

    with open("postcodes_gps_dict.json", "w", encoding="utf-8") as outfile:
        json.dump(postcode_dict, outfile, ensure_ascii=False)


# create_gps_dict()
