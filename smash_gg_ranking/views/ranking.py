import logging
from sqlalchemy import select

from db import db
from db.models import Ranking, RankingEvent, RankingSet, RankingAlgorithm
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
            event_info = graph_query.get_event_attributes(graph_query.parse_event_url(ranking_events[0].event_url))
            ranking_events_subquery = select(RankingEvent.id).filter(RankingEvent.ranking_id == r.id)
            set_count = session.query(RankingSet.id).filter(
                RankingSet.ranking_event_id.in_(ranking_events_subquery)).count()
            rank_views.append({
                "name": r.name,
                "id": r.id,
                "videogame": event_info['videogame'],
                "event_count": len(ranking_events),
                "participant_count": event_info['entrants_count'],
                "match_count": set_count,
                "ranking_algorithm_name": ranking_algorithm_name[0]
            })
        session.close()

    return rank_views
