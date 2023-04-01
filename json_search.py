import json
from pprint import pprint
import math
from unidecode import unidecode
from geopy.distance import distance

with open("listings.json", "r") as infile:
    listings = json.load(infile)

with open("postcodes_gps_dict.json", "r") as infile:
    gps_dict = json.load(infile)

with open("ville_list_clean.json", "r") as infile:
    town_list_clean = json.load(infile)

agent_dict = {
      'ami': 'Ami Immobilier',
      'mm': 'M&M Immobilier',
      'richardson': 'Richardson Immobilier',
      "l'immo": "L'Immo Chez Toit",
      'arthur': 'Arthur Immo',
      'jammes': 'Cabinet Jammes',
      'nestenn': 'Nestenn',
      'cimm': 'Cimm Immobilier',
      'api': 'A.P.I.',
      'aude': 'Aude Immobilier',
      'time': 'Time and Stone Immobilier'
}

def filter_price(results, min_price, max_price):
    return [x for x in results if min_price <= x["price"] <= max_price]

def filter_agent_type(results, type_list, agent_list):
    fullname_agent_search = [agent_dict[agent] for agent in agent_list]
    return [x for x in results if x["types"].casefold() in type_list and x["agent"] in fullname_agent_search]

def filter_beds(results, inc_none_beds, min_beds, max_beds):
    if inc_none_beds == True:
        return [x for x in results if x["bedrooms"] == None or min_beds <= x["bedrooms"] <= max_beds]
    elif inc_none_beds == False:
        return [x for x in results if x["bedrooms"] != None and min_beds <= x["bedrooms"] <= max_beds]

def filter_plot(results, inc_none_plot, min_plot, max_plot):
    if inc_none_plot == True:
        return [x for x in results if x["plot"] == None or min_plot <= x["plot"] <= max_plot]
    elif inc_none_plot == False:
        return [x for x in results if x["plot"] != None and min_plot <= x["plot"] <= max_plot]

def filter_size(results, inc_none_size, min_size, max_size):
    if inc_none_size == True:
        return [x for x in results if x["size"] == None or min_size <= x["size"] <= max_size]
    elif inc_none_size == False:
        return [x for x in results if x["size"] != None and min_size <= x["size"] <= max_size]

def get_distance(origin, destination):
    origin = gps_dict[origin]
    destination = gps_dict[destination]
    return distance(origin, destination).km

def filter_location(results, towns, search_radius, inc_none_location):
    location_results = []
    for town in towns:
        for result in results:
            if inc_none_location == True:
                if result["town"] == None:
                    location_results.append(result)
                else:
                    if unidecode(result["town"].casefold().replace("-", " ").replace("l hers", "l'hers").replace("d olmes", "d'olmes").replace("val du faby", "esperaza").replace("l'aiguillon", "l' aiguillon").replace("l'isle en dodon", "l' isle en dodon")) not in town_list_clean:
                        location_results.append(result)
                    else:
                        if get_distance(town.casefold(), unidecode(result["town"].casefold().replace("-", " ").replace("l hers", "l'hers").replace("d olmes", "d'olmes").replace("val du faby", "esperaza").replace("l'aiguillon", "l' aiguillon").replace("l'isle en dodon", "l' isle en dodon"))) <= search_radius:
                            location_results.append(result)
            elif inc_none_location == False:
                if result["town"] == None:
                    pass
                else:
                    if unidecode(result["town"].casefold().replace("-", " ").replace("l hers", "l'hers").replace("d olmes", "d'olmes").replace("val du faby", "esperaza").replace("l'aiguillon", "l' aiguillon").replace("l'isle en dodon", "l' isle en dodon")) not in town_list_clean:
                        pass
                    else:
                        if get_distance(town.casefold(), unidecode(result["town"].casefold().replace("-", " ").replace("l hers", "l'hers").replace("d olmes", "d'olmes").replace("val du faby", "esperaza").replace("l'aiguillon", "l' aiguillon").replace("l'isle en dodon", "l' isle en dodon"))) <= search_radius:
                            location_results.append(result)
    return location_results 

all_agents_set = set()
all_types_set = set()
for item in listings:
    all_agents_set.add(item["agent"])
    all_types_set.add(item["types"])


all_agent_list = list(all_agents_set)
all_type_list = list(all_types_set)
print(all_type_list)

def search(listings, type_list = all_type_list, agent_list = ['ami', 'mm', 'richardson', "l'immo", 'arthur', 'jammes', 'nestenn', 'cimm', 'api', 'aude', 'time'], inc_none_location = False, towns = None, search_radius = 0, inc_none_beds = True, min_beds = 0, max_beds = math.inf, min_price = 0, max_price = math.inf,  inc_none_plot = True, min_plot = 0, max_plot = math.inf, inc_none_size = True, min_size = 0, max_size = math.inf):
    results_list = filter_price(listings, min_price, max_price)
    results_list = filter_agent_type(results_list, type_list, agent_list)
    results_list = filter_beds(results_list, inc_none_beds, min_beds, max_beds)
    results_list = filter_plot(results_list, inc_none_plot, min_plot, max_plot)
    results_list = filter_size(results_list, inc_none_size, min_size, max_size)
    if towns:
        results_list = filter_location(results_list, towns, search_radius, inc_none_location)

    return results_list


# pprint(agent_list)

# pprint(type_list)

# results_list = (search(listings, type_list=["Terrain"]))
# pprint(results_list)


# print("\nNumber of results:", len(results_list), "\n")

# num = 0
# for item in listings:
#     if type(item["plot"]) ==  str:
#         num += 1
#         print(item["link_url"])
#         print(item["plot"])
# print(num)            
# print(types)
# print(list_agents)