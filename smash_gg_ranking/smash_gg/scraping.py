import logging
from sqlalchemy.exc import IntegrityError
import random

from config import config
from smash_gg_ranking.db import db
from smash_gg_ranking.db.models import Ranking, ParticipantRanking, Participant
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


def rank_event(event):
    session = db.get_session()

    with session() as session:
        ranking = session.query(Ranking).where(Ranking.videogame_id == event['videogame_id']).first()
        full_url = graph_query.reform_event_url(graph_query.parse_event_url(event['event_slug'])) # holy sheet

        if ranking is None:
            print("adding ranking and event")
            print(event)
            smash_ranking.add_ranking(
                ranking_name=event['videogame_name'],
                ranking_algorithm_name="elo",
                full_event_url=full_url)
        else:
            print("adding event")
            print(event)
            smash_ranking.add_event_to_ranking(
                full_url=full_url,
                ranking_name=event['videogame_name']
            )
        smash_ranking.calculate_ranking(event['videogame_name'])
        print("FINISHED={}".format(event))


def scrape_events_from_participants():
    session = db.get_session()

    with session() as session:
        participants = session.query(Participant).all()
        participant = random.choice(participants)

        events = scrape_events_from_user(participant.id)
    for event in events:
        rank_event(event)



