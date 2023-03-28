class Listing:
    def __init__(self, types, town, postcode, price, agent, ref, bedrooms, rooms, plot, size, link_url, description, photos, gps):
        self.types = types
        self.town = town
        self.postcode = postcode
        self.price = price
        self.agent = agent
        self.ref = ref
        self.bedrooms = bedrooms
        self.rooms = rooms
        self.plot = plot
        self.size = size
        self.link_url = link_url
        self.description = description
        self.photos = photos
        self.gps = gps

class Search:
    def __init__(self, min_beds, max_beds, min_price, max_price, type, agent, min_plot, max_plot, min_size, max_size, town, search_radius):
        self.min_beds = min_beds
        self.max_beds = max_beds
        self.min_price = min_price
        self.max_price = max_price
        self.type = type 
        self.agent = agent 
        self.min_plot = min_plot 
        self.max_plot = max_plot
        self.min_size = min_size
        self.max_size = max_size
        self.town = town
        self.search_radius = search_radius
