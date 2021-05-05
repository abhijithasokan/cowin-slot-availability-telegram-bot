import json
import requests
from urllib.parse import urlencode
import operator
from cachetools import cachedmethod, TTLCache
from cachetools.keys import hashkey
import time


class CowinDataConnector:
    ROOT_URL = 'https://cdn-api.co-vin.in'
    URL = ROOT_URL + '/api/v2/appointment/sessions/public/calendarByPin' #?pincode=%d&date=02-05-2021

    HEADERS = {
        'Host' : 'cdn-api.co-vin.in',
        'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language' : 'en-US,en;q=0.5',
        'Accept-Encoding' : 'gzip, deflate, br',
        'DNT' : '1',
        'Connection' : 'keep-alive',
        'Upgrade-Insecure-Requests' : '1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'TE': 'Trailers',
    }

    def __init__(self, response_cache_time = 120, max_cache_records = 1024):
        self.cache = TTLCache(maxsize=max_cache_records, ttl=response_cache_time)
        self.session = requests.session()
        self.session.headers.update(CowinDataConnector.HEADERS)

    def _build_url(self, pin_code, date_str):
        query_data = { 'pincode' : pin_code, 'date' : date_str }
        return CowinDataConnector.URL + '?' + urlencode(query_data)


    @cachedmethod(operator.attrgetter('cache'))
    def _fetch_data_helper(self, pin_code, date_str):
        url = self._build_url(pin_code, date_str)
        response = self.session.get(url)
        print("GET: ", url)
        if response.status_code != 200:
            print(response.text)
            return None  
        try: 
            data = json.loads(response.text)
        except:
            data = {}
        return data


    def fetch_data(self, pin_code, date):
        date_str = date.strftime("%d-%m-%Y")
        data = self._fetch_data_helper(pin_code, date_str)
        if data is None:
            self.cache.pop(hashkey(pin_code, date_str), None)
        return data


