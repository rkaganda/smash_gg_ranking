import logging
from sqlalchemy import and_, or_
from typing import Dict

from db import db
from db.models import Ranking, RankingSet, RankingEvent, Participant
from smash_gg import graph_query
from config import config

logger = logging.getLogger('views/matches')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def get_paging_info(sets, paging: Dict):
    # paging
    participant_sets_count = sets.count()
    paging_info = {
        "page_num": paging['page_num'],
        "max_page": (participant_sets_count // paging['page_size']) + 1,  # math is hard?
        "page_size": paging['page_size']
    }
    offset = (paging['page_num'] - 1) * paging['page_size']
    participant_sets = sets.offset(offset).limit(paging['page_size'])

    return participant_sets, paging_info


def get_ranking_sets(ranking_id: int, event_id: int, paging: Dict):
    sets = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()

        ranking_sets = session.query(RankingSet).where(
            RankingSet.ranking_event_id == event_id).order_by(RankingSet.set_datetime.desc())
        event = session.query(RankingEvent).where(RankingEvent.id == event_id).first()
        event = event.__dict__
        event['attrib'] = graph_query.get_event_attributes(graph_query.parse_event_url(event['event_url']))

        ranking_sets, paging_info = get_paging_info(ranking_sets, paging)

        # TODO refactor to mapping
        participants = session.query(Participant).all()
        par_tags = {}
        for par in participants:
            par_tags[par.id] = par.gamer_tag

        for rs in ranking_sets.all():
            sets.append({
                "winner_id": rs.winner_id,
                "winner_gamertag": par_tags[rs.winner_id],
                "winner_score": rs.winner_score,
                "winner_points": rs.winner_points,
                "winner_change": rs.winner_change,
                "loser_id": rs.loser_id,
                "loser_gamertag": par_tags[rs.loser_id],
                "loser_score": rs.loser_score,
                "loser_points": rs.loser_points,
                "loser_change": rs.loser_change,
                "set_datetime": rs.set_datetime,
            })

    return ranking.__dict__, event, sets, paging_info


def get_participant_sets(ranking_id: int, event_id: int, participant_id: str, paging: Dict):
    logging.debug("participant_id={}".format(participant_id))
    sets = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()

        participant_sets = session.query(RankingSet).where(
            or_(RankingSet.loser_id == participant_id, RankingSet.winner_id == participant_id)
        ).order_by(RankingSet.set_datetime.desc())

        event_data = None
        if event_id is not None:
            event = session.query(RankingEvent).where(RankingEvent.id == event_id).first()
            if event is not None:
                event_data = event.__dict__
                event_data['attrib'] = graph_query.get_event_attributes(graph_query.parse_event_url(event_data['event_url']))
                participant_sets = participant_sets.where(
                    RankingSet.ranking_event_id == event_id
                )
        else:
            pass

        participant_sets, paging_info = get_paging_info(participant_sets, paging)

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
                "winner_id": ps.winner_id,
                "winner_gamertag": par_tags[ps.winner_id],
                "winner_score": ps.winner_score,
                "winner_points": ps.winner_points,
                "winner_change": ps.winner_change,
                "loser_gamertag": par_tags[ps.loser_id],
                "loser_id": ps.loser_id,
                "loser_score": ps.loser_score,
                "loser_points": ps.loser_points,
                "loser_change": ps.loser_change,
                "set_datetime": ps.set_datetime,
            })

    return ranking.__dict__, event_data, participant_data, sets, paging_info
