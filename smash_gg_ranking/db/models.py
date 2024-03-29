from sqlalchemy import Column, Integer, Float, ForeignKey, Index, DateTime, String, Boolean

from config import config
from db.db import Base
from db.db import engine


class RankingAlgorithm(Base):
    __tablename__ = "{}_ranking_algorithms".format(config.settings['db_suffix'])
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    __table_args__ = {'extend_existing': True}


class Videogame(Base):
    __tablename__ = "{}_videogame".format(config.settings['db_suffix'])
    id = Column(Integer, primary_key=True)
    smash_gg_id = Column(Integer)
    name = Column(String, unique=True)
    __table_args__ = {'extend_existing': True}


class Ranking(Base):
    __tablename__ = "{}_ranking".format(config.settings['db_suffix'])
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    ranking_algorithms_id = Column(Integer, ForeignKey("{}_ranking_algorithms.id".format(config.settings['db_suffix'])))
    videogame_id = Column(Integer, nullable=False)
    name = Column(String, unique=True)
    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)


class RankingEvent(Base):
    __tablename__ = "{}_ranking_events".format(config.settings['db_suffix'])
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=False)
    ranking_id = Column(Integer, ForeignKey("{}_ranking.id".format(config.settings['db_suffix'])))
    event_url = Column(String, nullable=False)
    event_name = Column(String, nullable=False)
    event_datetime = Column(DateTime, nullable=False)
    __table_args__ = (Index('{}_ranking_event_index'.format(config.settings['db_suffix']), "event_id", "ranking_id", unique=True), {'extend_existing': True})


class RankingSet(Base):
    __tablename__ = "{}_ranking_sets".format(config.settings['db_suffix'])
    id = Column(Integer, primary_key=True)
    ranking_id = Column(Integer, ForeignKey("{}_ranking.id".format(config.settings['db_suffix'])), nullable=False)
    ranking_event_id = Column(Integer, ForeignKey("{}_ranking_events.id".format(config.settings['db_suffix'])),
                              nullable=False)
    set_id = Column(Integer, nullable=False)
    set_datetime = Column(DateTime, nullable=False)
    winner_id = Column(String, ForeignKey("{}_participants.id".format(config.settings['db_suffix'])), nullable=False)
    winner_score = Column(Integer, nullable=False)
    winner_points = Column(Float)
    winner_change = Column(Float)
    loser_id = Column(String, ForeignKey("{}_participants.id".format(config.settings['db_suffix'])), nullable=False)
    loser_score = Column(Integer, nullable=False)
    loser_points = Column(Float)
    loser_change = Column(Float)
    __table_args__ = (Index('{}_ranking_set_index'.format(config.settings['db_suffix']), "ranking_event_id", "set_id"), {'extend_existing': True})


class ParticipantRanking(Base):
    __tablename__ = "{}_participants_ranking".format(config.settings['db_suffix'])
    id = Column(Integer, primary_key=True, autoincrement=True)
    participant_id = Column(String, ForeignKey("{}_participants.id".format(config.settings['db_suffix'])), nullable=False)
    ranking_id = Column(Integer, ForeignKey("{}_ranking.id".format(config.settings['db_suffix'])))
    participant_points = Column(Float, nullable=False)
    up_from_last = Column(Boolean)
    __table_args__ = ({'extend_existing': True})


class Participant(Base):
    __tablename__ = "{}_participants".format(config.settings['db_suffix'])
    id = Column(String, primary_key=True)
    smash_gg_url = Column(String)
    gamer_tag = Column(String)
    __table_args__ = ({'extend_existing': True})


Base.metadata.create_all(engine)
