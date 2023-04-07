import json
from pprint import pprint
from unidecode import unidecode
import os

with open("listings.json", "r") as infile:
    results = json.load(infile)

for listing in results:
    if listing["agent"] == "Ami Immobilier":
        print(listing["link_url"])

# ref = "5320"

# image_path = f"\\static\\images\\{ref}"
# cwd = os.getcwd()
# print(cwd)
# print(f"{cwd}{image_path}")
# try:
#     os.mkdir(f"{cwd}{image_path}")
# except:
#     pass

# # os.mkdir(os.getcwd() + "\\new")




# keyword_list = ["piscine", "garage"]

# def filter_keywords(results, keyword_list):
#     if keyword_list:
#         valid_results = []
#         for result in results:
#             valid = True
#             for keyword in keyword_list:
#                 if unidecode(keyword).casefold() not in unidecode(result["description"]).casefold():
#                     valid = False
#             if valid == True:
#                 valid_results.append(result)
#         return valid_results
#     else:
#         return results
    
# pprint(len(filter_keywords(results, [ "£$%%£"])))