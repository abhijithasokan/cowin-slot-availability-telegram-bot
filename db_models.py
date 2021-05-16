from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy import Sequence


Base = declarative_base()

# AGE_GROUPS = {
#     'Above 45' : 1, "Above 18", "All Age groups"]
#     '18-' : 1,
#     '18+': 2,
#     '45+' : 4,
# }

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, Sequence('user_id_seq'), primary_key = True)
    uname = Column(String(50))
    fname = Column(String(50))
    is_subscribed = Column(Boolean, default = True)    # mark this as false when user wants to to stop getting updates..
    area_type = Column(String(10))
    area_code = Column(String(12))
    age_group = Column(Integer)


    def __repr__(self):
        return "User - %s %s %s %s %s"%(self.fname, self.uname, self.area_type, self.area_code, self.age_group)
    def __str__(self):
        return self.__repr__()

class UserActivity(Base):
    __tablename__ = 'user_activity'
    user_id = Column(Integer, primary_key = True)
    broadcast_msg_count = Column(Integer, default = 0) # to keep track of how much msg bot sent user.. 
    last_broadcast_time = Column(DateTime)

class AreaUpdate(Base):
    __tablename__ = 'area_update'
    area_type = Column(String(10), primary_key = True)
    area_code = Column(String(12), primary_key = True)
    age_gp = Column(Integer, primary_key = True)
    last_update = Column(String(65), nullable = True)
    last_update_time = Column(DateTime, nullable = True)


def get_db_login_info():
    import os
    db_info_file = os.environ['DB_INFO_FILE']
    if not db_info_file:
        raise Exception("environ variable DB_INFO_FILE is not set")
    with open(db_info_file) as fp:
        import json
        info = json.load(fp)
        return info['DB_SETTINGS']

if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    db_login_info = get_db_login_info()
    host, db_name, user_name, password = db_login_info['host'], db_login_info['name'], db_login_info['username'], db_login_info['password']
    engine = create_engine("mysql+pymysql://{}:{}@{}/{}?charset=utf8mb4".format(user_name, password, host, db_name), echo=True)
    Base.metadata.create_all(engine)
    
    session = sessionmaker(bind=engine)()
