from sqlalchemy import select, and_
import logging
from typing import Dict
from datetime import datetime

from smash_gg_ranking.config import config
from smash_gg_ranking.smash_gg import graph_query
from smash_gg_ranking.db.models import Ranking, RankingSet, RankingEvent, RankingAlgorithm, ParticipantRanking, \
    Participant, Videogame
from smash_gg_ranking.db import db
from smash_gg_ranking.ranking import elo

logger = logging.getLogger('graph_query')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


class EventRankingVideoMismatch(Exception):
    pass


class DuplicateRankingEvent(Exception):
    pass


class RankingEventOutOfDateRange(Exception):
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


def add_videogame(event_data: Dict):
    session = db.get_session()

    with session() as session:
        session.add(Videogame(
            id=event_data['videogame_id'], smash_gg_id=event_data['videogame_id'], name=event_data['videogame_name']
        ))
        session.commit()

    return event_data['videogame_id']


def add_ranking(ranking_name: str, ranking_algorithm_name: str, full_event_url: str,
                start_datetime: datetime = None, end_datetime: datetime = None) -> int:
    session = db.get_session()

    event_data = graph_query.get_event_attributes(graph_query.parse_event_url(full_event_url))

    with session() as session:
        videogame = session.query(Videogame).where(Videogame.smash_gg_id == event_data['videogame_id']).first()
        if videogame is None:
            videogame_id = add_videogame(event_data)
        else:
            videogame_id = videogame.smash_gg_id

        ranking_algorithm = session.query(RankingAlgorithm).where(
            RankingAlgorithm.name == ranking_algorithm_name).first()
        if ranking_algorithm is None:
            ranking_algorithms_id = add_ranking_algorithm("elo")
        else:
            ranking_algorithms_id = ranking_algorithm.id

        ranking = Ranking(
            name=ranking_name, ranking_algorithms_id=ranking_algorithms_id, videogame_id=videogame_id,
            start_datetime=start_datetime, end_datetime=end_datetime
        )
        session.add(ranking)
        session.flush()
        ranking_id = ranking.id
        session.commit()

        try:
            if not add_event_to_ranking(full_url=full_event_url, ranking_name=ranking_name):
                session.delete(ranking)
                session.commit()
        except Exception as e:
            session.delete(ranking)
            session.commit()
            session.commit()
            raise e

        session.close()

    return ranking_id


def event_ranking_already_exists(ranking_name, event_slugs):
    session = db.get_session()

    with session() as session:
        ranking = session.query(Ranking).where(Ranking.name == ranking_name).first()
        if ranking is None:
            return False

        ranking_event = session.query(RankingEvent.id).where(and_(
            RankingEvent.event_url == graph_query.reform_event_url(event_slugs),
            RankingEvent.ranking_id == ranking.id
        )).first()

    return False if (ranking_event is None) else True


def event_is_valid_for_ranking(ranking_name, event_slugs: Dict) -> bool:
    try:
        event_attributes = graph_query.get_event_attributes(event_slugs)
        logger.debug()
        session = db.get_session()

        with session() as session:
            ranking = session.query(Ranking).where(Ranking.name == ranking_name).first()
            if int(event_attributes['videogame_id']) != int(ranking.videogame_id):
                e = EventRankingVideoMismatch(
                    "event['videogame_id']={}, ranking.videogame_id={}".format(event_attributes['videogame_id'], ranking.videogame_id))
                logger.exception(e)
                raise e

            if ranking.start_datetime is not None:
                if ranking.start_datetime > event_attributes['start_at']:
                    raise RankingEventOutOfDateRange("{} {}".format(ranking, event_attributes))
            if ranking.end_datetime is not None:
                if ranking.end_datetime < event_attributes['start_at']:
                    raise RankingEventOutOfDateRange("{} {}".format(ranking, event_attributes))
    except Exception as e:
        logger.exception(e)
        logger.error("event_slugs={}".format(event_slugs))
        logger.error("ranking_name={}".format(ranking_name))
        logger.error("event_attributes={}".format(event_attributes))
    return True


def add_event_to_ranking(full_url, ranking_name):
    event_slugs = graph_query.parse_event_url(full_url)
    if event_ranking_already_exists(ranking_name, event_slugs):
        return False

    if not event_is_valid_for_ranking(ranking_name=ranking_name, event_slugs=event_slugs):
        return False

    # get users in event
    event_users = graph_query.get_users_from_event(event_slugs)

    event, ranking_event_sets = graph_query.get_event_id_and_sets(full_url)

    ranking_sets = []
    session = db.get_session()

    with session() as session:
        ranking = session.query(Ranking).where(Ranking.name == ranking_name).first()
        try:
            for event_user in event_users:
                session.merge(Participant(**event_user))

            ranking_event = RankingEvent(
                event_id=event['event_id'],
                event_url=graph_query.reform_event_url(event_slugs),
                event_name="{} {}".format(event['tournament_name'], event['name']),
                event_datetime=event['start_at'],
                ranking_id=ranking.id
            )
            session.add(ranking_event)
            session.flush()
            ranking_event_id = ranking_event.id

            for event_set in ranking_event_sets:
                event_set['ranking_event_id'] = ranking_event_id
                event_set['ranking_id'] = ranking.id
                event_set['winner_change'] = None
                event_set['loser_change'] = None

                ranking_sets.append(RankingSet(**event_set))
            session.bulk_save_objects(ranking_sets)

            session.commit()
            session.close()
        except AttributeError as e:
            logger.exception(e)
            logger.error("event={}".format(event))
            raise e
    return True


def calculate_ranking(ranking_name):
    session = db.get_session()

    with session() as session:
        ranking = session.query(Ranking).where(Ranking.name == ranking_name).scalar()
        ranking_events_subquery = select(RankingEvent.id).filter(RankingEvent.ranking_id == ranking.id)
        ranking_sets = session.query(RankingSet).filter(
            RankingSet.ranking_event_id.in_(ranking_events_subquery)).order_by(RankingSet.set_datetime.asc())
        participant_points = elo.update_ranking_set_points(ranking_sets)

        for pr_id in participant_points.keys():  # for each participant points
            participant_ranking = session.query(ParticipantRanking).where(  # get participant ranking
                and_(
                    ParticipantRanking.participant_id == pr_id,
                    ParticipantRanking.ranking_id == ranking.id
                )).first()
            if participant_ranking is None:  # if participant has no points
                participant_ranking_data = {  # create new
                    "participant_id": pr_id,
                    "ranking_id": ranking.id,
                    "participant_points": participant_points[pr_id],
                    "up_from_last": None
                }
                session.add(ParticipantRanking(**participant_ranking_data))
            else:  # update existing participant_ranking
                participant_ranking.participant_points = participant_points[pr_id]
                if participant_ranking.participant_points < participant_points[pr_id]:
                    participant_ranking.up_from_last = False
                elif participant_ranking.participant_points > participant_points[pr_id]:
                    participant_ranking.up_from_last = False
                else:
                    participant_ranking.up_from_last = None
        session.commit()
        session.close()
