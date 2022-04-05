import datetime

import requests
import logging
import json
from typing import Dict, List
import itertools
from tqdm import tqdm
import time

from config import config

logger = logging.getLogger('graph_query')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


class SmashGGQueryFailed(Exception):
    pass


class InvalidSmashGGEventURL(Exception):
    pass


class InvalidSetNode(Exception):
    pass


def smash_gg_query(query: str, variables: str):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": "Bearer {}".format(config.settings['smash_gg_token'])
    }
    smash_gg_url = 'https://api.smash.gg/gql/alpha'
    keep_trying = True
    while keep_trying:
        r = requests.post(smash_gg_url, json={'query': query, 'variables': variables}, headers=headers)

        if r.status_code != 200:
            if r.status_code == 429:
                logger.error("graph_query RATE LIMIT: {} \n response:{}\n"
                             .format(r.status_code, r.text))
                time.sleep(30)
            else:
                logger.error("smash graph_query FAILED \n response:{}\n {} \n graph_query:\n{} \n variables:{}\n "
                             .format(r.text, r.status_code, query, variables, ))
                raise SmashGGQueryFailed(r.text)
        else:
            keep_trying = False
    # logger.debug("query:\n{}\nvariables:\n{}\nresponse:\n{}".format(query, variables, r.text))

    return r.text


def parse_event_url(full_url: str) -> Dict:
    #  https://smash.gg/tournament/some_tournament/event/some_event/overview
    tournament_slug = None
    event_slut = None

    # parse tournament slug, event slug from url
    url_split = full_url.split('/')
    for i, url_part in enumerate(url_split):
        if url_part == 'tournament':
            tournament_slug = url_split[i + 1]
        elif url_part == 'event':
            event_slut = url_split[i + 1]
    if tournament_slug is None or event_slut is None:
        raise InvalidSmashGGEventURL(full_url)

    return {'tournament': tournament_slug, 'event': event_slut}


def reform_event_url(event_slugs):
    return "https://smash.gg/tournament/{}/event/{}".format(event_slugs['tournament'], event_slugs['event'])


def get_event_attributes(url_slugs, per_page=20) -> Dict[str, str]:
    variables = """
        {{
            "event_slug":"tournament/{}/event/{}",
            "perPage": {per_page}
        }}
        """.format(url_slugs['tournament'], url_slugs['event'], per_page=per_page)
    query = """
        query EventQuery($event_slug: String, $perPage: Int) {
            event(slug: $event_slug) {
                slug
                id
                startAt
                name
                numEntrants
                tournament {
                    name
                }
                videogame{
                    id
                    name
                    displayName
                    images {
                        id
                        url
                    }
                }
                sets(perPage: $perPage, sortType: STANDARD) {
                    pageInfo {
                        totalPages
                    }
                }
            }
        }
        """
    event = json.loads(smash_gg_query(query, variables))['data']['event']
    return {
        "event_id": event['id'],
        "tournament_name": event['tournament']['name'],
        "name": event['name'],
        "start_at": datetime.datetime.fromtimestamp(event['startAt']),
        "page_count": event['sets']['pageInfo']['totalPages'],
        "entrants_count": event['numEntrants'],
        "videogame_id": event['videogame']['id'],
        "videogame_name": event['videogame']['displayName']
    }


def parse_node_slot(node_slots: List, node_set) -> Dict:
    try:
        standing_slots = []
        highest_score = -1  # track the highest score
        highest_score_index = -1
        for ns_index, node_slot in enumerate(node_slots):
            if len(node_slot['entrant']['participants']) > 1:  # if more than 2 entrants
                raise InvalidSetNode(node_slot)
            standing_slots.append({
                'score': node_slot['standing']['stats']['score']['value'],
                'id': node_slot['entrant']['participants'][0]['user']['slug'].replace("/", "_")
            })
            if highest_score < node_slot['standing']['stats']['score']['value']:  # if highest score
                highest_score_index = ns_index
                highest_score = node_slot['standing']['stats']['score']['value']

        lowest_score_index = 0 if highest_score_index == 1 else 1
        node_set['winner_id'] = standing_slots[highest_score_index]['id']
        node_set['winner_score'] = standing_slots[highest_score_index]['score']
        node_set['loser_id'] = standing_slots[lowest_score_index]['id']
        node_set['loser_score'] = standing_slots[lowest_score_index]['score']

        if node_set['winner_score'] <= 0 or node_set['loser_score'] < 0:  # check for DQ
            node_set = None
    except TypeError as e:
        node_set = None
    except AttributeError as e:
        logger.exception(e)
        logger.error("node_slots={}".format(node_slots))
        node_set = None
    except InvalidSetNode as e:
        logger.exception(e)
        logger.error("node_slots={}".format(node_slots))
        node_set = None
    except IndexError as e:
        logger.exception(e)
        logger.error("node_slots={}".format(node_slots))
        node_set = None

    return node_set


def parse_set_nodes(set_nodes: List) -> List:
    event_sets = []
    for node in set_nodes:
        try:
            node_set = {
                'set_id': node['id'],
                'set_datetime': datetime.datetime.fromtimestamp(node['completedAt'])
            }
            if len(node['slots']) > 2:  # if more than two entrants
                raise InvalidSetNode(node['slots'])
            node_set = parse_node_slot(node['slots'], node_set)
            if node_set is not None:  # if non set was a DQ
                event_sets.append(node_set)
        except TypeError as e:
            logger.exception(e)
            logger.error(e)

    return event_sets


def parse_entrant_set(entrant_set: List) -> List:
    user_set = []
    for es in entrant_set:
        if 'participants' in es:
            for par in es['participants']:
                try:
                    if par['user']['slug'] is not None:
                        user_set.append({
                            'id': par['user']['slug'].replace("/", "_"),
                            'gamer_tag': par['gamerTag'],
                            'smash_gg_url': "http://www.smash.gg/{}".format(par['user']['slug'])
                        })
                except TypeError as e:
                    logger.exception(e)
                    logger.error("es={}".format(es))
                    logger.error("par={}".format(par))
    return user_set


def get_users_from_event(url_slugs: Dict, per_page=40) -> List:
    page_query = """
        query EventEntrants($event_slug: String, $perPage: Int!) {
          event(slug: $event_slug) {
            id
            name
            entrants(query: {
              perPage: $perPage,
            }) {
              pageInfo {
                total
                totalPages
              }
            }
          }
        }
    """
    page_query_variables = """
                    {{
                        "event_slug":"tournament/{}/event/{}",
                        "perPage": {}
                    }}
                    """.format(url_slugs['tournament'], url_slugs['event'], per_page)
    page_count = json.loads(smash_gg_query(page_query, page_query_variables))  # query smash_gg
    page_count = page_count['data']['event']['entrants']['pageInfo']['totalPages']

    query = """
    query EventEntrants($event_slug: String, $page: Int!, $perPage: Int!) {
        event(slug: $event_slug) {
            id
            name
            entrants(query: {
              page: $page
              perPage: $perPage
            }) {
              nodes {
                id
                participants {
                  id
                  gamerTag
                  user {
                    slug
                  }
                }
              }
            }
        }
    }
    """
    user_sets = []
    if config.settings['show_progress'] == 'True' and page_count > 1:
        print("get_users_from_event")
        pages_enum = tqdm(range(1, page_count+1))
    else:
        pages_enum = range(1, page_count+1)
    for page in pages_enum:
        variables = """
                {{
                    "event_slug":"tournament/{}/event/{}",
                    "page": {},
                    "perPage": {}
                }}
                """.format(url_slugs['tournament'], url_slugs['event'], page, per_page)
        user_page = json.loads(smash_gg_query(query, variables))  # query smash_gg for the event page
        user_sets.append(parse_entrant_set(user_page['data']['event']['entrants']['nodes']))  # parse user

    user_sets = list(itertools.chain.from_iterable(user_sets))  # concatenate event page lists
    return user_sets


def get_set_pages_from_event(url_slugs: Dict, page_count: int, per_page=20) -> List:
    query = """
        query EventQuery($event_slug: String, $page: Int, $perPage: Int) {
            event(slug: $event_slug) {
                id
                sets(page: $page, perPage: $perPage, sortType: STANDARD) {
                    nodes {
                        id
                        completedAt
                        slots {
                            standing {
                                stats {
                                    score {
                                        value
                                    }
                                }
                            }
                            entrant {
                                participants {
                                    gamerTag
                                    user {
                                        slug
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
    event_sets = []
    if config.settings['show_progress'] == 'True' and page_count > 1:
        print("get_set_pages_from_event")
        pages_enum = tqdm(range(1, page_count+1))
    else:
        pages_enum = range(1, page_count+1)
    for page in pages_enum:
        variables = """
            {{
                "event_slug":"tournament/{}/event/{}",
                "page": {},
                "perPage": {}
            }}
            """.format(url_slugs['tournament'], url_slugs['event'], page, per_page)
        event_page = json.loads(smash_gg_query(query, variables))  # query smash_gg for the event page
        event_sets.append(parse_set_nodes(event_page['data']['event']['sets']['nodes']))  # parse the event set page

    event_sets = list(itertools.chain.from_iterable(event_sets))  # concatenate event page lists

    return event_sets


def parse_event_nodes(event_nodes):
    events = []
    for en in event_nodes:
        events.append({
            "event_slug": en['slug'],
            "videogame_id": en['videogame']['id'],
            "videogame_name": en['videogame']['displayName']
        })
    return events


def get_events_from_user_slug(user_slug: str, per_page=20) -> List:
    page_query = """
            query QueryUser($user_slug: String, $perPage: Int) {
                user(slug: $user_slug) {
                    events(query: {
                        perPage: $perPage
                        }) {
                            pageInfo {
                            total
                            totalPages
                        }
                    }
                }
            }
            """
    page_vars = """
        {{
          "user_slug":"{}",
          "perPage": {}
        }}
    """.format(user_slug, per_page)

    page_count = json.loads(smash_gg_query(page_query, page_vars))  # query smash_gg
    page_count = page_count['data']['user']['events']['pageInfo']['totalPages']

    query = """
        query QueryUser($user_slug: String, $page:Int, $perPage: Int) {
            user(slug: $user_slug) {
                id
                name
                slug
                events(query: {
                    page: $page
                    perPage: $perPage
                    }) {
                        pageInfo {
                        total
                        totalPages
                    }
                    nodes {
                        id
                        name
                        slug
                        videogame {
                            id
                            displayName
                        }
                    }
                }
            }
        }
        """
    user_events = []
    if config.settings['show_progress'] == 'True' and page_count > 1:
        print("get_events_from_user_slug")
        pages_enum = tqdm(range(1, page_count+1))
    else:
        pages_enum = range(1, page_count+1)
    for page in pages_enum:
        variables = """
            {{
                "user_slug":"{}",
                "page": {},
                "perPage": {}
            }}
            """.format(user_slug, page, per_page)
        event_page = json.loads(smash_gg_query(query, variables))  # query smash_gg for the event page
        user_events.append(parse_event_nodes(event_page['data']['user']['events']['nodes']))  # parse the event set page

    event_sets = list(itertools.chain.from_iterable(user_events))  # concatenate event page lists

    return event_sets


def get_event_id_and_sets(full_url: str):
    per_page = 40
    url_slugs = parse_event_url(full_url)
    print(url_slugs)
    # query smash gg
    event = get_event_attributes(url_slugs, per_page)
    event_sets = get_set_pages_from_event(url_slugs, event['page_count'], per_page)

    return event, event_sets
