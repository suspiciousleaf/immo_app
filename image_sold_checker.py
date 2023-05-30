from PIL import Image
import time
import io
import json
from utilities import get_data
import concurrent.futures

# with open("listings.json", "r", encoding="utf8") as infile:
#     listings = json.load(infile)

def check_image_sold(image, agent):  # returns True if sold
    
    # Many agents use a specific colour to write "Vendu" etc over the listing first image, with no other indication that it is unavailable. The code below counts how many pixels in the image are approx that colour (with a narrow margin due to jpg compression) and calculates their percentage of the whole image. Anything above 0.1% is taken as positive.

    # Convert from bytes response object
    img1 = Image.open(io.BytesIO(image["response"].content))
    url = image["link"]
    # Converts image to RGB format to ensure each pixel tuple value has 3 values only
    img1.convert("RGB")

    # Converts the image to a low resolution thumbnail to speed up iterating through each pixel.
    img1.thumbnail((256, 256))
    # img1.show()

    # Returns the contents of the image as a sequence object containing RGB pixel values as tuples
    img_data = Image.Image.getdata(img1)

    # This dictionary stores the text colour used by each listing agent. Some use multiple text colours, some don't.
    colour_dict = {
    "Arthur Immo": [(244, 149, 5)], # yellow (47, 55, 62)
    "Cimm Immobilier": [(250, 5, 5), (240, 15, 15)],
    "Cabinet Jammes": [(5, 205, 250)],
    "M&M Immobilier": [(250, 250, 150), (250, 5, 5), (250, 250, 5), (5, 250, 250), (205, 250, 205)], # Some listings use a shade of blue that gives false positives for sky
    "Safti": [(230, 93, 12)],
    "Sextant": [(50, 205, 205), (5, 205, 250), (5, 177, 190)],
    "Time and Stone Immobilier": [(250, 5, 5), (250, 250, 5)] # Some listings use white text, this causes many false positives due to overexposed photos, so they are left in.
    }

    count = 0
    # Pixel RGB colour values must be within a margin of +/- 5 of the stated value, to allow for jpg compression altering some colours. 
    tolerance = 6

    for pixel in img_data:
        for colour_options in colour_dict[agent]:
            if all(colour_options[i] - tolerance < pixel[i] < colour_options[i] + tolerance for i in range(3)):
                count += 1
                break

    percentage = count / len(img_data) * 100

    # print(count)
    # print(f"{percentage:0.2f} %")
      
    # print(len(img_data))

    if agent == "arthur":   # Arthur requires a different percentage limit due to frequent large text on first image
        if percentage > 0.25:
          # print("Sold!")
          # print(url)
          return (True, url)
        else:
          return (False, url)    
    else:
        if percentage > 0.1:
          # print("Sold!", percentage)
          # print(url)
          return (True, url)
        else:
          # print("Available!", percentage)
          return (False, url)    

def filter_listings(raw_listings, available_listings):
    valid_listings = []
    for listing in raw_listings:
        # Ensures the listing has at least one image
        if listing["photos"]: 
          # If the image url is found in available_listings (list of all available image urls), append it to valid_listings
          if listing["photos"][0] in available_listings:  
            valid_listings.append(listing)
    return valid_listings

def remove_unavailable(test_listings, agent):
   
    # all_images = get_image_data_from(test_listings)

    sold_listings = []      # This will hold all unavailable listing urls
    available_listings = [] # This will hold all available listing urls

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Downloads the first image for all listings to be tested using get_data utility
        all_images = get_data([listing["photos"][0] for listing in test_listings]) 
        # Checks each image to see if it's available, True for sold, False for available. Returns (True, image url)
        results = executor.map(check_image_sold, (image for image in all_images), [agent for _ in all_images]) 
        for result in results:
          if result[0]:
              sold_listings.append(result[1])
          else:
              available_listings.append(result[1])

    valid_listings = filter_listings(test_listings, available_listings)


    # print(f"\n{agent} sold listings: {len(sold_listings)}")
    # pprint(sold_listings)

    # print(f"{agent} available listings: {len(available_listings)}")
    # pprint(available_listings)


    # print(f"Valid listings found for {agent}: {len(valid_listings)} / {len(test_listings)}")

    t1 = time.perf_counter()


    # print(f"Time taken: {t1-t0:.2f}s")

    return valid_listings

def sold_image_check(listings):
    
    # List of agents who require the first image to be scanned to check if the listing is under offer / sold
    agents = ["Arthur Immo", "Cimm Immobilier", "Cabinet Jammes", "M&M Immobilier", "Safti", "Sextant", "Time and Stone Immobilier"]

    available_listings = [] # Used to pass through valid lsitings, and untested agents
    test_listings = []      # This list contains all listings from an agent, so they can be tested
    for listing in listings:
      if listing["agent"] not in agents:  # Pass through all agents who aren't tested like this
        available_listings.append(listing)
      else:
        if not listing["photos"]: # Pass through any listings that have no photos available to test
          available_listings.append(listing)
        else:
          test_listings.append(listing) # Creates the list of listings to be tested

    for agent in agents:
      temp_list = []
      for listing in test_listings:
        if listing["agent"] == agent:
          temp_list.append(listing) # Creates a list with all listings from single agent to be tested
      try:
        available_listings.extend(remove_unavailable(temp_list, agent)) # Filter listings to be tested
      except Exception as e:
        available_listings.extend(temp_list)  # If error, passes whole list and reports
        print(f"{agent} filter failed: {e}")
      
    return available_listings

# print(len(listings))

# available_listings = sold_image_check(listings)
# print(len(available_listings))
# with open("listings_clean.json", "w" , encoding="utf-8") as outfile:
#    json.dump(available_listings, outfile, ensure_ascii=False)

