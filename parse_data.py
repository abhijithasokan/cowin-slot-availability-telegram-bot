from collections import defaultdict
from datetime import datetime
from emojis import EMOJIS

class CowinDataParser():
    pass

class CowinCenterSession:
    def __init__(self, session_id, date, vaccine, available_capacity, available_capacity_dose1, available_capacity_dose2, min_age_limit):
        self.session_id_ = session_id
        self.date_ = date
        self.vaccine_ = vaccine
        self.available_capacity_ = available_capacity
        self.available_capacity_dose1_ = available_capacity_dose1
        self.available_capacity_dose2_ = available_capacity_dose2
        self.min_age_limit_ = min_age_limit

    @staticmethod
    def build_session_from_json(data):
        if isinstance(data, dict):
            data = [data]
        
        for session_d in data:
            kwargs = {
                'session_id' : session_d['session_id'],
                'date' : datetime.strptime(session_d['date'], "%d-%m-%Y"),
                'available_capacity' : int(session_d['available_capacity']),
                'available_capacity_dose1' : int(session_d['available_capacity_dose1']),   
                'available_capacity_dose2' : int(session_d['available_capacity_dose2']),      
                'min_age_limit' : int(session_d['min_age_limit']),
                'vaccine' : session_d['vaccine'],
            }
            yield CowinCenterSession(**kwargs)
        return


    @staticmethod
    def build_and_get_filtered_sessions(data, filter_age, filter_capacity):
        for ss in CowinCenterSession.build_session_from_json(data):
            if ss.min_age_limit_ <= filter_age and ss.available_capacity_ >= filter_capacity:
                yield ss

    @staticmethod
    def get_session_msg(v_ss):
        vaccine_to_sessions = defaultdict(list)
        for session in v_ss:
            vaccine_to_sessions[session.vaccine_].append(session)
        msg = ''
        for vaccine, v_ss in vaccine_to_sessions.items():
            msg += '\nVaccine: {}'.format(vaccine.title())
            msg += '''
________________________________
| Date |     Age     |       Seats 
'''
            for session in v_ss:
                #vacc_name = session.vaccine_.title()[:min(10, len(session.vaccine_))]
                dte = session.date_.strftime("%d/%m")
                d1_cap = 'D1:{:3}'.format(session.available_capacity_dose1_ if session.available_capacity_dose1_ <= 999 else '1K+')
                d2_cap = 'D2:{:3}'.format(session.available_capacity_dose2_ if session.available_capacity_dose2_ <= 999 else '1K+')
                cap = '{}  {}'.format(d1_cap, d2_cap)
                msg += ' {0} {1: >8}        {2: >12}\n'.format(dte, session.min_age_limit_, cap)
            msg += '________________________________'
        return msg


class CowinCenter:
    def __init__(self, center_id, name, block_name, fee_type, sessions):
        self.center_id_ = center_id
        self.name_ = name
        self.block_name_ = block_name
        self.fee_type_ = fee_type
        self.sessions_ = sessions

    
    @staticmethod
    def build_from_json(json_data):
        data = [json_data] if not isinstance(json_data, list) else json_data

        for center_d in data:
            block_name = center_d['block_name']
            block_name = block_name if 'not applicable' not in block_name.lower() else ''
            kwargs = {
                'center_id' : center_d['center_id'],
                'name' : center_d['name'],
                'block_name' : block_name,   
                'fee_type' : center_d['fee_type'],
                'sessions' : list(CowinCenterSession.build_session_from_json(center_d['sessions'])),
            }
            yield CowinCenter(**kwargs)
        return


    @staticmethod
    def build_and_get_filtered_centers(json_data, filter_age, filter_capacity):
        data = [json_data] if not isinstance(json_data, list) else json_data

        for center_d in data:
            sessions = list(CowinCenterSession.build_and_get_filtered_sessions(center_d['sessions'], filter_age, filter_capacity))
            if sessions:
                block_name = center_d['block_name']
                block_name = block_name if 'not applicable' not in block_name.lower() else ''   
                kwargs = {
                    'center_id' : center_d['center_id'],
                    'name' : center_d['name'],
                    'block_name' : block_name,   
                    'fee_type' : center_d['fee_type'],
                    'sessions' : sessions,
                }
                yield CowinCenter(**kwargs)


    def __str__(self):
        ss = EMOJIS['hospital']  + ' {}, {}\n'.format(self.name_, self.block_name_)
        ss += 'Fee: {}'.format(self.fee_type_)
        ss += CowinCenterSession.get_session_msg(self.sessions_)
        ss += '\n\n'
        return ss
