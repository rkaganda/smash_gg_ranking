import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import logging

# from ..config import config
from config import config

logger = logging.getLogger('db')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

Base = declarative_base()
engine = sqla.create_engine(config.settings['db_url'])


def get_session() -> sessionmaker:
    session = sessionmaker()
    session.configure(bind=engine)
    return sessionmaker(engine)

