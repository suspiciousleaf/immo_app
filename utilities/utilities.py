import grequests
from geopy.geocoders import Nominatim

headers = {
    "authority": "www.iadfrance.com",
    "cache-control": "max-age=0",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "referer": "https://www.iadfrance.fr/",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9,tr-TR;q=0.8,tr;q=0.7",
}


def get_gps(town, postcode=""):
    geolocator = Nominatim(user_agent="property-scraper")
    location = geolocator.geocode(town + " " + postcode + " France")
    gps = [location.latitude, location.longitude]
    return gps


def get_data(links, header=True, prox=False):
    if prox:
        if header:
            reqs = [
                grequests.get(link, headers=headers, stream=True, proxies=proxy)
                for link in links
            ]
            resp = grequests.map(reqs)
        else:
            reqs = [grequests.get(link, stream=True, proxies=proxy) for link in links]
            resp = grequests.map(reqs)
    else:
        if header:
            reqs = [grequests.get(link, headers=headers, stream=True) for link in links]
            resp = grequests.map(reqs)
        else:
            reqs = [grequests.get(link, stream=True) for link in links]
            resp = grequests.map(reqs)

    data = []
    for i in range(len(resp)):
        data.append({"link": links[i], "response": resp[i]})
    return data


proxy = {
    "http": "http://158.160.56.149:8080",
    "http": "http://103.173.128.51:8080",
    "http": "http://201.182.251.142:999",
    "http": "http://95.216.75.78:3128",
    "http": "http://51.79.50.31:9300",
    "http": "http://202.131.159.210:80",
    "http": "http://41.76.145.136:443",
    "http": "http://188.168.25.90:81",
    "http": "http://64.225.8.82:9967",
    "http": "http://47.92.93.39:8888",
    "http": "http://201.184.24.13:999",
    "http": "http://213.52.102.66:80",
    "http": "http://3.132.30.131:80",
    "http": "http://41.76.145.136:3128",
    "http": "http://75.119.129.192:3128",
    "http": "http://161.35.197.118:8080",
    "http": "http://5.161.80.172:8080",
    "http": "http://201.158.48.74:8080",
    "http": "http://41.76.145.136:8080",
    "http": "http://51.159.115.233:3128",
    "http": "http://64.226.110.184:45212",
    "http": "http://65.21.110.128:8080",
    "http": "http://213.52.102.30:10800",
    "http": "http://50.232.250.157:8080",
    "http": "http://18.143.215.49:80",
    "http": "http://190.119.86.66:999",
    "http": "http://180.184.91.187:443",
    "http": "http://95.216.156.131:8080",
    "http": "http://5.78.83.35:8080",
    "http": "http://78.110.195.242:7080",
    "http": "http://213.32.75.88:9300",
    "http": "http://31.186.241.8:8888",
    "http": "http://209.38.250.139:45212",
    "http": "http://51.158.189.189:8080",
}
