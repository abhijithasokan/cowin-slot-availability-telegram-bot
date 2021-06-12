from collections import defaultdict
from datetime import datetime

from fetch_cowin_data import CowinDataConnector
from parse_data import CowinCenter, CowinCenterSession
import json

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker 
from db_models import User, UserActivity, AreaUpdate, get_db_login_info

from collections import defaultdict


class BotDataHandler:
    AGE_MAPPING_IN_ORDER = [ ('Above 45', 45), ('All Age groups', CowinCenterSession.ALL_AGE), ('Above 18', 18) ]
    AGE_MAPPING = dict(AGE_MAPPING_IN_ORDER)
    REV_AGE_MAPPING = { val:key for key, val in AGE_MAPPING.items()}

    def __init__(self, response_cache_time):
        db_login_info = get_db_login_info()
        host, db_name, user_name, password = db_login_info['host'], db_login_info['name'], db_login_info['username'], db_login_info['password']
        engine = create_engine("mysql+pymysql://{}:{}@{}/{}?charset=utf8mb4".format(user_name, password, host, db_name))
    
        self.db_session = sessionmaker(bind=engine)()

        self.data_conn = CowinDataConnector(response_cache_time=response_cache_time)
        

    def add_user(self, user, user_data):
        fname = (user.first_name if user.first_name else '') + ' ' + (user.last_name if user.last_name else '')
        uname = user.username if user.username else ''
        age = BotDataHandler.AGE_MAPPING.get(user_data['age'], BotDataHandler.AGE_MAPPING['All Age groups'])
        self.db_session.merge(User(user_id = user.id, uname = uname, fname = fname, 
                                    area_type = user_data['area_type'], area_code = user_data['area_code'], age_group = age, is_subscribed = True))
        self.db_session.commit()


    def stop_update_for_user(self, user_id):
        user = self.db_session.query(User).get(user_id)
        if (user is not None) and user.is_subscribed == True:
            user.is_subscribed = False
            self.db_session.commit()


    def resume_update_for_user(self, user_id):
        user = self.db_session.query(User).get(user_id)
        if (user is not None) and user.is_subscribed == False:
            user.is_subscribed = True
            self.db_session.commit()

    def get_area_str(self, area_code, area_type):
        area_code = int(area_code)
        if area_type == 'pincode':
            return '[pin] {}'.format(area_code)
        else:
            return self.get_states_data()['district_id_to_name'].get(area_code, '[district] %d'%area_code)

    def get_vaccine_centers_for_user(self, user_id):
        user = self.db_session.query(User).get(user_id)
        if user is None:
            raise Exception("User doesn't exist")  # handled later?

        area_code = user.area_code
        area_type = user.area_type
        age = user.age_group
        print("--------", user)
        api_data = self.data_conn.fetch_data(area_code, datetime.now(), area_type == "pincode")
        if api_data:
            centers = list( CowinCenter.build_and_get_filtered_centers(api_data.get("centers", []), age, 1) )
        else:
            centers = None

        no_vaccine_msg = None
        if centers is not None and len(centers) == 0:
            # no vaccination centers
            no_vaccine_msg = 'Currently no vaccination slots are available in {} for age group {}'.format(self.get_area_str(area_code, area_type), self.get_age_str2(age))
        return centers, no_vaccine_msg


    def get_filtered_data_for_location(self, age_groups, area_code, is_pincode, slot_threshold = 1):
        api_data = self.data_conn.fetch_data(area_code, datetime.now(), is_pincode)
        if not api_data:
            return None
        
        for age_grp in age_groups:
            centers = list( CowinCenter.build_and_get_filtered_centers(api_data.get("centers", []), age_grp, slot_threshold) )
            yield (age_grp, centers)


    def get_states_data(self):
        return self.data_conn.get_states_data()

    def get_dist_code_to_name_from_disk(self):
        data = self.data_conn.fetch_states_and_districts_from_disk()
        if data is not None:
            return data['district_id_to_name']

    def segregate_user_groups(self):
        users = self.db_session.query(User).filter_by(is_subscribed=True)

        #age_gps = BotDataHandler.AGE_MAPPING.values()
        dist_to_age_to_user_ids = defaultdict( lambda : defaultdict(list) )
        pincode_to_age_to_user_ids = defaultdict( lambda : defaultdict(list) )
        for uu in users:
            user_id = uu.user_id
            area_type = uu.area_type
            area_code = uu.area_code
            age_group = int(uu.age_group)
            if area_type == 'pincode':
                pincode_to_age_to_user_ids[area_code][age_group].append(user_id)
            else:
                dist_to_age_to_user_ids[area_code][age_group].append(user_id)

            
        return dist_to_age_to_user_ids, pincode_to_age_to_user_ids


    def update_broadcast_count_for_users(self, user_ids):
        for user_id in user_ids:
            user = self.db_session.query(UserActivity).get(user_id)
            if not user:
                user = UserActivity(user_id = user_id, broadcast_msg_count = 1, last_broadcast_time = datetime.now())
                self.db_session.add(user)
            else:
                user.last_broadcast_time = datetime.now()
                user.broadcast_msg_count += 1
        self.db_session.commit()


    def get_area_update_record(self, area_type, area_code, age_gp):
        age_gp = int(age_gp)
        area_rec = self.db_session.query(AreaUpdate).filter_by(area_type = area_type, area_code = area_code, age_gp = age_gp).first()
        if not area_rec:
            area_rec = AreaUpdate(area_type = area_type, area_code = area_code, age_gp = age_gp)
            self.db_session.add(area_rec)
        return area_rec

    def update_area_rec(self, area_rec, area_update_summary):
        area_rec.last_update_time = datetime.now()
        area_rec.last_update = area_update_summary

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

    def commit_db_session(self):
        self.db_session.commit()

    def get_age_str(self, age):
        return str(age).lower().replace('groups', '').replace('group', '').replace('age','').title().strip()

    def get_age_str2(self, age):
        ss = BotDataHandler.REV_AGE_MAPPING[age]
        return self.get_age_str(ss)