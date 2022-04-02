import logging
from sqlalchemy import select
import datetime

from db import db
from db.models import Ranking, RankingEvent, RankingSet
from smash_gg import query
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
            ranking_events = session.query(RankingEvent).where(RankingEvent.ranking_id == r.id).all()
            event_info = query.get_event_attributes(query.parse_event_url(ranking_events[0].event_url))
            ranking_events_subquery = select(RankingEvent.id).filter(RankingEvent.ranking_id == r.id)
            set_count = session.query(RankingSet.id).filter(
                RankingSet.ranking_event_id.in_(ranking_events_subquery)).count()
            logger.debug(set_count)
            rank_views.append({
                "name": r.name,
                "id": r.id,
                "videogame": event_info['videogame'],
                "event_count": len(ranking_events),
                "player_count": event_info['entrants_count'],
                "match_count": set_count
            })

        session.close()

    return rank_views


def get_events(ranking_id: int):
    events = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()
        ranking_events = session.query(RankingEvent).where(RankingEvent.ranking_id == ranking_id).all()
        logger.debug("ranking_events={}".format(ranking_events))
        for re in ranking_events:
            event = query.get_event_attributes(query.parse_event_url(re.event_url))
            events.append({
                "tournament": event['tournament'],
                "name": event['name'],
                "start_at": event['start_at'].strftime("%m/%d/%Y")
            })
        logger.debug("events={}".format(events))

    return ranking.name, events