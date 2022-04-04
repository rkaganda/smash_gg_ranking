from flask import Flask, redirect
from flask import render_template
import logging
from flask import request

from config import config
from views import ranking, events, participants, matches

app = Flask(__name__)

logger = logging.getLogger('app')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def generate_paging():
    page_params = {
        "page_num": request.args.get('page_num', default=1, type=int),
        "page_size": request.args.get('page_size', default=config.settings['default_page_size'], type=int)
    }
    page_params['page_size'] = min(config.settings['max_page_size'], page_params['page_size'])
    return page_params


@app.route('/')
def home():
    return redirect("/ranking/", code=302)


@app.route('/ranking/')
def view_rankings():
    rankings = ranking.get_rankings()
    return render_template('ranking.html', rankings=rankings)


@app.route('/ranking/<ranking_id>/events/')
def view_events(ranking_id=None):
    page_params = generate_paging()
    ranking_data, event_sets, paging_info = events.get_events(ranking_id, page_params)
    return render_template('ranking/events.html',
                           events=event_sets, ranking_data=ranking_data, paging_info=paging_info)


@app.route('/ranking/<ranking_id>/participants/')
@app.route('/ranking/<ranking_id>/event/<event_id>/participants/')
def view_ranking_participants(ranking_id=None, event_id=None):
    page_params = generate_paging()
    ranking_data, participants_set, event_data, paging_info = participants.get_ranking_participants(ranking_id, event_id, page_params)
    return render_template('ranking/participants.html', participants=participants_set, ranking_data=ranking_data,
                           event_data=event_data, paging_info=paging_info)


@app.route('/ranking/<ranking_id>/event/<event_id>/matches')
def view_ranking_event_matches(ranking_id=None, event_id=None):
    page_params = generate_paging()
    ranking_data, event_data, event_sets, paging_info = matches.get_ranking_sets(ranking_id, event_id, page_params)
    return render_template('ranking/event/matches.html',
                           event_sets=event_sets, ranking_data=ranking_data,
                           event_data=event_data, paging_info=paging_info)


@app.route('/ranking/<ranking_id>/participant/<participant_id>/matches')
@app.route('/ranking/<ranking_id>/participant/<participant_id>/matches/')
def view_ranking_participant_matches(ranking_id=None, participant_id=None):
    page_params = generate_paging()
    event_id = request.args.get('event', default=None, type=int)
    ranking_data, event_data, participant_data, participant_sets, paging_info = matches.get_participant_sets(
        ranking_id, event_id, participant_id, page_params)
    return render_template('ranking/participant/matches.html',
                           participant_sets=participant_sets, participant_data=participant_data,
                           ranking_data=ranking_data, event_data=event_data, paging_info=paging_info)
