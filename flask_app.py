from flask import Flask, send_file, send_from_directory
import json
import math
from json_search import search
# from markupsafe import escape
from flask import request

try:
    with open("listings.json", "r") as infile:
        listings = json.load(infile)
except:
    with open("/home/suspiciousleaf/immo_app/listings.jsonlistings.json", "r") as infile:
        listings = json.load(infile)
try:
    with open("postcodes_dict.json", "r") as infile:
        postcodes_dict = json.load(infile)
except:
    with open("/home/suspiciousleaf/immo_app/postcodes_dict.json", "r") as infile:
        postcodes_dict = json.load(infile)

try:
    with open("ville_list_clean.json", "r") as infile:
        town_list_clean = json.load(infile)
except:
    with open("/home/suspiciousleaf/immo_app/ville_list_clean.json", "r") as infile:
        town_list_clean = json.load(infile)

# Must change the above open json to this when hosted:
# with open("/home/suspiciousleaf/immo_app/listings.json", "r") as infile:
#     listings = json.load(infile)

# Must do for flask_app.py, app.py, json_search.py


app = Flask(__name__, static_url_path='/static')

@app.route("/images/<path:folder>/<path:image>")
def download_file(folder, image):
    return send_file(f"static/images/{folder}/{image}"
    )

# @app.route('/<name>/', methods=['GET'])
# def name(name):
#     return "Hello, {}".format(name)

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

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

    def try_csv(input):
        try:
            return input.split(",")
        except:
            pass

    def try_search_radius(input):
        try:
            return int(input)
        except:
            return 0

    inc_none_beds_req = not request.args.get('inc_none_beds') == "false"

    min_beds_req = try_min(request.args.get('min_beds'))
    max_beds_req = try_max(request.args.get('max_beds'))

    inc_none_rooms_req = not request.args.get('inc_none_rooms') == "false"

    min_rooms_req = try_min(request.args.get('min_rooms'))
    max_rooms_req = try_max(request.args.get('max_rooms'))

    min_price_req = try_min(request.args.get('min_price'))
    max_price_req = try_max(request.args.get('max_price'))

    agent_list_req = try_csv(request.args.get('agents'))
    type_list_req = try_csv(request.args.get('types'))

    inc_none_plot_req = not request.args.get('inc_none_plot') == "false"

    min_plot_req = try_min(request.args.get('min_plot'))
    max_plot_req = try_max(request.args.get('max_plot'))

    inc_none_size_req = not request.args.get('inc_none_size') == "false"

    min_size_req = try_min(request.args.get('min_size'))
    max_size_req = try_max(request.args.get('max_size'))

    search_radius_req = try_search_radius(request.args.get('search_radius'))
    inc_none_location_req = not request.args.get('inc_none_location') == "false"
    towns_req = try_csv(request.args.get('town'))

    keyword_list_req = try_csv(request.args.get('keywords'))

    return search(listings = listings, keyword_list = keyword_list_req, type_list = type_list_req, agent_list = agent_list_req, towns = towns_req, inc_none_location = inc_none_location_req, search_radius = search_radius_req, inc_none_beds = inc_none_beds_req, min_beds = min_beds_req, max_beds = max_beds_req, inc_none_rooms = inc_none_rooms_req, min_rooms = min_rooms_req, max_rooms = max_rooms_req, min_price = min_price_req, max_price = max_price_req, inc_none_plot = inc_none_plot_req, min_plot = min_plot_req, max_plot = max_plot_req, inc_none_size = inc_none_size_req, min_size = min_size_req, max_size = max_size_req)

# Search parameters: Type, Agent, location, search radius, bedroom number, room number, price, plot size, property size

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=105)

