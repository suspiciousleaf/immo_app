import io
import os
import subprocess

from PIL import Image

# Sets the current working directory to cwd
cwd = os.getcwd()


def make_photos_dir(ref: str, cwd, agent: str):
    """Creates a directory to save the downloaded photos in, a solfder for the agent and a folder for each listing within that."""
    try:
        # Checks if the "agent" folder exists for the listing and creates it if not present
        os.mkdir(f"{cwd}/static/images/{agent}")
    except:
        pass
    # print(URL)
    image_path = f"static/images/{agent}/{ref}"
    try:
        # Checks if the "ref" folder exists for the property and creates it if not present
        os.mkdir(f"{cwd}/{image_path}")
    except:
        pass


# This function goes to an image URL, downloads the image, compresses it, creates a folder for it with the name as the ref of the property listing, and saves the image to that folder with sequential name 0, 1, 2 etc.
def dl_comp_photo(response, ref, filename, cwd, agent):
    """Takes image as bytes, converts the image to RGB, resizes, saves, and returns the url where it will be hosted on PythonAnywhere"""

    image_path = f"static/images/{agent}/{ref}"
    img = response.content
    image = Image.open(io.BytesIO(img))
    # converts to RGB so it can be saved as a jpg, RGBA cannot be saved to jpg so was causing errors
    image = image.convert("RGB")
    image.thumbnail([1000, 1000])

    image.save(f"{cwd}/{image_path}/{filename}.jpg", "JPEG", optimize=True, quality=60)

    # print(f"Image saved for agent: {agent}, ref: {ref}, image: {filename}")

    return f"https://suspiciousleaf.eu.pythonanywhere.com/{image_path}/{filename}.jpg"


def sync_local_remote_image_directories():
    """This function uses rsync and wsl to synchronize the remote photo directory on PythonAnywhere with the local directory. New images added, old images deleted."""

    command = "wsl rsync -azh --delete static/images/ suspiciousleaf@ssh.eu.pythonanywhere.com:immo_app/static/images/"

    try:
        print("\nPhoto sync beginning...")
        subprocess.run(command, shell=True, text=True)
        print("Photo sync complete.")
    except Exception as e:
        print("An error occured during photo sync: " + str(e))
