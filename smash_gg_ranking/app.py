from flask import Flask, redirect
from flask import render_template

from views import ranking, events, participants

app = Flask(__name__)


@app.route('/')
def home():
    return redirect("/ranking/", code=302)


@app.route('/ranking/')
def view_rankings():
    rankings = ranking.get_rankings()
    return render_template('ranking.html', rankings=rankings)


@app.route('/ranking/events/<ranking_id>')
def view_events(ranking_id=None):
    ranking_name, event_sets = events.get_events(ranking_id)
    return render_template('ranking/events.html', events=event_sets, ranking_name=ranking_name)


@app.route('/ranking/participants/<ranking_id>')
def view_ranking_participants(ranking_id=None):
    ranking_name, participants_set = participants.get_ranking_participants(ranking_id)
    return render_template('ranking/participants.html', participants=participants_set, ranking_name=ranking_name)


