import requests
from PIL import Image
import io
import json
import os

cwd = os.getcwd()   # Sets the current working directory to cwd

with open("listings.json", "r") as infile:
    listings = json.load(infile)

def make_photos_dir(ref, cwd, agent):
    try:
      os.mkdir(f"{cwd}/static/images/{agent}")  # Checks if the "agent" folder exists for the listing and creates it if not present
    except:
      pass
    # print(URL)
    image_path = f"static/images/{agent}/{ref}"
    try:
        os.mkdir(f"{cwd}/{image_path}")  # Checks if the "ref" folder exists for the property and creates it if not present
    except:
        pass

def dl_comp_photo(URL, ref, filename, cwd, agent):     # This function goes to am image URL, downloads the image, compresses it, creates a folder for it with the name as the ref of the property listing, and saves the image to that folder with sequential name 0, 1, 2 etc.
    # print("dl_comp_photo ran")

    image_path = f"static/images/{agent}/{ref}"
    response = requests.get(URL, stream = True, timeout=3)
    response.raw.decode_content = True

    img = response.content
    image = Image.open(io.BytesIO(img))
    image = image.convert('RGB')    # converts to RGB so it can be saved as a jpg, RGBA cannot be saved to jpg so was causing errors
    image.thumbnail([500, 500])
    
    image.save(f"{cwd}/{image_path}/{filename}.jpg", 
                    "JPEG", 
                    optimize = True, 
                    quality = 50)

    print(f"Image saved for agent: {agent}, ref: {ref}, image: {filename}")

    return f"https://suspiciousleaf.pythonanywhere.com/{image_path}/{filename}.jpg"


