import json
from pprint import pprint

from flask import Flask, request

from db_search import search, get_listings_by_listingID
from utilities.db_utilities import open_SSH_tunnel, close_SSH_tunnel
from utilities.agent_dict import agent_dict


# The import below is used to get the dictionary that is used. The path of the file is different when hosted locally or on PythonAnywhere, so the try/except allows the files to be imported correctly regardless of whether the program is run locally or when hosted. This same try/except is used to track if running locally or hosted, so that an ssh tunnel can be opened for the database connection if running locally.

try:  # postcodes_dict.json
    with open("postcodes_dict.json", "r", encoding="utf8") as infile:
        postcodes_dict = json.load(infile)
    # running_local is used to track if the program is running on the local machine (which requres an ssh tunnel to be established to access the databases), or if it is running on the host, which does not require it.
    running_local = True
except:
    with open(
        "/home/suspiciousleaf/immo_app/postcodes_dict.json", "r", encoding="utf8"
    ) as infile:
        postcodes_dict = json.load(infile)
    running_local = False

app = Flask(__name__)


# The after_request is used to add a header to every request to fix CORS errors (cross origin resource sharing)
@app.after_request
def add_header(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# The postcode dictionary is used by the front end for the location search section, to autofill search queries
@app.route("/postcode_dict/", methods=["GET"])
def postcodes():
    return postcodes_dict


# Dictionary of agent abbreviated names : full agent names
@app.route("/agent_dict/", methods=["GET"])
def agents():
    return agent_dict


# This  will check if a valid value is given for fields which require a number, and return None if not valid. This will exclude that parameter from being used in the search
def try_num(input):
    try:
        return int(float(input))
    except:
        return None


# This will check for fields expected to be in csv format, location names etc
def try_csv(input):
    try:
        return input.split(",")
    except:
        pass


@app.route("/full_listings", methods=["GET"])
def full_listing_ids():
    if running_local:
        ssh = open_SSH_tunnel()

    listingID_list = try_csv(request.args.get("id"))

    results = get_listings_by_listingID(listingID_list)

    if running_local:
        close_SSH_tunnel(ssh)

    return results


# The path below is to receive the search query and parameters, and call the search function from db_search.py
@app.route("/search_results", methods=["GET"])
def search_call():
    if running_local:
        ssh = open_SSH_tunnel()

    # The code below extracts the search parameters from the query and validates them using the above functions, then calls the search function with those parameters as arguments

    inc_none_beds_req = not request.args.get("inc_none_beds") == "false"

    min_beds_req = try_num(request.args.get("min_beds"))
    max_beds_req = try_num(request.args.get("max_beds"))

    min_price_req = try_num(request.args.get("min_price"))
    max_price_req = try_num(request.args.get("max_price"))

    agent_list_req = try_csv(request.args.get("agents"))
    type_list_req = try_csv(request.args.get("types"))

    inc_none_plot_req = not request.args.get("inc_none_plot") == "false"

    min_plot_req = try_num(request.args.get("min_plot"))
    max_plot_req = try_num(request.args.get("max_plot"))

    inc_none_size_req = not request.args.get("inc_none_size") == "false"

    min_size_req = try_num(request.args.get("min_size"))
    max_size_req = try_num(request.args.get("max_size"))

    depts_list_req = try_csv(request.args.get("depts"))
    search_radius_req = try_num(request.args.get("search_radius"))

    inc_none_location_req = not request.args.get("inc_none_location") == "false"

    towns_req = try_csv(request.args.get("town"))

    keyword_list_req = try_csv(request.args.get("keywords"))

    # print(
    #     f"{type_list_req = }, \n{agent_list_req = }, \n{depts_list_req = }, \n{keyword_list_req = }, \n{towns_req = }, \n{inc_none_location_req = }, \n{search_radius_req = }, \n{inc_none_beds_req = }, \n{min_beds_req = }, \n{max_beds_req = }, \n{min_price_req = }, \n{max_price_req = }, \n{inc_none_plot_req = }, \n{min_plot_req = }, \n{max_plot_req = }, \n{inc_none_size_req = }, \n{min_size_req = }, \n{max_size_req = }",
    # )

    results = search(
        type_list=type_list_req,
        agent_list=agent_list_req,
        depts_list=depts_list_req,
        keyword_list=keyword_list_req,
        towns=towns_req,
        inc_none_location=inc_none_location_req,
        search_radius=search_radius_req,
        inc_none_beds=inc_none_beds_req,
        bed_min=min_beds_req,
        bed_max=max_beds_req,
        price_min=min_price_req,
        price_max=max_price_req,
        inc_none_plot=inc_none_plot_req,
        plot_min=min_plot_req,
        plot_max=max_plot_req,
        inc_none_size=inc_none_size_req,
        size_min=min_size_req,
        size_max=max_size_req,
    )

    if running_local:
        close_SSH_tunnel(ssh)

    return results


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=105)

#! Century21 can return listings with towns + postcodes but no GPS coords
#! richardson listings missing some photos, eg ref 4149
