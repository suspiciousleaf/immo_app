class Listing:
    def __init__(
        self,
        types,
        town,
        postcode,
        price,
        agent,
        ref,
        bedrooms,
        rooms,
        plot,
        size,
        link_url,
        description,
        photos,
        photos_hosted,
        gps,
    ):
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
        self.photos_hosted = photos_hosted
        self.gps = gps
