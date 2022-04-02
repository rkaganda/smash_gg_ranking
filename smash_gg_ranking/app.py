from flask import Flask
from flask import render_template

from views import ranking

from config import config
app = Flask(__name__)


# @app.route('/hello/')
# @app.route('/hello/<name>')
# def hello(name=None):
#     return render_template('hello.html', name=name)


@app.route('/ranking/')
def view_rankings():
    rankings = ranking.get_rankings()
    return render_template('ranking.html', rankings=rankings)


@app.route('/ranking/events/<ranking_id>')
def view_events(ranking_id=None):
    ranking_name, events = ranking.get_events(ranking_id)
    return render_template('events.html', events=events, ranking_name=ranking_name)


