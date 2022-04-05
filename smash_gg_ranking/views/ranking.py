import logging

from db import db
from db.models import Ranking, RankingEvent, RankingSet, RankingAlgorithm, ParticipantRanking, Videogame
from smash_gg import graph_query
from config import config

logger = logging.getLogger('views/ranking')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def get_rankings():
    rank_views = []
    session = db.get_session()

    with session() as session:
        rankings = session.query(Ranking).all()

        for r in rankings:
            ranking_algorithm_name = session.query(RankingAlgorithm.name).where(
                RankingAlgorithm.id == r.ranking_algorithms_id).first()
            ranking_events = session.query(RankingEvent).where(RankingEvent.ranking_id == r.id).all()
            if len(ranking_events) == 0:
                break
            # event_info = graph_query.get_event_attributes(graph_query.parse_event_url(ranking_events[0].event_url))

            videogame_name = session.query(Videogame.name).where(Videogame.smash_gg_id == r.videogame_id).scalar()

            # TODO fix after updating AWS db
            if videogame_name is None:
                videogame_name = 'Guilty Gear: Strive'
                videogame_name = "hmm"

            participant_count = session.query(ParticipantRanking.id).where(ParticipantRanking.ranking_id == r.id).count()

            set_count = session.query(RankingSet.id).where(
                RankingSet.ranking_id == r.id).count()
            rank_views.append({
                "name": r.name,
                "id": r.id,
                "videogame": videogame_name,
                "event_count": len(ranking_events),
                "participant_count": participant_count,
                "match_count": set_count,
                "ranking_algorithm_name": ranking_algorithm_name[0]
            })
        session.close()

    return rank_views
