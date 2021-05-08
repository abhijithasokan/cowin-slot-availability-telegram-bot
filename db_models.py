from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
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
    uname = Column(String)
    fname = Column(String)
    is_subscribed = Column(Boolean, default = True)    # mark this as false when user wants to to stop getting updates..
    area_type = Column(String)
    area_code = Column(String)
    age_group = Column(Integer)


    def __repr__(self):
        return "User - %s %s %s %s %s"%(self.fname, self.uname, self.area_type, self.area_code, self.age_group)
    def __str__(self):
        return self.__repr__()

class UserActivity(Base):
    __tablename__ = 'user_activity'
    user_id = Column(Integer, primary_key = True)
    msg_sent = Column(Integer, default = 0)  # to keep track of how much msg bot sent user.. 
    msg_recevied = Column(Integer, default = 1)




if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine('sqlite:///test.db', echo=True)
    Base.metadata.create_all(engine)
    
    session = sessionmaker(bind=engine)()

    from sqlalchemy import select
    x = session.query(User).get(137407007)
