from flask import Flask, redirect
from flask import render_template
import logging

from config import config
from views import ranking, events, participants, matches

app = Flask(__name__)

logger = logging.getLogger('app')
logger.setLevel(config.settings['log_level'])
handler = logging.FileHandler(filename=config.settings['log_path'], encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


@app.route('/')
def home():
    return redirect("/ranking/", code=302)


@app.route('/ranking/')
def view_rankings():
    rankings = ranking.get_rankings()
    return render_template('ranking.html', rankings=rankings)


@app.route('/ranking/events/<ranking_id>')
def view_events(ranking_id=None):
    ranking_data, event_sets = events.get_events(ranking_id)
    return render_template('ranking/events.html', events=event_sets, ranking_data=ranking_data)


@app.route('/ranking/<ranking_id>/participants/')
def view_ranking_participants(ranking_id=None):
    ranking_data, participants_set = participants.get_ranking_participants(ranking_id)
    return render_template('ranking/participants.html', participants=participants_set, ranking_data=ranking_data)


@app.route('/ranking/<ranking_id>/event/<event_id>/matches')
def view_matches_ranking_event(ranking_id=None, event_id=None):
    ranking_data, event_data, event_sets = matches.get_ranking_sets(ranking_id, event_id)
    return render_template('ranking/event/matches.html', event_sets=event_sets, ranking_data=ranking_data,
                           event_data=event_data)


@app.route('/ranking/<ranking_id>/participant/<participant_id>/matches')
def view_matches_ranking_participant(ranking_id=None, participant_id=None):
    ranking_data, participant_data, participant_sets = matches.get_participant_sets(ranking_id, participant_id)
    logging.debug("participant_data={}".format(participant_data))
    return render_template('ranking/participant/matches.html', participant_sets=participant_sets,
                           participant_data=participant_data, ranking_data=ranking_data)
