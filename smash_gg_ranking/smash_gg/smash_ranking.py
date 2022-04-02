from sqlalchemy import select
import logging


from smash_gg_ranking.config import config
from smash_gg_ranking.smash_gg import query
from smash_gg_ranking.db.models import Ranking, RankingSet, RankingEvent, RankingAlgorithm
from smash_gg_ranking.db import db
from smash_gg_ranking.ranking import elo

logger = logging.getLogger('query')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


class EventRankingVideoMismatch(Exception):
    pass


def add_ranking_algorithm(name: str) -> id:
    session = db.get_session()
    ranking_algorithm = RankingAlgorithm(name=name)

    with session() as session:
        session.add(ranking_algorithm)
        session.flush()
        ranking_algorithm_id = ranking_algorithm.id
        session.commit()
        session.close()

    return ranking_algorithm_id


def add_ranking(ranking_name: str, ranking_algorithm_name: str, videogame_id: int) -> int:
    session = db.get_session()

    with session() as session:
        ranking_algorithm = session.query(RankingAlgorithm).where(
            RankingAlgorithm.name == ranking_algorithm_name).first()
        ranking = Ranking(name=ranking_name, ranking_algorithms_id=ranking_algorithm.id, videogame_id=videogame_id)
        session.add(ranking)
        session.flush()
        ranking_id = ranking.id
        session.commit()
        session.close()

    return ranking_id


def add_event_to_ranking(full_url, ranking_name):
    event, ranking_event_sets = query.get_event_id_and_sets(full_url)

    ranking_sets = []
    session = db.get_session()

    with session() as session:
        ranking = session.query(Ranking).where(Ranking.name == ranking_name).first()
        if int(event['videogame']['id']) != int(ranking.videogame_id):
            e = EventRankingVideoMismatch(
                "event['videogame']['id']={}, ranking.videogame_id={}".format(event['videogame']['id'], ranking.videogame_id))
            logger.exception(e)
            raise e
        ranking_event = RankingEvent(event_id=event['event_id'], event_url=full_url, ranking_id=ranking.id)
        session.add(ranking_event)
        session.flush()
        ranking_event_id = ranking_event.id

        for event_set in ranking_event_sets:
            event_set['ranking_event_id'] = ranking_event_id
            event_set['winner_change'] = None
            event_set['loser_change'] = None

            ranking_sets.append(RankingSet(**event_set))
        session.bulk_save_objects(ranking_sets)

        session.commit()
        session.close()


def calculate_ranking(ranking_name):
    session = db.get_session()

    with session() as session:
        ranking = session.query(Ranking).where(Ranking.name == ranking_name).scalar()
        ranking_events_subquery = select(RankingEvent.id).filter(RankingEvent.ranking_id == ranking.id)
        ranking_sets = session.query(RankingSet).filter(RankingSet.ranking_event_id.in_(ranking_events_subquery))
        elo.update_ranking_set_points(ranking_sets)
        session.commit()
        session.close()
