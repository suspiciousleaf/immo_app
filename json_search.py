import json
from pprint import pprint
import math

with open("listings.json", "r") as infile:
    listings = json.load(infile)

# min_price = int(input("Minimum price: "))
# max_price = int(input("Maximum price: "))
# min_bedrooms = int(input("Minimum bedrooms: "))


def filter_price(results, min_price, max_price):
    return [x for x in results if min_price <= x["price"] <= max_price]

def filter_agent_type(results, type_list, agent_list):
    return [x for x in results if x["types"] in type_list and x["agent"] in agent_list]

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


all_agents_set = set()
all_types_set = set()
price_types = set()
for item in listings:
    all_agents_set.add(item["agent"])
    all_types_set.add(item["types"])
    price_types.add(type(item["price"]))

# print(price_types)
agent_list = list(all_agents_set)
type_list = list(all_types_set)

def search(listings, type_list = type_list, agent_list = agent_list, town = "", search_radius = 0, inc_none_beds = True, min_beds = 0, max_beds = math.inf, min_price = 0, max_price = math.inf,  inc_none_plot = True, min_plot = 0, max_plot = math.inf, inc_none_size = True, min_size = 0, max_size = math.inf):
    results_list = filter_price(listings, min_price, max_price)
    results_list = filter_agent_type(results_list, type_list, agent_list)
    results_list = filter_beds(results_list, inc_none_beds, min_beds, max_beds)
    results_list = filter_plot(results_list, inc_none_plot, min_plot, max_plot)
    results_list = filter_size(results_list, inc_none_size, min_size, max_size)
    return results_list

# pprint(agent_list)

# pprint(type_list)

# results_list = (search(listings, inc_none_beds = True, min_price = 99999))
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