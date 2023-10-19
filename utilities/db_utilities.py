import mysql.connector
from pprint import pprint
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

ssh_password = os.environ.get("PA_SSH_PASS")
db_password = os.environ.get("PA_DB_PASS")
database = os.environ.get("PA_DB_NAME")


def open_SSH_tunnel():
    """Opens SSH tunnel via cmd so database can be accessed via localhost. Returns ssh object that must be closed using close_SSH_tunnel function.

    Returns:
        ssh object: Used only to close the connection
    """
    print("Opening SSH Tunnel")
    # Define the SSH command to establish a tunnel
    ssh_command = "ssh -L 3306:suspiciousleaf.mysql.eu.pythonanywhere-services.com:3306 suspiciousleaf@ssh.eu.pythonanywhere.com"

    # Open a new cmd process and run the SSH command
    cmd_process = subprocess.Popen(
        ["cmd", "/K", ssh_command],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        text=True,
    )
    return cmd_process


def close_SSH_tunnel(cmd_process):
    # Check if the process is still running, and terminate it if necessary
    if cmd_process.poll() is None:
        print("Closing SSH Tunnel")
        cmd_process.terminate()


# Decorator function
def connect_to_database(original_func):
    """Decorator function to connect to the database, run the function, and then close the connection

    Args:
        original_func (function): Function to be wrapped
    """

    def make_connection(*args, **kwargs):
        results = None
        try:
            # print("Connecting to database...")
            db = mysql.connector.connect(
                user="suspiciousleaf",
                password=db_password,
                host="127.0.0.1",
                port=3306,
                database=database,
                use_pure=True,
            )
            cursor = db.cursor()
            results = original_func(db, cursor, *args, **kwargs)

        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            if "cursor" in locals() and cursor:
                cursor.close()
            if "db" in locals() and db:
                db.close()
            # print("Database connection closed")
            if results is not None:
                return results

    return make_connection


@connect_to_database
def get_current_listing_urls(db, cursor):
    try:
        cursor = db.cursor(dictionary=True)

        table_name = "listings"

        query = f"SELECT agent, link_url, ref  FROM {table_name};"

        cursor.execute(query)

        results = cursor.fetchall()

        return results

    except Exception as e:
        print(f"An error occurred: {str(e)}")


@connect_to_database
def select_listings_by_link_url(db, cursor, urls):
    """Allows multiple rows to be selected if their link_url field is in the provided list. Used for testing.

    Args:
        db: Database object provided by decorator
        cursor: Cursor object provided by decorator
        urls (lst[str]): List of urls to search for

    Returns:
        list of matching rows
    """
    try:
        cursor = db.cursor(dictionary=True)

        query = f"SELECT agent, link_url, ref  FROM listings WHERE FIND_IN_SET(link_url, %s);"

        value = (",".join(urls),)
        cursor.execute(query, value)

        results = cursor.fetchall()

        return results

    except Exception as e:
        print(f"Failed to select listings using urls: {str(e)}")


@connect_to_database
def select_sold_urls(db, cursor):
    """Returns a set containing all urls identified as sold from image analyser from sold_urls table.

    Returns:
       set(sold_urls)
    """
    try:
        query = f"SELECT urls FROM sold_urls;"

        cursor.execute(query)

        results = cursor.fetchall()

        return set([result[0] for result in results])

    except Exception as e:
        print(f"Failed to select sold_urls: {str(e)}")


@connect_to_database
def select_primary_image_url(db, cursor, agents_to_check):
    """Returns a list with the url of the primary image for all listing agents that use text overlay on image to indicate unavailable properties. This is used for the sold image scanner.

    Args:
        agents_to_check (list): list of the full name of all listing agents to check.

    Returns:
        list[dict]: "link_url": url of main listing, "photos": url of primary photo to scan
    """
    try:
        cursor = db.cursor(dictionary=True)

        agents_tuple = (",".join(agents_to_check),)

        query = f"SELECT agent, link_url, photos FROM listings WHERE FIND_IN_SET(agent, %s);"

        cursor.execute(query, agents_tuple)

        results = cursor.fetchall()

        results_with_photos = []

        # Ensures that only results with photos are passed through for scanning, and returns only the url for the primary photo
        for result in results:
            if result["photos"]:
                result["photos"] = result["photos"].split(":;:")[0]
                results_with_photos.append(result)

        return results_with_photos

    except Exception as e:
        print(f"Failed to select primary image urls: {str(e)}")


@connect_to_database
def delete_row_id(db, cursor, table_name, id_to_delete):
    """Allows individual rows to be deleted from database using UUID (listingID)

    Args:
        db object
        cursor object
        table_name (str): Table name
        id_to_delete (int): listingID
    """
    try:
        query = f"DELETE FROM {table_name} WHERE listingID = %s"
        value = (id_to_delete,)
        cursor.execute(query, value)
        db.commit()
        print(f"Deleted UUID {id_to_delete} from {table_name} successfully")
    except Exception as e:
        print(f"Failed to delete UUID {id_to_delete}: {str(e)}")


@connect_to_database
def delete_listings_by_url_list(db, cursor, urls_to_delete):
    """Allows multiple rows to be deleted from database if their url (link_url) is in the provided list.

    Args:
        db object
        cursor object
        table_name (str): Table name
        urls_to_delete (lst[str]): list of urls to delete
    """
    try:
        query = f"DELETE FROM listings WHERE FIND_IN_SET(link_url, %s);"
        value = (",".join(urls_to_delete),)
        cursor.execute(query, value)
        db.commit()
        print(f"Deleted {len(urls_to_delete)} entries from listings successfully\n")
    except Exception as e:
        print(f"Failed to delete listings by url list: {str(e)}")


@connect_to_database
def delete_duplicates_by_specific_key(db, cursor, key):
    """Run this to delete all rows with duplicate values for the given key. Should only really be used for link_url, but may have other applications. Be careful not to use on "agent" etc

    Args:
        key: All listings with the same key after the first will be deleted.
    """
    try:
        query = f"DELETE listings FROM listings INNER JOIN (SELECT {key}, MIN(listingID) as min_id FROM listings GROUP BY {key}) AS duplicate_rows ON listings.{key} = duplicate_rows.{key} AND listings.listingID != duplicate_rows.min_id;"

        cursor.execute(query)
        db.commit()
    except Exception as e:
        print(f"Failed to delete listings by url list: {str(e)}")


@connect_to_database
def create_listings_table(db, cursor):
    """Creates the main listings table to store listings data. Schema is hard coded into function. db object does not need to be passed in as COMMIT is auto performed when using DDL statements with MySQL.

    Args:
        cursor: cursor object
    """
    # Character sets changed for columns to minimize size, particularly for description and photos. utf8 char assumed to be 4 bytes each, so 16383 chars* 4 bytes = 65,532, which is the max under the total row size limit of 65535 bytes. latin1 and ascii chars are 1 byte each.
    columns_string = "listingID int PRIMARY KEY AUTO_INCREMENT, types VARCHAR(11), town VARCHAR(255), postcode CHAR(5), price INT UNSIGNED, agent VARCHAR(50), ref VARCHAR(30), bedrooms SMALLINT UNSIGNED, rooms SMALLINT UNSIGNED, plot MEDIUMINT UNSIGNED, size MEDIUMINT UNSIGNED, link_url VARCHAR(1024), description VARCHAR(14000), photos TEXT, photos_hosted TEXT, gps POINT, id VARCHAR(80), types_original VARCHAR(30)"

    # Total bytes used with description as TEXT: Approx 6089 bytes. Max size is 65,535, so 59,446 bytes remain. Divided by 4 for utf8mb4 charset gives approx 14,861 VARCHAR length available to use. This is roughly double the maximum length of descriptions scraped so far, so should be safe to try using. Description changed from TEXT to VARCHAR(14000) to improve query performance.

    create_table_query = f"CREATE TABLE IF NOT EXISTS listings ({columns_string});"
    cursor.execute(create_table_query)
    print(f'Table "listings" created in "{database}" database successfully')


@connect_to_database
def create_sold_urls_table(db, cursor):
    """Creates the table to hold urls of sold images detected by the image scanner. Schema is hard coded into function. db object does not need to be passed in as COMMIT is auto performed when using DDL statements with MySQL."""
    columns_string = "id int PRIMARY KEY AUTO_INCREMENT, urls VARCHAR(10000) NOT NULL"

    create_table_query = f"CREATE TABLE IF NOT EXISTS sold_urls ({columns_string});"
    cursor.execute(create_table_query)
    print(f'Table "sold_urls" created successfully')


@connect_to_database
def add_listings(db, cursor, listings):
    """This function takes a list of dictionaries, listings, inserts them into the listings table, and commits the data. Insertion is done separately for listings with GPS data, and listings without. This is due to the inability to use placeholders inside the MySQL POINT syntax.

    Args:
        db: database object
        cursor: cursor object
        listings (lst[dict]): list of listing dictionaries
    """

    def gps_insert_data_to_table(cursor, columns_raw, gps_listing_values_list):
        gps_string = "ST_GeomFromText('POINT(%(lat)s %(lon)s)', 4326)"

        # Creates a string of csv %(key)s placeholders for the values to be inserted
        placeholders = ", ".join(f"%({key})s" for key in columns_raw)

        # Creates a string of columns to be inserted
        columns = ", ".join(columns_raw)

        insert_query = f"INSERT INTO listings (gps, {columns}) VALUES ({gps_string}, {placeholders})"

        cursor.executemany(insert_query, gps_listing_values_list)

    def no_gps_insert_data_to_table(cursor, columns_raw, no_gps_listing_values_list):
        # Creates a string of csv %s placeholders for the values to be inserted
        placeholders = ", ".join(f"%({key})s" for key in columns_raw)

        # Creates a string of columns to be inserted
        columns = ", ".join(columns_raw)

        insert_query = f"INSERT INTO listings ({columns}) VALUES ({placeholders})"

        cursor.executemany(insert_query, no_gps_listing_values_list)

    print("\nAdding data...")

    columns = [
        "types",
        "town",
        "postcode",
        "price",
        "agent",
        "ref",
        "bedrooms",
        "rooms",
        "plot",
        "size",
        "link_url",
        "description",
        "photos",
        "photos_hosted",
        "types_original",
    ]

    gps_listing_values_list = []
    no_gps_listing_values_list = []

    try:
        for listing in listings:
            if listing.get("gps"):
                # Create a dictionary with all possible fields to work with executemany INSERT query. List types converted to csv (:;:), other values inserted as found, and "gps" converted to seperate lat and lon fields for POINT field
                listing_dict = {}
                for key in columns:
                    if isinstance(listing.get(key), list):
                        listing_dict[key] = ":;:".join([str(x) for x in listing[key]])
                    else:
                        listing_dict[key] = listing.get(key)

                listing_dict["lat"] = round(listing["gps"][0], 6)
                listing_dict["lon"] = round(listing["gps"][1], 6)

                gps_listing_values_list.append(listing_dict)

            else:
                listing_dict = {}
                for key in columns:
                    if isinstance(listing.get(key), list):
                        listing_dict[key] = ":;:".join([str(x) for x in listing[key]])
                    else:
                        listing_dict[key] = listing.get(key)

                no_gps_listing_values_list.append(listing_dict)

        # Add all listings that have GPS coordinates and commit
        if gps_listing_values_list:
            # print("Adding GPS listings")
            gps_insert_data_to_table(cursor, columns, gps_listing_values_list)
            db.commit()
            # print("Listings with GPS data added successfully")

        # Add all listings that have no GPS coordinates and commit
        if no_gps_listing_values_list:
            # print("Adding non GPS listings")
            no_gps_insert_data_to_table(cursor, columns, no_gps_listing_values_list)
            db.commit()
            # print("Listings without GPS data added successfully")

        print(f"All data added successfully")
    except Exception as e:
        print(f"Failed to add data: {str(e)}")


@connect_to_database
def add_sold_urls_to_database(db, cursor, sold_urls):
    try:
        """Takes a list of sold urls and inserts them into the sold_urls table.

        Args:
            sold_urls (list[str]): List of all sold urls to be inserted
        """
        insert_query = f"INSERT INTO sold_urls (urls) VALUES (%s);"

        cursor.executemany(insert_query, [(url,) for url in sold_urls])
        db.commit()

    except Exception as e:
        print(f"Failed to insert sold urls: {str(e)}")


if __name__ == "__main__":
    ssh = open_SSH_tunnel()
    close_SSH_tunnel(ssh)
