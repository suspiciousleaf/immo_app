import json
from unidecode import unidecode

try:
    try:
        with open("listings.json", "r", encoding="utf8") as infile:
            listings_json = json.load(infile)
    except:
        with open("/home/suspiciousleaf/immo_app/listings.json", "r", encoding="utf8") as infile:
            listings_json = json.load(infile)
except:
    listings_json = []

try:
    try:
        with open("postcodes_dict.json", "r", encoding="utf8") as infile:
            postcodes_dict = json.load(infile)
    except:
        with open("/home/suspiciousleaf/immo_app/postcodes_dict.json", "r", encoding="utf8") as infile:
            postcodes_dict = json.load(infile)
except:
    postcodes_dict = []

try:
    try:
        with open("postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
    except:
        with open("/home/suspiciousleaf/immo_app/postcodes_gps_dict.json", "r", encoding="utf8") as infile:
            gps_dict = json.load(infile)
except:
    gps_dict = []

town_list = [item for sublist in postcodes_dict.values() for item in sublist]   # Creates a flat list of all town names from postcode_dict

def fix_location(listing):
    if listing["town"] != None:
        listing["town"] = unidecode(listing["town"].capitalize())   
        for postcode, town in postcodes_dict.items():
            if listing["town"].casefold().replace("st ", "saint ").replace("proche ", "").strip() in town:  # Any listing which has a valid town name but might be missing details has those details added and GPS corrected in some cases. Anything ending with "st" could cause an error.
                listing["town"] = listing["town"].casefold().replace("st ", "saint ").replace("proche ", "").capitalize().strip()
                listing["postcode"] = postcode
                listing["gps"] = gps_dict[postcode + ";" + listing["town"].casefold()] 
                # print(listing["town"], listing["postcode"], listing["gps"], listing["link_url"]) 

        if not listing["postcode"]: # Look through non valid town strings to see if a town name can be found, then add details as above
            # print(listing["town"], listing["postcode"], listing["gps"], listing["link_url"])
            for word in listing["town"].split():
                for postcode, town in postcodes_dict.items():
                    if word.casefold() in town:
                        listing["town"] = word.capitalize()
                        listing["postcode"] = postcode
                        listing["gps"] = gps_dict[postcode + ";" + listing["town"].casefold()]
                        # print(listing["town"], listing["postcode"], listing["gps"], listing["link_url"])
                        
        if listing["town"].casefold() not in town_list: # If listing has a postcode but no recognised town, sets town and GPS based on postcode
            if listing["postcode"]:
                # print(listing["postcode"])
                try:
                    listing["town"] = postcodes_dict[listing["postcode"]][0].capitalize()
                    listing["gps"] = gps_dict[listing["postcode"] + ";" + listing["town"].casefold()]
                except:
                    pass
            if not listing["gps"]:    # Check every word in description to find valid town names if the above line didn't find valid gps
                for word in listing["description"].split():     
                    if word.casefold() in town_list:
                        listing["town"] = word.capitalize()
                        listing["postcode"] = [i for i in postcodes_dict if listing["town"].casefold() in postcodes_dict[i]][0]
                        listing["gps"] = gps_dict[listing["postcode"] + ";" + listing["town"].casefold()]
                    
            if listing["town"] == "Sault":  # approximate locations for Ami listings Sault and Cathare
                listing["town"] = "Belcaire"
                listing["postcode"] = "11340"
                listing["gps"] = [42.8163554, 1.9603877]
                listing["description"] = "APPROXIMATE LOCATION - " + listing["description"]
            
            if listing["town"] == "Cathare":
                listing["town"] = "Belesta"
                listing["postcode"] = "09300"
                listing["gps"] = [42.9029283, 1.9340613]
                listing["description"] = "APPROXIMATE LOCATION - " + listing["description"]

        if listing["town"].casefold() not in town_list: # Any remaining properties have spurious values wiped
            listing["town"] = None
            listing["postcode"] = None
            listing["gps"] = None
    return listing

#  Error with multiple listing locations being set to the last one in postcode_dict, caused by using "postcode" as variable for listing, and when iterating through dctionary in scraping program       