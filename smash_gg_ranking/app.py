from flask import Flask, redirect
from flask import render_template

from views import ranking, events

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
    return render_template('events.html', events=event_sets, ranking_name=ranking_name)


