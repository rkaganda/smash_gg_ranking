import logging
from sqlalchemy import select

from db import db
from db.models import Ranking, RankingEvent, RankingSet
from smash_gg import graph_query
from config import config

logger = logging.getLogger('views/events')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def get_events(ranking_id: int):
    events = []
    session = db.get_session()
    with session() as session:
        ranking = session.query(Ranking).where(Ranking.id == ranking_id).first()
        ranking_events = session.query(RankingEvent).where(RankingEvent.ranking_id == ranking_id).all()
        for re in ranking_events:
            set_count = session.query(RankingSet.id).where(RankingSet.ranking_event_id==re.id).count()
            event = graph_query.get_event_attributes(graph_query.parse_event_url(re.event_url))
            events.append({
                "url": re.event_url,
                "tournament": event['tournament'],
                "name": event['name'],
                "set_count": set_count,
                "start_at": event['start_at'].strftime("%m/%d/%Y")
            })

    return ranking.name, events

