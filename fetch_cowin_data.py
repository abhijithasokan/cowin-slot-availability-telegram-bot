import json
import requests
from urllib.parse import urlencode
import operator
from cachetools import cachedmethod, TTLCache
from cachetools.keys import hashkey
import time
import os
from collections import defaultdict

import logging
logging.basicConfig(level=logging.INFO)

class CowinDataConnector:
    ROOT_URL = 'https://cdn-api.co-vin.in'
    PIN_URL = ROOT_URL + '/api/v2/appointment/sessions/public/calendarByPin' #?pincode=%d&date=02-05-2021
    DIST_URL = ROOT_URL + '/api/v2/appointment/sessions/public/calendarByDistrict' #?district_id=114&date=07-05-2021'
    STATE_LIST_URL = ROOT_URL + '/api/v2/admin/location/states'
    DISTRICT_LIST_URL = ROOT_URL + '/api/v2/admin/location/districts/'
    STATES_FILE_NAME = 'fetched_data/states.json'

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

    
    ONE_DAY = 60*60*24
    QUATER_DAY = ONE_DAY / 4

    def __init__(self, response_cache_time = 120, max_cache_records = 1024):
        self.cache = TTLCache(maxsize=max_cache_records, ttl=response_cache_time)
        self.cache_state_data = TTLCache(maxsize=2, ttl=CowinDataConnector.ONE_DAY)
        self.session = requests.session()
        self.session.headers.update(CowinDataConnector.HEADERS)

    def _build_url(self, url, **kwargs):
        return url + '?' + urlencode(kwargs)

    # def _build_url(self, pin_code, date_str):
    #     query_data = { 'pincode' : pin_code, 'date' : date_str }
    #     return CowinDataConnector.PIN_URL + '?' + urlencode(query_data)


    @cachedmethod(operator.attrgetter('cache'))
    def _fetch_data_helper(self, area_code, date_str, is_pin_code_based):
        if is_pin_code_based:
            url = self._build_url(CowinDataConnector.PIN_URL, pincode=area_code, date=date_str)
        else:
            url = self._build_url(CowinDataConnector.DIST_URL, district_id=area_code, date=date_str)

        response = self.session.get(url)
        logging.info('GET: {}'.format(url))
        if response.status_code != 200:
            logging.error("API request failed {}. Resp - {}".format(url, response.text))
            return None
        try:
            data = json.loads(response.text)
        except:
            data = {}
        return data


    def _fetch_states_and_districts_and_dump(self):
        logging.info("-- fetch_states_and_districts_and_dump()")
        response = self.session.get(CowinDataConnector.STATE_LIST_URL)
        if response.status_code != 200:
            return None
        states_data = json.loads(response.text)
        state_name_to_id = {}
        state_to_district_names = defaultdict(list)
        district_name_to_id = {}
        for state in states_data['states']:
            state_id = state['state_id']
            state_name_to_id[state['state_name']] = state_id

            response2 = self.session.get(CowinDataConnector.DISTRICT_LIST_URL + str(state['state_id']))
            if response2.status_code != 200:
                return None

            district_data = json.loads(response2.text)
            for district in district_data['districts']:
                district_name, district_id = district['district_name'], district['district_id']
                district_name_to_id[district_name] = district_id
                state_to_district_names[state_id].append(district_name)
            
        with open(CowinDataConnector.STATES_FILE_NAME, 'w') as fp:
            data = {
                'state_name_to_id': state_name_to_id, 
                'state_to_district_names': state_to_district_names, 
                'district_name_to_id' : district_name_to_id,
                'district_id_to_name' : { val:key for key, val in district_name_to_id.items() }
            }
            #print(data)
            json.dump(data, fp)
            return data


    @cachedmethod(operator.attrgetter('cache_state_data'))
    def get_states_data(self):
        logging.info("-- get_states_data()")
        try: 
            data = self. _fetch_states_and_districts_and_dump()
        except:
            data = None

        if data is None:
            # try from disk
            with open(CowinDataConnector.STATES_FILE_NAME, 'r') as fp:
                data = json.load(fp)
        return data 

        
    def fetch_states_and_districts_from_disk(self):
        if os.path.exists(CowinDataConnector.STATES_FILE_NAME):
            with open(CowinDataConnector.STATES_FILE_NAME) as fp:
                data = json.load(fp)
                return data

    def _update_pin_code_cache_with_district_data(self, dist_data: dict, date_str: str):
        data: Any = dist_data.get('centers', None)
        if data is None:
            return
        pin_code_to_centers = defaultdict(list)
        for center in data:
            pin_code_to_centers[str(center['pincode'])].append(center)
        new_cache_entries = [((pin_code, date_str, True), {'centers': centers}) for pin_code, centers in
                             pin_code_to_centers.items()]
        self.cache.update(new_cache_entries)
        return

    def fetch_data(self, area_code, date, is_pin_code_based = False):
        date_str = date.strftime("%d-%m-%Y")
        area_code = str(area_code)
        data = self._fetch_data_helper(area_code, date_str, is_pin_code_based)
        if data is None:
            self.cache.pop(hashkey(area_code, date_str, is_pin_code_based), None)
            logging.error("API returned empty data. {}".format(area_code))
        else:
            if not is_pin_code_based: # area type is district
                self._update_pin_code_cache_with_district_data(data, date_str)

        return data



