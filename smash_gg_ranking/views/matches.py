import logging
from sqlalchemy import and_, or_
from sqlalchemy.inspection import inspect
from typing import Dict

from db import db
from db.models import Ranking, RankingSet, RankingEvent, Participant
from smash_gg import graph_query
from views import paging
from config import config

logger = logging.getLogger('views/matches')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def get_ranking_sets(ranking_id: int, event_id: int, page_params: Dict):
    sets = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()

        ranking_sets = session.query(RankingSet).where(
            RankingSet.ranking_event_id == event_id).order_by(RankingSet.set_datetime.desc())
        event = session.query(RankingEvent).where(RankingEvent.id == event_id).first()
        event = event.__dict__
        event['attrib'] = graph_query.get_event_attributes(graph_query.parse_event_url(event['event_url']))

        ranking_sets, paging_info = paging.get_paging_info(ranking_sets, page_params)

        # TODO refactor to mapping
        participants = session.query(Participant).all()
        par_tags = {}
        for par in participants:
            par_tags[par.id] = par.gamer_tag

        for rs in ranking_sets.all():
            sets.append({
                "winner_id": rs.winner_id,
                "winner_gamertag": par_tags[rs.winner_id],
                "winner_score": round(rs.winner_score, 2),
                "winner_points": round(rs.winner_points, 2),
                "winner_change": round(rs.winner_change, 2),
                "loser_id": rs.loser_id,
                "loser_gamertag": par_tags[rs.loser_id],
                "loser_score": round(rs.loser_score, 2),
                "loser_points": round(rs.loser_points, 2),
                "loser_change": round(rs.loser_change, 2),
                "set_datetime": rs.set_datetime.strftime("%Y-%m-%d %I:%M %p %z"),
            })

    return ranking.__dict__, event, sets, paging_info


def get_participant_sets(ranking_id: int, event_id: int, participant_id: str, page_params: Dict):
    logging.debug("participant_id={}".format(participant_id))
    sets = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()

        participant_sets = session.query(RankingSet, RankingEvent.event_name).where(
            or_(RankingSet.loser_id == participant_id, RankingSet.winner_id == participant_id)
        ).filter(RankingSet.ranking_event_id == RankingEvent.id).order_by(RankingSet.set_datetime.desc())

        event_data = None
        if event_id is not None:
            event = session.query(RankingEvent).where(RankingEvent.id == event_id).first()
            if event is not None:
                event_data = event.__dict__
                participant_sets = participant_sets.where(
                    RankingSet.ranking_event_id == event_id
                )
        else:
            pass

        participant_sets, paging_info = paging.get_paging_info(participant_sets, page_params)

        # TODO refactor to mapping
        participants = session.query(Participant).all()
        par_tags = {}
        for par in participants:
            par_tags[par.id] = par.gamer_tag

        participant_data = {
            "id": participant_id,
            "gamertag": par_tags[participant_id]
        }

        for ps in participant_sets:
            sets.append({
                "winner_id": ps.RankingSet.winner_id,
                "winner_gamertag": par_tags[ps.RankingSet.winner_id],
                "winner_score": round(ps.RankingSet.winner_score, 2),
                "winner_points": round(ps.RankingSet.winner_points, 2),
                "winner_change": round(ps.RankingSet.winner_change, 2),
                "loser_gamertag": par_tags[ps.RankingSet.loser_id],
                "loser_id": ps.RankingSet.loser_id,
                "loser_score": round(ps.RankingSet.loser_score, 2),
                "loser_points": round(ps.RankingSet.loser_points, 2),
                "loser_change": round(ps.RankingSet.loser_change, 2),
                "set_datetime": ps.RankingSet.set_datetime.strftime("%Y-%m-%d %I:%M %p"),
                "event_name": ps.event_name,
                "event_id": ps.RankingSet.ranking_event_id
            })

    return ranking.__dict__, event_data, participant_data, sets, paging_info
