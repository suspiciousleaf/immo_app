from flask import Flask
import json
import math
from json_search import search
from markupsafe import escape
from flask import request

with open("listings.json", "r") as infile:
    listings = json.load(infile)

with open("postcodes_dict.json", "r") as infile:
    postcodes_dict = json.load(infile)

with open("ville_list_clean.json", "r") as infile:
    town_list_clean = json.load(infile)

# Must change the above open json to this when hosted:
# with open("/home/suspiciousleaf/immo_app/listings.json", "r") as infile:
#     listings = json.load(infile)

# Must do for flask_app.py, app.py, json_search.py


app = Flask(__name__)
    
# @app.route('/<name>/', methods=['GET'])
# def name(name):
#     return "Hello, {}".format(name)

@app.route('/postcode_dict/', methods=['GET'])
def postcodes():
    return postcodes_dict

@app.route("/search_results", methods=['GET'])
def search_call():
    def try_max(input):
        try:
            return int(input)
        except:
            return math.inf
        
    def try_min(input):
        try:
            return int(input)
        except:
            return 0

    def try_towns(input):
        try:
            return input.split(",")
        except:
            pass

    def try_search_radius(input):
        try:
            return int(input)
        except:
            return 0

    inc_none_beds_req = request.args.get('inc_none_beds') == "true"

    min_beds_req = try_min(request.args.get('min_beds'))
    max_beds_req = try_max(request.args.get('max_beds'))
    min_price_req = try_min(request.args.get('min_price'))
    max_price_req = try_max(request.args.get('max_price'))

    inc_none_plot_req = request.args.get('inc_none_plot') == "true"

    min_plot_req = try_min(request.args.get('min_plot'))
    max_plot_req = try_max(request.args.get('max_plot'))

    inc_none_size_req = request.args.get('inc_none_size') == "true"

    min_size_req = try_min(request.args.get('min_size'))
    max_size_req = try_max(request.args.get('max_size'))

    search_radius_req = try_search_radius(request.args.get('search_radius'))
    inc_none_location_req = request.args.get('inc_none_location') == "true"
    towns_req = try_towns(request.args.get('town'))

    return search(listings = listings, towns = towns_req, inc_none_location = inc_none_location_req, search_radius = search_radius_req, inc_none_beds = inc_none_beds_req, min_beds = min_beds_req, max_beds = max_beds_req, min_price = min_price_req, max_price = max_price_req, inc_none_plot = inc_none_plot_req, min_plot = min_plot_req, max_plot = max_plot_req, inc_none_size = inc_none_size_req, min_size = min_size_req, max_size = max_size_req)

# search(listings, type_list = type_list, agent_list = agent_list, town = "", search_radius = 0, inc_none_beds = True, min_beds = 0, max_beds = math.inf, min_price = 0, max_price = math.inf,  inc_none_plot = True, min_plot = 0, max_plot = math.inf, inc_none_size = True, min_size = 0, max_size = math.inf)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=105)

