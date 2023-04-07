import requests
from PIL import Image
import io
import json
import os

cwd = os.getcwd()   # Sets the current working directory to cwd

with open("listings.json", "r") as infile:
    listings = json.load(infile)

def dl_comp_photo(URL, ref, filename, cwd):     # This function goes to am image URL, downloads the image, compresses it, creates a folder for it with the name as the ref of the property listing, and saves the image to that folder with sequential name 0, 1, 2 etc.

    response = requests.get(URL, stream = True)
    response.raw.decode_content = True

    img = response.content
    image = Image.open(io.BytesIO(img))
    image = image.convert('RGB')    # converts to RGB so it can be saved as a jpg, RGBA cannot be saved to jpg so was causing errors
    image.thumbnail([500, 500])

    image_path = f"static/images/{ref}"
    try:
        os.mkdir(f"{cwd}/{image_path}")  # Checks if the "ref" folder exists for the property and creates it if not present
    except:
        pass
    # print(f"{cwd}/{image_path}/{filename}.jpg")
    image.save(f"{cwd}/{image_path}/{filename}.jpg", 
                    "JPEG", 
                    optimize = True, 
                    quality = 50)
    
def get_ami_images():
    for listing in listings:
        if listing["agent"] == "Ami Immobilier":
            for i in range(len(listing["photos"])):
                dl_comp_photo(listing["photos"][i], listing["ref"], i, cwd)
    print("Ami image download complete.")

#get_ami_images()
