import grequests
from geopy.geocoders import Nominatim

headers = {
    'authority': 'www.iadfrance.com',
    'cache-control': 'max-age=0',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'referer': 'https://www.iadfrance.fr/',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.9,tr-TR;q=0.8,tr;q=0.7',
}

def get_gps(town, postcode = ""):
    geolocator = Nominatim(user_agent="property-scraper")
    location = geolocator.geocode(town + " " + postcode + " France")
    gps = [location.latitude, location.longitude]
    return gps

def get_data(links, header=True):
    if header: 
        reqs = [grequests.get(link, headers=headers, stream=True) for link in links]
        resp = grequests.map(reqs)
    else:
        reqs = [grequests.get(link, stream=True) for link in links]
        resp = grequests.map(reqs) 
     
    data = []
    for i in range(len(resp)):
        data.append({'link': links[i], 'response': resp[i]})
    return data