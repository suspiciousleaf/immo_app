# import os
# import time
import math
# import json
# import concurrent.futures

from pprint import pprint
import grequests    # This must be imported as it is imported with get_gps, and if requests is imported before grequests it will cause recursion error
import requests
from bs4 import BeautifulSoup
# import shutil
from unidecode import unidecode

# from async_image_downloader import make_photos_dir, dl_comp_photo
# from location_fix import fix_location   # This is necessary for Richardson and Ami, as both have poor quality and inconsistent location data
# from json_search import agent_dict
# from models import Listing
# from utilities import get_gps, get_data

URL = "https://beauxvillages.com/fr/nos-biens_fr?option=com_iproperty&view=allproperties&id=0&layout=&autocomplete=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne%2CAude&filter_province=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne&filter_county=Aude&filter_order=p.price&filter_order_Dir=ASC&commit=&5a7fb023d0edd8037757cf17e9634828=1&Itemid=10504793"# + str(i)
page = requests.get(URL)

beaux_soup = BeautifulSoup(page.content, "html.parser")#.decode('utf-8', 'ignore')
num_props__div = beaux_soup.find("span", class_="ip-pagination-results").get_text()
num_props = int(num_props__div[num_props__div.find("sur")+4:])
print("\nBeaux Villages number of listings:", num_props)
pages = math.ceil(num_props/30)
print("Pages:", pages)

search_urls = [f"https://beauxvillages.com/fr/nos-biens_fr?option=com_iproperty&view=allproperties&id=0&layout=&autocomplete=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne%2CAude&filter_province=Aude%2CAri%C3%A8ge%2CH%C3%A9rault%2CPyr%C3%A9n%C3%A9es-Orientales%2CHaute-Garonne&filter_county=Aude&filter_order=p.price&filter_order_Dir=ASC&commit=&5a7fb023d0edd8037757cf17e9634828=1&Itemid=10504793&start={i*30}" for i in range(pages)]

url = search_urls[0]

# pprint(search_urls)

def get_links(url):
    page = requests.get(url)
    links_soup = BeautifulSoup(page.content, "html.parser")
    # print(links_soup)
    links_div = links_soup.find("div", id="ip-searchfilter-wrapper")
    links_div = links_div.find_all("div", class_="ip-property-thumb-holder")
    # for div in links_div:
    #   print(div)

get_links(url)

def get_listing_details(url):
    page = requests.get(url)
    listing_soup = BeautifulSoup(page.content, "html.parser")
    print(listing_soup)
    

get_listing_details("https://beauxvillages.com/fr/nos-biens_fr/property/244923-BVI59352")