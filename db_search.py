from pprint import pprint
import time
import json

from utilities.db_utilities import connect_to_database


try:
    with open("postcodes_gps_dict.json", "r", encoding="utf8") as infile:
        gps_town_dict = json.load(infile)
except:
    with open(
        "/home/suspiciousleaf/immo_app/postcodes_gps_dict.json", "r", encoding="utf8"
    ) as infile:
        gps_town_dict = json.load(infile)


def keyword_search(keyword_list: list[str]) -> dict:
    """
    Takes a list of keyword strings to search descriptions, all keyword strings must be present to be selected.
    Accent and case insensitive.
    Args:
        keywords (list): List of keywords to search for

    Returns:
        dict: "keywords_dict": keywords, "query_string": String with all conditionals and placeholders
    """
    # Create dictionary with formatted keywords (values) and placeholders (keys)
    keywords_dict = {f"kw{i}": f"%{keyword}%" for i, keyword in enumerate(keyword_list)}

    # Generate the conditional string for SQL query
    query_string = " AND ".join(
        [f"description LIKE %({key})s" for key in keywords_dict]
    )

    return {"keywords_dict": keywords_dict, "query_string": query_string}


def department_search(depts: list[str], inc_none_location) -> dict:
    """_summary_
    Takes a list of department postcode prefixes, returns all listings within those departments.
    Args:
        depts (list): List of department postcode prefixes to filter by
    Returns:
        dict: "depts_dict": department codes, "query_string": String with all conditionals and placeholders
    """
    # Create dictionary with formatted postcode prefixes (values) and placeholders (keys)
    depts_dict = {f"dept{i}": f"%{keyword}___%" for i, keyword in enumerate(depts)}

    # Generate the conditional string for SQL query
    query_string_raw = " OR ".join([f"postcode LIKE %({key})s" for key in depts_dict])

    query_string = f"({query_string_raw})"

    if inc_none_location:
        return {
            "depts_dict": depts_dict,
            "query_string": f"({query_string} OR gps IS NULL)",
        }
    else:
        return {"depts_dict": depts_dict, "query_string": query_string}


def min_max_filter(
    conditions: list[str],
    params: dict,
    param: str,
    param_min: int,
    param_max: int,
    inc_none: bool = False,
) -> dict:
    """Builds conditional query statement and inserts paramters into dictionary for placeholders

    Args:
        conditions (str): SQL query statements list
        params (dict): Dictionary of placeholder parameters
        param (str): Name of value to be checked in database
        param_min (int): Min value if given
        param_max (int): Max value if given

    Returns:
        dict: "conditions": SQL conditions with placeholders, "params": Updated params dictionary with values for placeholders
    """
    statement = ""
    if any([param_min, param_max]):
        if param_min and not param_max:
            statement = f"{param} >= %({param}_min)s"
            params[f"{param}_min"] = param_min

        elif param_max and not param_min:
            statement = f"{param} <= %({param}_max)s"
            params[f"{param}_max"] = param_max

        elif param_min and param_max:
            statement = f"{param} BETWEEN %({param}_min)s AND %({param}_max)s"
            params[f"{param}_min"] = param_min
            params[f"{param}_max"] = param_max

        if inc_none:
            conditions.append(f"(({statement}) OR {param} IS NULL)")
        elif statement:
            conditions.append(statement)

    return {"conditions": conditions, "params": params}


def location_search(
    gps_list: list[list[float]], radius: int, inc_none_location: bool
) -> dict:
    """
    Takes a nested list of GPS coordinates and a search radius and creates a query string and values dictionary to filter all locations within the search radius of any provided GPS coordinates.

    Args:
        gps_list (list): List of GPS coordinates (nested for multiples)
        radius (int): Search radius in metres

    Returns:
        dict: "gps_dict": GPS coordinates, "query_string": String with all conditionals and placeholders
    """
    # Create dictionary with GPS coordinates for each location
    gps_dict = {}
    for i, coords in enumerate(gps_list):
        gps_dict[f"lat{i}"] = round(coords[0], 6)
        gps_dict[f"long{i}"] = round(coords[1], 6)

    # Generate the conditional string for SQL query
    query_string = " OR ".join(
        [
            f"(ST_Distance_Sphere(gps, ST_GeomFromText('POINT(%(lat{i})s %(long{i})s)', 4326)) <= {radius})"
            for i, _ in enumerate(gps_list)
        ]
    )
    if inc_none_location:
        return {
            "gps_dict": gps_dict,
            "query_string": f"({query_string} OR gps IS NULL)",
        }
    else:
        return {"gps_dict": gps_dict, "query_string": f"({query_string})"}


def perform_search(
    cursor,
    type_list=None,
    agent_list=None,
    depts_list=None,
    keyword_list=None,
    price_min=None,
    price_max=None,
    bedrooms_min=None,
    bedrooms_max=None,
    inc_none_beds=False,
    size_min=None,
    size_max=None,
    inc_none_size=False,
    plot_min=None,
    plot_max=None,
    inc_none_plot=False,
    towns=None,
    search_radius=0,
    inc_none_location=False,
):
    query = f"SELECT listingID, agent, plot, size, price FROM listings"

    conditions = []
    params = {}

    if agent_list:
        agents = ",".join(agent_list)
        conditions.append("FIND_IN_SET(agent, %(agents)s)")
        params["agents"] = agents

    if depts_list:
        dept_response = department_search(depts_list, inc_none_location)
        conditions.append(dept_response["query_string"])
        params.update(dept_response["depts_dict"])

    if type_list:
        types = ",".join(type_list)
        conditions.append("FIND_IN_SET(types, %(types)s)")
        params["types"] = types

    price_response = min_max_filter(conditions, params, "price", price_min, price_max)
    conditions = price_response["conditions"]
    params = price_response["params"]

    bedrooms_response = min_max_filter(
        conditions, params, "bedrooms", bedrooms_min, bedrooms_max, inc_none_beds
    )
    conditions = bedrooms_response["conditions"]
    params = bedrooms_response["params"]

    size_response = min_max_filter(
        conditions, params, "size", size_min, size_max, inc_none_size
    )
    conditions = size_response["conditions"]
    params = size_response["params"]

    plot_response = min_max_filter(
        conditions, params, "plot", plot_min, plot_max, inc_none_plot
    )
    conditions = plot_response["conditions"]
    params = plot_response["params"]

    if keyword_list:
        response = keyword_search(keyword_list)
        conditions.append(response["query_string"])
        params.update(response["keywords_dict"])

    if towns:
        gps_list = [
            [
                gps_town_dict[key.replace("-", ";")][0],
                gps_town_dict[key.replace("-", ";")][1],
            ]
            for key in towns
        ]
        gps_response = location_search(gps_list, search_radius, inc_none_location)
        conditions.append(gps_response["query_string"])
        params.update(gps_response["gps_dict"])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += ";"

    cursor.execute(query, params)


@connect_to_database
def search(
    db,
    cursor,
    type_list=None,
    agent_list=None,
    depts_list=None,
    keyword_list=None,
    price_min=None,
    price_max=None,
    bed_min=None,
    bed_max=None,
    inc_none_beds=False,
    size_min=None,
    size_max=None,
    inc_none_size=False,
    plot_min=None,
    plot_max=None,
    inc_none_plot=False,
    towns=None,
    search_radius=0,
    inc_none_location=False,
):
    try:
        t0 = time.perf_counter()
        # Change cursor provided to dictionary cursor for results
        cursor = db.cursor(dictionary=True)

        perform_search(
            cursor,
            type_list,
            agent_list,
            depts_list,
            keyword_list,
            price_min,
            price_max,
            bed_min,
            bed_max,
            inc_none_beds,
            size_min,
            size_max,
            inc_none_size,
            plot_min,
            plot_max,
            inc_none_plot,
            towns,
            search_radius,
            inc_none_location,
        )

        print(f"\nTime taken: {time.perf_counter() - t0:.2f}s\n")

        # print(cursor.statement)

        results = cursor.fetchall()

        if results:
            return results
        else:
            return []

    except Exception as e:
        print(f"An error occurred: {str(e)}")


@connect_to_database
def get_listings_by_listingID(db, cursor, listing_IDs: list[str]) -> list:
    """Takes a list of UUIDs (listingID) as strings and returns those entire listings

    Args:
        listing_IDs (list[str]): List of all requested UUIDs

    Returns:
        list[dict]: List of full listings
    """
    try:
        table_name = "listings"
        t0 = time.perf_counter()
        cursor = db.cursor(dictionary=True)

        # listingID must be selected to enable the "save listing" function, even though it isn't displayed on the page.
        query = f"SELECT listingID, types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos_hosted FROM {table_name} WHERE FIND_IN_SET(listingID, %(listing_IDs_requested)s);"

        params = {}

        listing_IDs_requested = ",".join(listing_IDs)

        params["listing_IDs_requested"] = listing_IDs_requested

        cursor.execute(query, params)

        results = cursor.fetchall()

        if results:
            for result in results:
                if result["description"]:
                    result["description"] = result["description"].split(":;:")
                if result["photos_hosted"]:
                    result["photos_hosted"] = result["photos_hosted"].split(":;:")
            return results
        else:
            return []

    except Exception as e:
        print(f"An error occurred: {str(e)}")
