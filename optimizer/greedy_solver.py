"""
optimizer/greedy_solver.py — Greedy heuristic with local search.

Algorithm
---------
Phase 1 — Greedy construction:
  Start with any anchor Pokemon. Then iteratively add the Pokemon from the
  remaining pool that maximizes the marginal gain in composite team score.
  This is O(n * 6) = O(n) and runs in milliseconds.

Phase 2 — Local search (1-opt):
  For each current team member (non-anchor), try swapping it with every
  other pool Pokemon. Accept the swap if it improves the team score.
  Repeat until no improving swap exists (local optimum).
  This is O(n * 6) per pass, usually converges in 2–5 passes.

The greedy result is a fast baseline to benchmark ILP and GA quality against.
It typically achieves 85–95% of the ILP optimal score in < 1% of the time.
"""

from __future__ import annotations

import time

from optimizer.constraints import build_eligible_pool
from optimizer.models import (
    OptimizeRequest,
    OptimizeResponse,
    Pokemon,
    ScoreWeights,
    Team,
    TeamMember,
)
from optimizer.scoring import score_team


def _score(
    pokemon_list: list[Pokemon],
    weights: ScoreWeights,
    request: OptimizeRequest,
) -> float:
    members = [TeamMember(pokemon=p) for p in pokemon_list]
    score, _ = score_team(members, weights, request.play_style, request.weather_condition)
    return score


def _greedy_construct(
    pool: list[Pokemon],
    anchors: list[Pokemon],
    weights: ScoreWeights,
    request: OptimizeRequest,
) -> list[Pokemon]:
    """
    Greedily build a team of 6 by adding the highest marginal-gain Pokemon one at a time.
    Starts from anchor Pokemon (if any).
    """
    team = list(anchors)
    remaining = [p for p in pool if p.name not in {a.name for a in anchors}]

    while len(team) < 6 and remaining:
        best_gain = -1.0
        best_pick = None

        current_score = _score(team, weights, request) if team else 0.0

        for candidate in remaining:
            trial = team + [candidate]
            gain = _score(trial, weights, request) - current_score
            if gain > best_gain:
                best_gain = gain
                best_pick = candidate

        if best_pick:
            team.append(best_pick)
            remaining.remove(best_pick)
        else:
            break

    return team


def _local_search(
    team: list[Pokemon],
    pool: list[Pokemon],
    anchors: set[str],
    weights: ScoreWeights,
    request: OptimizeRequest,
    max_passes: int = 10,
) -> list[Pokemon]:
    """
    1-opt local search: repeatedly try swapping each non-anchor team member
    with every pool member not already on the team.
    Stop when no improving swap is found (local optimum) or max_passes exhausted.
    """
    team_names = {p.name for p in team}
    pool_lookup = {p.name: p for p in pool}

    for _pass in range(max_passes):
        improved = False

        for slot_idx, current_member in enumerate(team):
            if current_member.name in anchors:
                continue  # Never swap anchors

            current_score = _score(team, weights, request)

            for candidate in pool:
                if candidate.name in team_names:
                    continue  # Already on team

                # Try swap
                trial = list(team)
                trial[slot_idx] = candidate
                trial_score = _score(trial, weights, request)

                if trial_score > current_score:
                    team_names.discard(current_member.name)
                    team_names.add(candidate.name)
                    team = trial
                    current_score = trial_score
                    improved = True
                    break  # Restart slot search with new team

        if not improved:
            break

    return team


def solve(request: OptimizeRequest) -> tuple[Team, float]:
    """
    Run greedy construction + local search.
    Returns (team, solve_time_seconds).
    """
    t0 = time.perf_counter()
    pool = build_eligible_pool(request)

    if len(pool) < 6:
        raise ValueError(f"Pool has only {len(pool)} eligible Pokemon (need at least 6).")

    weights = request.weights or ScoreWeights.for_play_style(request.play_style)
    anchor_names = set(request.anchor_pokemon)
    anchors = [p for p in pool if p.name in anchor_names]

    # Phase 1: Greedy construction
    team_pokemon = _greedy_construct(pool, anchors, weights, request)

    # Phase 2: Local search
    team_pokemon = _local_search(team_pokemon, pool, anchor_names, weights, request)

    solve_time = time.perf_counter() - t0

    members = [
        TeamMember(pokemon=p, is_anchor=(p.name in anchor_names))
        for p in team_pokemon
    ]
    composite, breakdown = score_team(members, weights, request.play_style, request.weather_condition)

    team = Team(
        members=members,
        score=composite,
        score_breakdown=breakdown,
        solver="greedy",
        solve_time_seconds=round(solve_time, 4),
    )
    return team, solve_time


def solve_and_respond(request: OptimizeRequest) -> OptimizeResponse:
    pool = build_eligible_pool(request)
    team, _ = solve(request)
    return OptimizeResponse(
        request=request,
        teams={"greedy": team},
        pool_size=len(pool),
    )
