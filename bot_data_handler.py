from collections import defaultdict
from datetime import datetime

from fetch_cowin_data import CowinDataConnector
from parse_data import CowinCenter
import json

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker 
from db_models import User

class BotDataHandler:
    AGE_MAPPING = {
        'Above 45' : 45,
        'Above 18' : 18,
        'All Age groups' : 0
    }
    def __init__(self):
        engine = create_engine('sqlite:///test.db')    
        self.db_session = sessionmaker(bind=engine)()

        self.data_conn = CowinDataConnector()
        

    def add_user(self, user, user_data):
        fname = user.first_name + ' ' + user.last_name
        age = BotDataHandler.AGE_MAPPING.get(user_data['age'], BotDataHandler.AGE_MAPPING['All Age groups'])
        self.db_session.merge(User(user_id = user.id, uname = user.username, fname = fname, 
                                    area_type = user_data['area_type'], area_code = user_data['area_code'], age_group = age))
        self.db_session.commit()


    def get_vaccine_centers_for_user(self, user_id):
        user = self.db_session.query(User).get(user_id)
        if user is None:
            raise Exception("User doesn't exist")

        area_code = user.area_code
        area_type = user.area_type
        print("------------------------", user)
        api_data = self.data_conn.fetch_data(area_code, datetime.now(), area_type == "pincode")
        if api_data:
            centers = list(CowinCenter.build_from_json(api_data.get("centers", [])))
        else:
            centers = None
        return centers



    def get_states_data(self):
        return self.data_conn.get_states_data()

 
        