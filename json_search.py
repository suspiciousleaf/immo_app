import json
from pprint import pprint
import math
from unidecode import unidecode
from geopy.distance import distance

# This is used to convert the agent name strings used in the search request to the full agent names used in the listings
agent_dict = {
      'ami': 'Ami Immobilier',
      'api': 'A.P.I.',
      'arthur': 'Arthur Immo',
      'aude': 'Aude Immobilier',
      'beaux': 'Beaux Villages',
      'c21': 'Century 21',
      'cimm': 'Cimm Immobilier',
      "europe": "Europe Sud Immobilier",
      "iad": "IAD Immobilier",
      'jammes': 'Cabinet Jammes',
      "l'immo": "L'Immo Chez Toit",
      'mm': 'M&M Immobilier',
      'nestenn': 'Nestenn',
      'richardson': 'Richardson Immobilier',
      'safti': 'Safti',
      'selection': 'Selection Habitat',
      'sextant': "Sextant",
      'time': 'Time and Stone Immobilier'
}

try:
    try:
        with open("listings.json", "r", encoding="utf8") as infile:
            listings = json.load(infile)
    except:
        with open("/home/suspiciousleaf/immo_app/listings.json", "r", encoding="utf8") as infile:
            listings = json.load(infile)
except:
    listings = []

try:
    with open("postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
except:
    with open("/home/suspiciousleaf/immo_app/postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
try:
    with open("postcodes_gps_dict.json", "r", encoding="utf8") as infile:
        gps_dict = json.load(infile)
except:
    with open("/home/suspiciousleaf/immo_app/postcodes_gps_dict.json", "r", encoding="utf8") as infile:
        gps_dict = json.load(infile)
try:
    with open("ville_list_clean.json", "r", encoding="utf8") as infile:
        town_list_clean = json.load(infile)
except:
    with open("/home/suspiciousleaf/immo_app/ville_list_clean.json", "r") as infile:
        town_list_clean = json.load(infile)

def filter_price(results, min_price, max_price):
    # print("filter_price ran")
    return [x for x in results if min_price <= x["price"] <= max_price]

def filter_agent(results, agent_list):
    # print("filter_agent ran")
    if agent_list:
        fullname_agent_search = [agent_dict[agent] for agent in agent_list]
        return [x for x in results if x["agent"] in fullname_agent_search]
    else:
        return results

def filter_keywords(results, keyword_list):
    if keyword_list:
        valid_results = []
        for result in results:
            valid = True
            for keyword in keyword_list:
                if unidecode(keyword).casefold() not in unidecode(result["description"]).casefold():
                    valid = False
            if valid == True:
                valid_results.append(result)
        return valid_results
    else:
        return results

def filter_type(results, type_list):
    # print("filter_type ran")
    if type_list:
        return [x for x in results if x["types"].capitalize() in type_list]
    else:
        return results

def filter_beds(results, inc_none_beds, min_beds, max_beds):
    # print("filter_beds ran")
    if inc_none_beds == True:
        return [x for x in results if x["bedrooms"] == None or min_beds <= x["bedrooms"] <= max_beds]
    elif inc_none_beds == False:
        return [x for x in results if x["bedrooms"] != None and min_beds <= x["bedrooms"] <= max_beds]
    
def filter_rooms(results, inc_none_rooms, min_rooms, max_rooms):
    # print("filter_rooms ran")
    if inc_none_rooms == True:
        return [x for x in results if x["bedrooms"] == None or min_rooms <= x["bedrooms"] <= max_rooms]
    elif inc_none_rooms == False:
        return [x for x in results if x["bedrooms"] != None and min_rooms <= x["bedrooms"] <= max_rooms]    

def filter_plot(results, inc_none_plot, min_plot, max_plot):
    # print("filter_plot ran")
    if inc_none_plot == True:
        return [x for x in results if x["plot"] == None or min_plot <= x["plot"] <= max_plot]
    elif inc_none_plot == False:
        return [x for x in results if x["plot"] != None and min_plot <= x["plot"] <= max_plot]

def filter_size(results, inc_none_size, min_size, max_size):
    # print("filter_size ran")
    if inc_none_size == True:
        return [x for x in results if x["size"] == None or min_size <= x["size"] <= max_size]
    elif inc_none_size == False:
        return [x for x in results if x["size"] != None and min_size <= x["size"] <= max_size]

def get_distance(origin, destination):
    # print("get_distance ran")
    origin_postcode = [i for i in postcodes_dict if origin in postcodes_dict[i]][0]
    origin_key = origin_postcode + ";" + origin

    destination_postcode = [i for i in postcodes_dict if destination in postcodes_dict[i]][0]
    destination_key = destination_postcode + ";" + destination

    origin = gps_dict[origin_key]
    destination = gps_dict[destination_key]
    return distance(origin, destination).km
   
def filter_department(results, dep_list):
    # print("filter_department ran")
    if dep_list:
        return [x for x in results if type(x["postcode"]) == str and x["postcode"][:2] in dep_list]
    else:
        return results

def filter_location(results, towns, search_radius, inc_none_location):
    # print("filter_location ran")
    if towns:
        location_results = []
        for town in towns:
            for result in results:
                if inc_none_location == True:   # Adds any listings with a town name None, or name not in list of valid town names
                    if result["town"] == None:
                        location_results.append(result)
                    else:
                        if unidecode(result["town"].casefold().replace("-", " ").replace("l hers", "l'hers").replace("d olmes", "d'olmes").replace("val du faby", "esperaza").replace("l'aiguillon", "l'aiguillon").replace("l'isle en dodon", "l' isle en dodon")) not in town_list_clean:
                            location_results.append(result)
                        else:
                            try:
                                if get_distance(town.casefold(), unidecode(result["town"].casefold().replace("-", " ").replace("l hers", "l'hers").replace("d olmes", "d'olmes").replace("val du faby", "esperaza").replace("l'aiguillon", "l'aiguillon").replace("l'isle en dodon", "l' isle en dodon"))) <= search_radius:
                                    location_results.append(result)
                            except:
                                pass
                elif inc_none_location == False:
                    if result["town"] == None:
                        pass
                    else:
                        if unidecode(result["town"].casefold().replace("-", " ").replace("l hers", "l'hers").replace("d olmes", "d'olmes").replace("val du faby", "esperaza").replace("l'aiguillon", "l'aiguillon").replace("l'isle en dodon", "l' isle en dodon")) not in town_list_clean:
                            pass
                        else:
                            try:
                                if get_distance(town.casefold(), unidecode(result["town"].casefold().replace("-", " ").replace("l hers", "l'hers").replace("d olmes", "d'olmes").replace("val du faby", "esperaza").replace("l'aiguillon", "l'aiguillon").replace("l'isle en dodon", "l' isle en dodon"))) <= search_radius:
                                    location_results.append(result)
                            except:
                                pass
        return location_results 
    else:
        return results

# This block is run occasionally to check for any new property types that haven't been included in the filtering list in app.py
# all_agents_set = set()    
# all_types_set = set()
# for item in listings:
#     all_agents_set.add(item["agent"])
#     all_types_set.add(item["types"])

# all_agent_list = list(all_agents_set)
# all_type_list = list(all_types_set)
# print(all_type_list)


# The below are the expected options for property types and agents
# types = ['terrain', 'immeuble', 'appartement', 'commerce', 'maison']
# agent_list = ['ami', 'mm', 'richardson', "l'immo", 'arthur', 'jammes', 'nestenn', 'cimm', 'api', 'aude', 'time']


def search(listings, type_list = None, agent_list = None, keyword_list = None, dep_list = None, inc_none_location = False, towns = None, search_radius = 0, inc_none_beds = True, min_beds = 0, max_beds = math.inf, inc_none_rooms = True, min_rooms = 0, max_rooms = math.inf, min_price = 0, max_price = math.inf,  inc_none_plot = True, min_plot = 0, max_plot = math.inf, inc_none_size = True, min_size = 0, max_size = math.inf):
    if print_filter_results:
        print("Full results list length:", len(listings))
    results_list = filter_price(listings, min_price, max_price)
    if print_filter_results:
        print("After price filter:", len(results_list))
    results_list = filter_agent(results_list, agent_list)
    if print_filter_results:
        print("After agent filter:", len(results_list))
    results_list = filter_type(results_list, type_list)
    if print_filter_results:
        print("After type filter:", len(results_list))
    results_list = filter_beds(results_list, inc_none_beds, min_beds, max_beds)
    if print_filter_results:
        print("After bedrooms filter:", len(results_list))
    results_list = filter_rooms(results_list, inc_none_rooms, min_rooms, max_rooms)
    if print_filter_results:
        print("After room filter:", len(results_list))
    results_list = filter_plot(results_list, inc_none_plot, min_plot, max_plot)
    if print_filter_results:
        print("After plot filter:", len(results_list))
    results_list = filter_size(results_list, inc_none_size, min_size, max_size)
    if print_filter_results:
        print("After size filter:", len(results_list))
    results_list = filter_department(results_list, dep_list)
    if print_filter_results:
        print("After department filter:", len(results_list))
    results_list = filter_keywords(results_list, keyword_list)
    if print_filter_results:
        print("After keyword filter:", len(results_list))
    results_list = filter_location(results_list, towns, search_radius, inc_none_location)
    if print_filter_results:
        print("After location filter:", len(results_list))

    return results_list

print_filter_results = False    #   If this is set to true, console will log how many valid listings are found after applying each filter. Used for debugging


# results_list = (search(listings, dep_list = ["11", "66", "09"]))
# print("\nNumber of results:", len(results_list), "\n")


# print(num)            
# print(types)
# print(list_agents)
