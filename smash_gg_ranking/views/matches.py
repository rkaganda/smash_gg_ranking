import logging
from sqlalchemy import and_, or_

from db import db
from db.models import Ranking, RankingSet, RankingEvent
from smash_gg import graph_query
from config import config

logger = logging.getLogger('views/matches')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def get_ranking_sets(ranking_id: int, event_id: int):
    sets = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()

        ranking_sets = session.query(RankingSet).where(
            RankingSet.ranking_event_id == event_id).order_by(RankingSet.set_datetime.desc()).all()
        event = session.query(RankingEvent).where(RankingEvent.id == event_id).first()
        event = event.__dict__
        event['attrib'] = graph_query.get_event_attributes(graph_query.parse_event_url(event['event_url']))
        for rs in ranking_sets:
            sets.append({
                "winner_id": rs.winner_id,
                "winner_score": rs.winner_score,
                "winner_points": rs.winner_points,
                "winner_change": rs.winner_change,
                "loser_id": rs.loser_id,
                "loser_score": rs.loser_score,
                "loser_points": rs.loser_points,
                "loser_change": rs.loser_change,
                "set_datetime": rs.set_datetime,
            })

    return ranking.__dict__, event, sets


def get_participant_sets(ranking_id: int, participant_id: str):
    logging.debug("participant_id={}".format(participant_id))
    participant_data = {
        "id": participant_id
    }
    sets = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()

        participant_sets = session.query(RankingSet).where(
            and_(or_(RankingSet.loser_id == participant_id, RankingSet.winner_id == participant_id),
                 RankingSet.ranking_id == ranking.id
                 )
        ).order_by(RankingSet.set_datetime.desc())
        for ps in participant_sets:
            sets.append({
                "winner_id": ps.winner_id,
                "winner_score": ps.winner_score,
                "winner_points": ps.winner_points,
                "winner_change": ps.winner_change,
                "loser_id": ps.loser_id,
                "loser_score": ps.loser_score,
                "loser_points": ps.loser_points,
                "loser_change": ps.loser_change,
                "set_datetime": ps.set_datetime,
            })

    return ranking.__dict__, participant_data, sets


def get_event_participant_sets(ranking_id: int, event_id: int, participant_id: str):
    logging.debug("participant_id={}".format(participant_id))
    participant_data = {
        "id": participant_id
    }
    sets = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()
        event = session.query(RankingEvent).where(RankingEvent.id == event_id).first()
        event = event.__dict__
        event['attrib'] = graph_query.get_event_attributes(graph_query.parse_event_url(event['event_url']))

        participant_sets = session.query(RankingSet).where(
            and_(or_(RankingSet.loser_id == participant_id, RankingSet.winner_id == participant_id),
                 RankingSet.ranking_event_id == event_id
                 )
        ).order_by(RankingSet.set_datetime.desc())
        for ps in participant_sets:
            sets.append({
                "winner_id": ps.winner_id,
                "winner_score": ps.winner_score,
                "winner_points": ps.winner_points,
                "winner_change": ps.winner_change,
                "loser_id": ps.loser_id,
                "loser_score": ps.loser_score,
                "loser_points": ps.loser_points,
                "loser_change": ps.loser_change,
                "set_datetime": ps.set_datetime,
            })

    return ranking.__dict__, event, participant_data, sets
