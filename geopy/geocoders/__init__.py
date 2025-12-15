class Nominatim:
    def __init__(self, user_agent: str, timeout: int = 10):
        self.user_agent = user_agent
        self.timeout = timeout

    def geocode(self, query: str, addressdetails: bool = True, language: str = "en"):
        return None
