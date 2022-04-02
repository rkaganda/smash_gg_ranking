import logging

from db import db
from db.models import Ranking, RankingEvent, ParticipantRanking
from smash_gg import graph_query
from config import config

logger = logging.getLogger('views/players')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def get_ranking_participants(ranking_id: int):
    participants = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()
        participant_ranking = session.query(ParticipantRanking).where(
            ParticipantRanking.ranking_id == ranking_id).order_by(ParticipantRanking.participant_points.desc()).all()
        rank = 1
        for pr in participant_ranking:
            participants.append({
                "rank": rank,
                "participant_id": pr.participant_id,
                "participant_points": pr.participant_points,
                "up_from_last": pr.up_from_last
            })
            rank = rank + 1

    return ranking.name, participants
