
from datetime import datetime

class CowinDataParser():
    pass

class CowinCenterSession:
    def __init__(self, session_id, date, vaccine, available_capacity, min_age_limit):
        self.session_id_ = session_id
        self.date_ = date
        self.vaccine_ = vaccine
        self.available_capacity_ = available_capacity
        self.min_age_limit_ = min_age_limit

    @staticmethod
    def build_session_from_json(data):
        if isinstance(data, dict):
            data = [data]
        
        for session_d in data:
            kwargs = {
                'session_id' : session_d['session_id'],
                'date' : datetime.strptime(session_d['date'], "%d-%m-%Y"),
                'available_capacity' : session_d['available_capacity'],   
                'min_age_limit' : session_d['min_age_limit'],
                'vaccine' : session_d['vaccine'],
            }
            yield CowinCenterSession(**kwargs)
        return

    @staticmethod
    def get_session_msg(v_ss):
        msg = '''
________________________
| Date | Seats |  Age Lim |
'''
        for session in v_ss:
            msg += '|%s   %5d    %7d  \n'%(session.date_.strftime("%d/%m"), session.available_capacity_, session.min_age_limit_)
        msg += '________________________'
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
            kwargs = {
                'center_id' : center_d['center_id'],
                'name' : center_d['name'],
                'block_name' : center_d['block_name'],   
                'fee_type' : center_d['fee_type'],
                'sessions' : list(CowinCenterSession.build_session_from_json(center_d['sessions'])),
            }
            yield CowinCenter(**kwargs)
        return

    def __str__(self):
        ss = 'Center - {}, {}\n'.format(self.name_, self.block_name_)
        ss += 'Fee: {}'.format(self.fee_type_)
        ss += CowinCenterSession.get_session_msg(self.sessions_)
        return ss
