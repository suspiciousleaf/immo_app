import json
import math

from flask import Flask, send_file
from flask import request

from json_search import search, listings_id_search  # , agent_dict

# The imports below are to get the listing data, as well as two dictionaries that are used. The path of the file is different when hosted locally or on PythonAnywhere, so the try/except allows the files to be imported correctly regardless of whether the program is run locally or when hosted.

try:  # listings.json
    with open("listings.json", "r", encoding="utf8") as infile:
        listings = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/listings.json", "r", encoding="utf8"
    ) as infile:
        listings = json.load(infile)
try:  # postcodes_dict.json
    with open("static/data/postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/static/data/postcodes_dict.json",
        "r",
        encoding="utf8",
    ) as infile:
        postcodes_dict = json.load(infile)

app = Flask(__name__, static_url_path="/static")


# This path is used to serve images that have been downloaded from the listing agent and hosted, rather than being used directly from the listing agent image host
@app.route("/static/images/<path:agent>/<path:ref>/<path:image>")
def download_file(agent, ref, image):
    return send_file(f"static/images/{agent}/{ref}/{image}")


# The after_request is used to add a header to every request to fix CORS errors (cross origin resource sharing)
@app.after_request
def add_header(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# The postcode dictionary is used by the front end for the location search section, to autofill search queries
@app.route("/postcode_dict/", methods=["GET"])
def postcodes():
    return postcodes_dict


# # Dictionary of agent abbreviated names : full agent names
# @app.route("/agent_dict/", methods=["GET"])
# def agents():
#     return agent_dict


# This  will check if a valid value is given for fields which define a maximum value, and will return infinite if not found
def try_max(input):
    try:
        return int(input)
    except:
        return math.inf


# This  will check if a valid value is given for fields which define a minimum value, and will return 0 if not found
def try_min(input):
    try:
        return int(input)
    except:
        return 0


# This will check for fields expected to be in csv format, location names etc
def try_csv(input):
    try:
        return input.split(",")
    except:
        pass


@app.route("/full_listings", methods=["GET"])
def full_listing_ids():
    refs_req = try_csv(request.args.get("id"))

    return listings_id_search(listings=listings, refs=refs_req)


# The path below is to receive the search query and parameters, and call the search function from json_search.py
@app.route("/search_results", methods=["GET"])
def search_call():
    # The code below extracts the search parameters from the query and validates them using the above functions, then calls the search function with those parameters as arguments

    inc_none_beds_req = not request.args.get("inc_none_beds") == "false"

    min_beds_req = try_min(request.args.get("min_beds"))
    max_beds_req = try_max(request.args.get("max_beds"))

    inc_none_rooms_req = not request.args.get("inc_none_rooms") == "false"

    min_rooms_req = try_min(request.args.get("min_rooms"))
    max_rooms_req = try_max(request.args.get("max_rooms"))

    min_price_req = try_min(request.args.get("min_price"))
    max_price_req = try_max(request.args.get("max_price"))

    agent_list_req = try_csv(request.args.get("agents"))
    type_list_req = try_csv(request.args.get("types"))

    inc_none_plot_req = not request.args.get("inc_none_plot") == "false"

    min_plot_req = try_min(request.args.get("min_plot"))
    max_plot_req = try_max(request.args.get("max_plot"))

    inc_none_size_req = not request.args.get("inc_none_size") == "false"

    min_size_req = try_min(request.args.get("min_size"))
    max_size_req = try_max(request.args.get("max_size"))

    depts_list_req = try_csv(request.args.get("depts"))
    search_radius_req = try_min(request.args.get("search_radius"))
    inc_none_location_req = not request.args.get("inc_none_location") == "false"
    towns_req = try_csv(request.args.get("town"))

    keyword_list_req = try_csv(request.args.get("keywords"))

    return search(
        listings=listings,
        keyword_list=keyword_list_req,
        type_list=type_list_req,
        agent_list=agent_list_req,
        depts_list=depts_list_req,
        towns=towns_req,
        inc_none_location=inc_none_location_req,
        search_radius=search_radius_req,
        inc_none_beds=inc_none_beds_req,
        min_beds=min_beds_req,
        max_beds=max_beds_req,
        inc_none_rooms=inc_none_rooms_req,
        min_rooms=min_rooms_req,
        max_rooms=max_rooms_req,
        min_price=min_price_req,
        max_price=max_price_req,
        inc_none_plot=inc_none_plot_req,
        min_plot=min_plot_req,
        max_plot=max_plot_req,
        inc_none_size=inc_none_size_req,
        min_size=min_size_req,
        max_size=max_size_req,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=105)
