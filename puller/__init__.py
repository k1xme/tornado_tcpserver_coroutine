# -*- encoding: utf-8 -*-
import logging


logger = logging.getLogger('Puller')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('etc/logs/data.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s]-[%(levelname)s]: %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


from sqlalchemy import create_engine
from sqlalchemy import Column, Float, Integer, String, DATETIME, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine('mysql+pymysql://trqcloud:dangerous@localhost/trqcloud')
Base = declarative_base()
Base.metadata.engine = engine
DBSessionMaker = sessionmaker(bind=engine)
session = DBSessionMaker()

from pika import adapters
import pika
import models