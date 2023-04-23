import grequests
from geopy.geocoders import Nominatim

def get_gps(town, postcode = ""):
    geolocator = Nominatim(user_agent="property-scraper")
    location = geolocator.geocode(town + " " + postcode + " France")
    gps = [location.latitude, location.longitude]
    return gps

def get_data(links): 
    reqs = [grequests.get(link, stream=True) for link in links]
    resp = grequests.map(reqs)
     
    data = []
    for i in range(len(resp)):
        data.append({'link': links[i], 'response': resp[i]})
    return data