import logging
from sqlalchemy.exc import IntegrityError

from config import config
from smash_gg_ranking.db import db
from smash_gg_ranking.db.models import Ranking, ParticipantRanking
from smash_gg import graph_query
from smash_gg import smash_ranking


logger = logging.getLogger('smash_gg/scraping')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def scrape_events_from_user(user_id):
    user_slug = user_id.replace("_","/")
    events = graph_query.get_events_from_user_slug(user_slug=user_slug)
    # query smash gg for all
    return events


def populate_ranking_from_participants(ranking_name, event_count=1):
    event_added = 0
    session = db.get_session()

    with session() as session:
        ranking = session.query(Ranking).where(Ranking.name == ranking_name).first()
        participant_ids = session.query(ParticipantRanking.participant_id).where(ParticipantRanking.ranking_id==ranking.id).all()
        for participant_id in participant_ids:
            events = scrape_events_from_user(participant_id[0])
            for event in events:
                if int(event['videogame_id']) == int(ranking.videogame_id):
                    # print(event['event_slug'])
                    if smash_ranking.add_event_to_ranking(event['event_slug'], ranking.name):
                        event_added = event_added + 1
                        print("event_added={}".format(event_added))
                    else:
                        pass
                if event_count <= event_added:
                    break
            if event_count <= event_added:
                break
