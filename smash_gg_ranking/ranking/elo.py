from typing import List, Dict

from smash_gg_ranking.config import config
from smash_gg_ranking.db.models import RankingSet


def calc_expected_outcome(team_a_elo: float, team_b_elo: float) -> float:
    #  https://en.wikipedia.org/wiki/Elo_rating_system
    beta = config.settings['elo_beta']
    return 1 / (1 + pow(10, (team_b_elo - team_a_elo) / beta))


def calc_elo_change(winner_elo: float, winner_score: int,  loser_elo: float, loser_score: int) -> (float, float):
    k = config.settings['elo_K']
    expected_winner_probability = calc_expected_outcome(winner_elo, loser_elo)
    expected_loser_probability = calc_expected_outcome(loser_elo, winner_elo)

    total_score = winner_score+loser_score
    winner_change = (k * ((winner_score/total_score) - expected_winner_probability))
    loser_change = (k * ((loser_score/total_score) - expected_loser_probability))

    return winner_change, loser_change


def update_ranking_set_points(ranking_sets: List[RankingSet]):
    participants_elo = {}  # store teams as through matches
    for r_set in ranking_sets:
        if r_set.winner_id not in participants_elo.keys():  # if no elo
            participants_elo[r_set.winner_id] = config.settings['elo_initial']
        if r_set.loser_id not in participants_elo.keys():  # if no elo
            participants_elo[r_set.loser_id] = config.settings['elo_initial']

        # calc elo change
        r_set.winner_change, r_set.loser_change = calc_elo_change(
            participants_elo[r_set.winner_id], r_set.winner_score, participants_elo[r_set.loser_id], r_set.loser_score)

        # save old elo
        r_set.winner_points = participants_elo[r_set.winner_id]
        r_set.loser_points = participants_elo[r_set.loser_id]
        # add elo to current elo
        participants_elo[r_set.winner_id] = participants_elo[r_set.winner_id] + r_set.winner_change
        participants_elo[r_set.loser_id] = participants_elo[r_set.loser_id] + r_set.loser_change

