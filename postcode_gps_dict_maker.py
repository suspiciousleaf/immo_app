# This program is used to build the dictionary of postcodes with their GPS coordinates, output is postcodes_gps_dict.json

from pprint import pprint
from unidecode import unidecode
import json
from geopy.geocoders import Nominatim

with open("ville_list.txt", "r", encoding = 'utf-8-sig') as infile:
    postcodes = infile.readlines()

postcodes = [unidecode(line.strip()).replace("Code Postal ", "").replace("-", " ").casefold() for line in postcodes]
# print(postcodes)

breaks = []
def postcode_dict():
    for i in range(len(postcodes)):
        if postcodes[i].isnumeric():
            breaks.append(i)

    postcode_list = []

    for i in range(len(breaks)-1): 
      postcode_list.append(postcodes[breaks[i]:breaks[i+1]])

    return {lst[0]:lst[1:] for lst in postcode_list}

    # pprint(postcode_dict)

with open("postcodes_dict.json", "w") as outfile:
    json.dump(postcode_dict(), outfile)

def get_gps(town, postcode):
    geolocator = Nominatim(user_agent="property-scraper")
    location = geolocator.geocode(town + " " + postcode + " France")
    gps = [location.latitude, location.longitude]
    return gps

town_list = [item for item in postcodes if item.isnumeric() == False]

with open("ville_list_clean.json", "w") as outfile:
    json.dump(town_list, outfile)
# print(town_list)

def create_town_list():
    with open("postcodes_dict.json", "r") as infile:
            town_postcode_dict = json.load(infile)

def get_gps_dict():
    
    town_gps_dict = {}
    for i in range(len(town_list)):
      print("Number: {}".format(i))
      try:
          town_gps_dict[town_list[i]] = get_gps(town_list[i], get_key(town_list[i]))
      except:
          town_gps_dict[town_list[i]] = get_gps(town_list[i], "")
      print(town_list[i], town_gps_dict[town_list[i]])
    return town_gps_dict

def get_key(val):
    for key, value in town_postcode_dict.items():
        if val in value:
            return key

def create_gps_dict():
    with open("postcodes_gps_dict.json", "w") as outfile:  
        json.dump(get_gps_dict(), outfile)

# create_town_list()

# create_gps_dict()