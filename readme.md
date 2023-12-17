# Web scraper to gather listings from all estate agents covering a specific area, and serve the data up with an API.

### My region lacks a single website where all estate agents post their listings so they can all be searched in one place. The goal of this project is to create a web scraper that will scrape all listings from the estate agents, make the data as uniform as possible, extract available data so that it can be searched more easily, stored in a MySQL database, and finally hosted in the form of an API that can be queried by the front end.
<br>
Many agents are individual offices and there is no consistency between their advertising. Quality of information also varies considerably between agents. 

<br>
<br>

# Live version
The live site including front end can be accessed [here](https://immobee.netlify.app/).

<br>

# How it works
## Short version:
A scraper will run for each estate agent, that will find all the listings available for that agent, compare it to previous data, delete any listings no longer online, and add the data for newly added listings. The data is stored in a `MySQL` database for the `API` to use. 
<br>
Running `app.py` runs the scraper, running `flask_app.py` hosts the `API`.
<br>
<br>
Data is normalized as much as possible, the string scraped for location is verified to be a valid town name, as much data as possible is extracted, and exceptions are printed to the terminal.
<br>
<br>
If `host_photos` is set to `True` when calling the main scraper function, in addition to scraping each listing page, the program will download all photos, compress them, and save them to a new local directory. These will then be hosted on [PythonAnywhere](https://www.pythonanywhere.com/). This is necessary for *Richardson*, which is HTTP only so cannot embed images using HTTPS, and *Ami*, which blocks leeching. 
Photos for old listings will be deleted when the listing is taken down from the agent website. `Rsync` is used to synchronize the hosted directory images with the local ones at the end fo each run of the scraper.
<br>
<br>

## Long version:
When `app.py` is run, the program will run an individual scraper for each estate agent. At present, 24 agents are included. 
The scrapers follow the same process for (almost) all agents. They start by finding the total number of listings that the agent has, dividing that by the number of listings per search page (currently hard coded) to find how many search pages to expect, generate the url for each search page, and scrape each of those to get the urls for all available listings.
<br>
Previously scraped listing urls are retrieved from the database and compared to the newly available ones. Listings in the database that are no longer online will be deleted, and ones found online but not yet in the database will be scraped.
<br>
These urls are passed to the next function, that scrapes the individual listing page and returns the data as a dictionary. Once all urls have been scraped, the list is returned to `app.py` and the next agent scraper begins. 
<br>
Once all scrapers have run, the *Type* of each listing is checked in an attempt to fit them in to one of *House, Apartment, Multi-occupancy building, Land, Commercial,* or *Other*. If the type doesn't fit into one fo the first five, it will be set to *Other*, and the scraped type will be set to a new value in the dictionary so it can be categorized later, and will also print to console.
After all agents have been scraped and data verified, a promt will appear to confirm if new listings should be added to the database, and another to confirm if old ones should be deleted.

Some scrapers run asynchronously using `grequests`, some run using multi-threading, and a couple directly access an `API` I found in network requests on page loading.
<br>
<br>
If `host_photos` is set to `True` when calling the main scraper function, in addition to scraping each listing page, the program will download all photos, compress them, and save them to a new local directory. These will then be uploaded and hosted on [PythonAnywhere](https://www.eu.pythonanywhere.com/). This is necessary for *Richardson*, which is HTTP only so cannot embed images using HTTPS, and *Ami*, which blocks leeching. 
Photos for old listings will be deleted when the listing is taken down from the agent website. `Rsync` is used to keep the hosted directory up to date.
<br>
<br>
Every 5 times the scraper runs, an additional function runs. Several agents leave sold properties online, the only change being a text overlay on the first image. "Vendu", "Trop tard" etc. This function downloads the first image for all agents who do this, compresses it to speed up processing, and then counts the number of pixels in that image that have the colour that agent uses for their text overlays. This is much more effective than using an OCR approach, since the text is often at strange angles, using different fonts, or other things which reduce OCR effectiveness. Since we don't care what the text says, only that it is present or not, this approach works with approx 99.5% accuracy. One agent sometimes uses white text which has to be ignored, since it triggers false positives on overexposed areas of photos.
Any listings detected as unavailable are removed from the database, and the url is added to another table to ensure that the listing isn't scraped again the next time it runs. 
<br>
<br>
# Difficulties encountered
## Location
The scrapers for *Richardson* and *Ami* run an additional function to verify their scraped location. The scraped string is checked against a dictionary of all town names scraped from a government website (this scraper is in `postcodes_gps_dict_maker.py`). If the scraped string is not in the database, the function will check for a valid postcode and use that to populate the town name, or scan through the description to see if a valid town is mentioned. If the town has to be determined this way, a disclaimer is added to the description that it might be inaccurate (eg, *beautiful property 30 minutes drive from Carcassonne* will set the location to Carcassonne).

## Bedrooms
*Richardson* has poor information on bedrooms, so an additional function `find_chamb` is run to try to extract that information from the description. It's a `regex` based approach that improves accuracy, but is still not perfect. 

<br>

# API
### Base URL:
https://suspiciousleaf.eu.pythonanywhere.com/search_results
<br>

### Query parameters:
<br>

| Keyword | Definition | Format | Default |
|---|---|---|---|
| agents  | Agents to include  | Comma-separated values   | Leave blank for all  |
| town     | Requested locations |  Comma-separated values | Leave blank for all |
| search_radius  | Radius around each of the above towns in km | Number | 0 |
| types | Types of property to include |  Comma-separated values | Leave blank for all |
| min_X, max_X  | Min and max values for price, bedrooms, rooms, land size("plot"), property size ("size")  | Number | |
| inc_none_X    | Include listings where X is not known. Bedrooms, location, land size, property size   | Boolean | True |
| keywords   | Keywords to search for in description, e.g. *garage* | Comma-separated values |
<br>
### An example query
<br>
https://suspiciousleaf.eu.pythonanywhere.com/search_results??town=11000-carcassonne&search_radius=25&types=Maison&min_beds=4&max_price=750000&min_plot=1000&min_size=100&max_size=300&inc_none_location=false&inc_none_size=false&inc_none_plot=false&keywords=piscine
<br>
<br>
This will return a `JSON` object with barebones details for each property in the search criteria. 

"agent": "Safti",
"listingID": 6257,
"plot": 1041,
"price": 279000,
"size": 102

These are the details used for sorting on the front end, and the primary key used on the database. This allows the front end to sort results, control pagination, save listings to a favourite or block list locally, and then query the back end for the complete listings required for each listing to be shown on that page using `listingID`.

Example query for full listing:
<br>
https://suspiciousleaf.eu.pythonanywhere.com/full_listings?id=14554,13328,14144,13867,15570,15386,15591,13868,15389,14134,15394,14125
<br>
<br>

# How to run

To run the scraper, run `app.py`.
<br>
The `API` is run by running `flask_app.py`. It can then be accessed on `localhost:105`.

<br><br>

# Known areas to work on in the future
- Some code is common to all scrapers and could be separated into utility methods in `utilities.py`. Examples include:
  - Deleting downloaded photos for listings that have been taken down (the only part of the code that uses [shutil](https://docs.python.org/3/library/shutil.html))
  - Checking the town / postcode at the end of each `get_listing_details()` and setting the GPS coordinates.
<br>
<br>

- Additional comments to explain more intricate use cases.
<br>

- The possibility of integrating a proxy should be more thoroughly investigated to potentially improve the scraping speed for some agents. The main gain would be seen when running the scraper for the first time, which takes several minutes, because on each subsequent run very few additional listings are typically scraped. This means that any gains in requests per second may end up being lost to increases in latency. 