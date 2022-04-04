import logging
from sqlalchemy import and_, or_, func
from typing import Dict

from db import db
from db.models import Ranking, RankingEvent, ParticipantRanking, RankingSet, Participant
from smash_gg import graph_query
from config import config
from views import paging

logger = logging.getLogger('views/players')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def get_ranking_participants(ranking_id: int, event_id: int, page_params: Dict):
    participants = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()

        participant_ranking = session.query(ParticipantRanking).where(
            ParticipantRanking.ranking_id == ranking_id)

        # todo filter by event_id
        if event_id is not None:
           pass

        participant_ranking= participant_ranking.order_by(ParticipantRanking.participant_points.desc())

        participant_ranking, paging_info = paging.get_paging_info(participant_ranking, page_params)

        rank = 1 + paging_info['offset']

        # TODO refactor to mapping
        participants_data = session.query(Participant).all()
        par_tags = {}
        for par in participants_data:
            par_tags[par.id] = par.gamer_tag

        for pr in participant_ranking:
            set_wins = session.query(
                func.sum(RankingSet.winner_score).label('win_sum'),
                func.count(RankingSet.winner_score).label('win_count')
            ).where(
                    and_(RankingSet.winner_id == pr.participant_id, RankingSet.ranking_id == ranking.id)).first()
            set_loses = session.query(
                func.sum(RankingSet.winner_score).label('loss_sum'),
                func.count(RankingSet.winner_score).label('loss_count')
            ).where(
                    and_(RankingSet.loser_id == pr.participant_id, RankingSet.ranking_id == ranking.id)).first()
            logger.debug(set_loses)



            set_count = set_wins.win_count + set_loses.loss_count

            participants.append({
                "rank": rank,
                "participant_id": pr.participant_id,
                "participant_gamertag": par_tags[pr.participant_id],
                "participant_points": round(pr.participant_points, 2),
                "set_count": set_count,
                "win_score": 0 if set_wins.win_sum is None else set_wins.win_sum,
                "loss_score": set_loses.loss_sum,
                "set_win_count": set_wins.win_count,
                "set_loss_count": set_loses.loss_count,
                "up_from_last": pr.up_from_last
            })
            rank = rank + 1

    return ranking, participants, paging_info
