import logging
from sqlalchemy import and_, or_
from typing import Dict

from db import db
from db.models import Ranking, RankingEvent, ParticipantRanking, RankingSet, Participant
from smash_gg import graph_query
from config import config

logger = logging.getLogger('views/players')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def get_ranking_participants(ranking_id: int, paging: Dict):
    participants = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()
        participant_ranking_count = session.query(ParticipantRanking).where(
            ParticipantRanking.ranking_id == ranking_id).count()
        paging_info = {
            "page_num": paging['page_num'],
            "max_page": (participant_ranking_count // paging['page_size']) + 1,  # math is hard?
            "page_size": paging['page_size']
        }
        offset = (paging['page_num']-1) * paging['page_size']

        participant_ranking = session.query(ParticipantRanking).where(
            ParticipantRanking.ranking_id == ranking_id).order_by(
            ParticipantRanking.participant_points.desc()).offset(offset).limit(paging['page_size'])
        rank = 1 + offset

        # TODO refactor to mapping
        participants_data = session.query(Participant).all()
        par_tags = {}
        for par in participants_data:
            par_tags[par.id] = par.gamer_tag

        for pr in participant_ranking:
            set_count = session.query(RankingSet).where(
                and_(or_(RankingSet.loser_id == pr.participant_id, RankingSet.winner_id == pr.participant_id),
                     RankingSet.ranking_id == ranking.id
                     )
            ).count()
            participants.append({
                "rank": rank,
                "participant_id": pr.participant_id,
                "participant_gamertag": par_tags[pr.participant_id],
                "participant_points": pr.participant_points,
                "set_count": set_count,
                "up_from_last": pr.up_from_last
            })
            rank = rank + 1

    return ranking, participants, paging_info
