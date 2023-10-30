import io
import concurrent.futures

from PIL import Image
from pprint import pprint

from utilities.utility_holder import get_data
from utilities.db_utilities import select_primary_image_url


def check_image_sold(image, agent: str) -> tuple():  # returns True if unavailable
    try:
        """Checks individual images to see if they likely have text overlay, indicating unavailable.

        Returns:
            (Bool, url)
            True if text overlay is detected, so True for sold properties
        """
        # Many agents use a specific colour to write "Vendu" etc over the listing first image, with no other indication that it is unavailable. The code below counts how many pixels in the image are approx that colour (with a narrow margin due to jpg compression) and calculates their percentage of the whole image. Anything above 0.1% is taken as positive.

        # Convert from bytes response object

        # If the image failed to download, return False
        url = image["link"]
        if image["response"].status_code != 200:
            print(
                f"{agent} image failed to download. HTTP code: {image['response'].status_code}, url: {url}"
            )
            return (False, url)

        img1 = Image.open(io.BytesIO(image["response"].content))

        # Converts image to RGB format to ensure each pixel tuple value has 3 values only
        img1.convert("RGB")

        # Converts the image to a low resolution thumbnail to speed up iterating through each pixel.
        img1.thumbnail((256, 256))

        # Arthur Immo sometimes puts a band of text at the top or bottom with their logo, this can interfere with the results. The code below crops the top and bottom 25% from each image so it can just scan the middle section, where "Sold" type graphics are palced.
        if agent == "Arthur Immo":
            width, height = img1.size
            new_height = int(height * 0.5)  # Keep 50% of the original height

            # Calculate the top and bottom coordinates for cropping
            top = (height - new_height) // 2
            bottom = top + new_height

            # Crop the image
            img1 = img1.crop((0, top, width, bottom))

        # img1.show()

        # Returns the contents of the image as a sequence object containing RGB pixel values as tuples
        img_data = Image.Image.getdata(img1)

        # This dictionary stores the text colour used by each listing agent. Some use multiple text colours, some don't.
        colour_dict = {
            "Arthur Immo": [(244, 149, 5)],  # yellow (47, 55, 62)
            "Cimm Immobilier": [(250, 5, 5), (240, 15, 15)],
            "Cabinet Jammes": [(5, 205, 250)],
            # Some M&M listings use a shade of blue that gives false positives for sky
            "M&M Immobilier": [
                (250, 250, 150),
                (250, 5, 5),
                (250, 250, 5),
                (5, 250, 250),
                (205, 250, 205),
            ],
            "Safti": [(230, 93, 12)],
            "Sextant": [(50, 205, 205), (5, 205, 250), (5, 177, 190)],
            # Some Time and Stone listings use white text, this causes many false positives due to overexposed photos, so they are left in
            "Time and Stone Immobilier": [
                (250, 5, 5),
                (250, 250, 5),
            ],
        }

        count = 0
        # Pixel RGB colour values must be within a margin of +/- 5 of the stated value, to allow for jpg compression altering some colours.
        tolerance = 6

        for pixel in img_data:
            for colour_options in colour_dict[agent]:
                if all(
                    colour_options[i] - tolerance
                    < pixel[i]
                    < colour_options[i] + tolerance
                    for i in range(3)
                ):
                    count += 1
                    break

        percentage = count / len(img_data) * 100

        # Arthur requires a different percentage limit due to frequent large text on first image. Most of this is cropped out, but sometimes a fancy font is used that extends beyond the cropping and causes false positives.
        if agent == "Arthur Immo":
            if percentage > 0.4:
                return (True, url)
            else:
                return (False, url)
        else:
            if percentage > 0.1:
                return (True, url)
            else:
                return (False, url)

    except Exception as e:
        print(f"Image scan failed for {url}: {str(e)}")
        return (False, url)


def remove_unavailable(test_listings: list, agent) -> set:
    # This will hold all unavailable listing urls
    sold_image_urls = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Downloads the first image for all listings to be tested using get_data utility
        all_images = get_data([listing["photos"] for listing in test_listings])

        # Checks each image to see if it's available, True for sold, False for available. Returns (True, image url)
        results = executor.map(
            check_image_sold,
            (image for image in all_images),
            [agent for _ in all_images],
        )

        for result in results:
            if result[0]:
                sold_image_urls.append(result[1])

    return set(sold_image_urls)


def sold_image_check() -> list:
    """Checks first image of listings to check for "Vendu" etc text overlay"""
    # List of agents who require the first image to be scanned to check if the listing is under offer / sold

    agents = [
        "Arthur Immo",
        "Cimm Immobilier",
        "Cabinet Jammes",
        "M&M Immobilier",
        "Safti",
        "Sextant",
        "Time and Stone Immobilier",
    ]

    test_listings = select_primary_image_url(agents)

    # This is used to store the urls of photos of unavailable properties
    sold_image_urls_set = set()
    for agent in agents:
        temp_list = [listing for listing in test_listings if listing["agent"] == agent]

        try:
            # Filter listings to be tested
            images_to_remove = remove_unavailable(temp_list, agent)
            print(f"Unavailable listings detected for {agent}: {len(images_to_remove)}")
            sold_image_urls_set.union(images_to_remove)

        except Exception as e:
            print(f"{agent} filter failed: {e}")

    listing_urls_to_remove = []

    for listing in test_listings:
        if listing["photos"] in sold_image_urls_set:
            listing_urls_to_remove.append[listing["link_url"]]

    print(f"Found {len(listing_urls_to_remove)} unavailable listings")
    return listing_urls_to_remove
