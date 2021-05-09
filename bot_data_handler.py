from collections import defaultdict
from datetime import datetime

from fetch_cowin_data import CowinDataConnector
from parse_data import CowinCenter
import json

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker 
from db_models import User, get_db_login_info

from collections import defaultdict

class BotDataHandler:
    AGE_MAPPING = {
        'Above 45' : 45,
        'Above 18' : 18,
        'All Age groups' : 200
    }


    def __init__(self):
        db_login_info = get_db_login_info()
        host, db_name, user_name, password = db_login_info['host'], db_login_info['name'], db_login_info['username'], db_login_info['password']
        engine = create_engine("mysql+pymysql://{}:{}@{}/{}?charset=utf8mb4".format(user_name, password, host, db_name))
    
        self.db_session = sessionmaker(bind=engine)()

        self.data_conn = CowinDataConnector()
        

    def add_user(self, user, user_data):
        fname = (user.first_name if user.first_name else '') + ' ' + (user.last_name if user.last_name else None)
        uname = user.username if user.username else ''
        age = BotDataHandler.AGE_MAPPING.get(user_data['age'], BotDataHandler.AGE_MAPPING['All Age groups'])
        self.db_session.merge(User(user_id = user.id, uname = uname, fname = fname, 
                                    area_type = user_data['area_type'], area_code = user_data['area_code'], age_group = age))
        self.db_session.commit()


    def get_vaccine_centers_for_user(self, user_id):
        user = self.db_session.query(User).get(user_id)
        if user is None:
            raise Exception("User doesn't exist")

        area_code = user.area_code
        area_type = user.area_type
        age = user.age_group
        print("--------", user)
        api_data = self.data_conn.fetch_data(area_code, datetime.now(), area_type == "pincode")
        if api_data:
            centers = list( CowinCenter.build_and_get_filtered_centers(api_data.get("centers", []), age, 1) )
        else:
            centers = None
        return centers


    def get_filtered_data_for_location(self, age_groups, area_code, is_pincode, slot_threshold = 1):
        api_data = self.data_conn.fetch_data(area_code, datetime.now(), is_pincode)
        if not api_data:
            return None
        
        for age_grp in age_groups:
            centers = list( CowinCenter.build_and_get_filtered_centers(api_data.get("centers", []), age_grp, slot_threshold) )
            yield (age_grp, centers)


    def get_states_data(self):
        return self.data_conn.get_states_data()

    def get_dist_code_to_name(self):
        data = self.data_conn.fetch_states_and_districts_from_disk()
        if data is not None:
            name_to_id =  data['district_name_to_id']
            return { val: key for (key, val) in name_to_id.items() }


    def segregate_user_groups(self):
        users = self.db_session.query(User).all()

        #age_gps = BotDataHandler.AGE_MAPPING.values()
        dist_to_age_to_user_ids = defaultdict( lambda : defaultdict(list) )
        pincode_to_age_to_user_ids = defaultdict( lambda : defaultdict(list) )
        for uu in users:
            user_id = uu.user_id
            area_type = uu.area_type
            area_code = int(uu.area_code)
            age_group = int(uu.age_group)
            if area_type == 'pincode':
                pincode_to_age_to_user_ids[area_code][age_group].append(user_id)
            else:
                dist_to_age_to_user_ids[area_code][age_group].append(user_id)

            
        return dist_to_age_to_user_ids, pincode_to_age_to_user_ids

    @staticmethod
    def get_chunked_msg_text(items, max_len):
        if not items:
            return []
        chunks = [str(items[0])]
        for item in items[1:]:
            ss = str(item)
            if (len(chunks[-1]) + len(ss) + 3)>= max_len:
                chunks.append(ss)
            else:
                chunks[-1] = chunks[-1] + '\n' + ss
        return chunks


    def get_age_str(self, age_str):
        return age_str.lower().replace('groups', '').replace('group', '').replace('age','').title()

    def get_rev_age_mapping(self, age):
        rev_map = { val:key for (key, val) in BotDataHandler.AGE_MAPPING.items() }
        ss = rev_map[age]
        return self.get_age_str(ss)