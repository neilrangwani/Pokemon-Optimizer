"""
optimizer/ilp_solver.py — Integer Linear Programming solver via PuLP.

Formulation
-----------
Decision variables:
    x_i ∈ {0, 1}  for each Pokemon i in the eligible pool
    y_t ∈ {0, 1}  for each type t (auxiliary: 1 if team covers type t offensively)

Hard constraints:
    ∑ x_i = 6                          (team size = 6)
    x_i = 1  ∀ anchor Pokemon i        (anchor constraint)
    x_i = 0  ∀ excluded Pokemon i      (legendary / gen filter — applied in pool)

Linearized objective components:
    offensive_coverage:
        y_t ≤ ∑_{i: pokemon i covers type t SE} x_i   (y_t can only be 1 if some team member covers t)
        y_t is binary
        Contribution: ∑_t w_freq_t * y_t  (weighted by type frequency)

    defensive_synergy:
        For each type t, let weak_t = ∑_{i: pokemon i is weak to t} x_i
        Penalty variable p_t ≥ 0 captures shared weaknesses
        p_t ≥ weak_t - 2  (penalty kicks in at 3+ shared weaknesses)
        Contribution: -∑_t w_freq_t * p_t

    stat_distribution & role_diversity:
        These components are inherently non-linear (thresholding, role classification).
        The ILP linearizes them via indicator variables per archetype.

        For stat_distribution:
            Define binary z_arch ∈ {0,1} for each archetype a
            z_arch ≤ ∑_{i: pokemon i fits archetype a} x_i
            Contribution: ∑_a z_arch / num_archetypes

        Role diversity is approximated similarly.

    moveset_quality: contributed as a per-Pokemon constant score (pre-computed).

The ILP objective = weighted sum of all linearized components.
This gives an exact optimal solution for the linearized formulation.
Non-linear interactions (e.g., synergy between specific pairs) are handled by the GA.
"""

from __future__ import annotations

import time
from collections import defaultdict

import pulp

from optimizer.constraints import build_eligible_pool, validate_team
from optimizer.models import (
    OptimizeRequest,
    OptimizeResponse,
    Pokemon,
    PokemonType,
    ScoreWeights,
    Team,
    TeamMember,
)
from optimizer.scoring import (
    ROLE_THRESHOLDS,
    TYPE_FREQUENCY_WEIGHTS,
    TYPES,
    classify_role,
    load_type_chart,
    score_team,
)

# Archetype indicator functions — map a Pokemon to True if it fits the archetype
ARCHETYPES: dict[str, callable] = {
    "fast_attacker":  lambda p: p.stats.speed >= 100 and (p.stats.attack >= 90 or p.stats.sp_atk >= 90),
    "physical_wall":  lambda p: p.stats.defense >= 100 and p.stats.hp >= 80,
    "special_wall":   lambda p: p.stats.sp_def >= 100 and p.stats.hp >= 80,
    "bulky_attacker": lambda p: p.stats.hp >= 80 and (p.stats.attack >= 90 or p.stats.sp_atk >= 90) and p.stats.speed < 100,
    "speed_control":  lambda p: p.stats.speed >= 110 or p.stats.speed <= 55,
}


def _covers_type_se(pokemon: Pokemon, target_type: str, chart: dict) -> bool:
    """True if this Pokemon's STAB moves can hit target_type super-effectively."""
    for ptype in pokemon.types:
        if chart[ptype.value][target_type] >= 2.0:
            return True
    return False


def _is_weak_to(pokemon: Pokemon, attacker_type: str, chart: dict) -> bool:
    """True if this Pokemon takes super-effective damage from attacker_type."""
    mult = 1.0
    for dt in pokemon.types:
        mult *= chart[attacker_type][dt.value]
    return mult > 1.0


def solve(request: OptimizeRequest) -> tuple[Team, float]:
    """
    Solve the team optimization ILP.

    Returns:
        (optimal_team, solve_time_seconds)
    """
    t0 = time.perf_counter()
    pool = build_eligible_pool(request)

    if len(pool) < 6:
        from optimizer.constraints import load_all_pokemon
        all_gens = sorted({p.generation for p in load_all_pokemon()})
        raise ValueError(
            f"Pool has only {len(pool)} eligible Pokémon (need at least 6). "
            f"Data is loaded for Gen {', '.join(str(g) for g in all_gens)} only. "
            "Select a generation with data, or relax filters (e.g., allow legendaries)."
        )

    weights = request.weights or ScoreWeights.for_play_style(request.play_style)
    chart = load_type_chart()
    anchor_names = set(request.anchor_pokemon)

    # Build index for fast lookup
    n = len(pool)
    idx_to_pokemon = {i: p for i, p in enumerate(pool)}

    # Pre-compute coverage and weakness bitmaps
    covers_type: dict[str, list[int]] = {t: [] for t in TYPES}     # type → [pokemon indices that cover it SE]
    weak_to_type: dict[str, list[int]] = {t: [] for t in TYPES}    # type → [pokemon indices weak to it]

    for i, p in idx_to_pokemon.items():
        for t in TYPES:
            if _covers_type_se(p, t, chart):
                covers_type[t].append(i)
            if _is_weak_to(p, t, chart):
                weak_to_type[t].append(i)

    # Archetype membership
    archetype_members: dict[str, list[int]] = {
        arch: [i for i, p in idx_to_pokemon.items() if fn(p)]
        for arch, fn in ARCHETYPES.items()
    }

    # Per-Pokemon stat score (contributes to moveset_quality component)
    # Normalize BST to [0, 1] as a simple proxy when no moveset data exists
    max_bst = max(p.bst for p in pool)
    bst_score = {i: p.bst / max_bst for i, p in idx_to_pokemon.items()}

    # ---------------------------------------------------------------------------
    # Build the LP
    # ---------------------------------------------------------------------------
    prob = pulp.LpProblem("PokemonTeamOptimizer", pulp.LpMaximize)

    # Decision variables
    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]
    # Auxiliary: type coverage indicators
    y = {t: pulp.LpVariable(f"y_{t}", cat="Binary") for t in TYPES}
    # Auxiliary: shared weakness penalty variables
    p_weak = {t: pulp.LpVariable(f"p_{t}", lowBound=0) for t in TYPES}
    # Auxiliary: archetype coverage indicators
    z = {arch: pulp.LpVariable(f"z_{arch}", cat="Binary") for arch in ARCHETYPES}

    # ---------------------------------------------------------------------------
    # Hard constraints
    # ---------------------------------------------------------------------------
    # Team size
    prob += pulp.lpSum(x) == 6, "team_size"

    # Anchor constraints
    for i, p in idx_to_pokemon.items():
        if p.name in anchor_names:
            prob += x[i] == 1, f"anchor_{p.name}"

    # Required type constraints: at least one team member must have each required type
    for req_type in request.required_types:
        members_with_type = [i for i, p in idx_to_pokemon.items() if req_type in p.types]
        if members_with_type:
            prob += pulp.lpSum(x[i] for i in members_with_type) >= 1, f"req_type_{req_type.value}"

    # ---------------------------------------------------------------------------
    # Coverage linearization: y_t ≤ ∑_{i covers t} x_i
    # If no team member covers type t, y_t must be 0.
    # ---------------------------------------------------------------------------
    for t in TYPES:
        coverers = covers_type[t]
        if coverers:
            prob += y[t] <= pulp.lpSum(x[i] for i in coverers), f"cover_ub_{t}"
        else:
            prob += y[t] == 0, f"cover_impossible_{t}"

    # ---------------------------------------------------------------------------
    # Weakness penalty: p_weak_t ≥ (weak_count_t - 2), captures 3+ shared weaknesses
    # ---------------------------------------------------------------------------
    for t in TYPES:
        weak_list = weak_to_type[t]
        if weak_list:
            prob += (
                p_weak[t] >= pulp.lpSum(x[i] for i in weak_list) - 2,
                f"weak_penalty_{t}",
            )

    # ---------------------------------------------------------------------------
    # Archetype coverage: z_arch ≤ ∑_{i fits arch} x_i
    # ---------------------------------------------------------------------------
    for arch, members in archetype_members.items():
        if members:
            prob += z[arch] <= pulp.lpSum(x[i] for i in members), f"arch_ub_{arch}"
        else:
            prob += z[arch] == 0, f"arch_impossible_{arch}"

    # ---------------------------------------------------------------------------
    # Objective function (all components normalized to comparable scales)
    # ---------------------------------------------------------------------------
    total_freq_weight = sum(TYPE_FREQUENCY_WEIGHTS.values())

    # W1: Offensive coverage (weighted by type frequency)
    offensive = pulp.lpSum(
        TYPE_FREQUENCY_WEIGHTS.get(t, 1.0) * y[t] for t in TYPES
    ) / total_freq_weight

    # W2: Defensive synergy (penalize shared weaknesses)
    weakness_penalty = pulp.lpSum(
        TYPE_FREQUENCY_WEIGHTS.get(t, 1.0) * p_weak[t] for t in TYPES
    ) / (total_freq_weight * 4)  # normalize: max 4 extra weak on a single type
    defensive = 1.0 - weakness_penalty

    # W3: Stat distribution (archetype coverage)
    stat_dist = pulp.lpSum(z[arch] for arch in ARCHETYPES) / len(ARCHETYPES)

    # W4: Role diversity (approximate via archetype coverage for ILP)
    role_div = stat_dist  # ILP uses same archetype proxy

    # W5: Moveset quality (BST proxy per pokemon)
    moveset_q = pulp.lpSum(bst_score[i] * x[i] for i in range(n)) / 6

    prob += (
        weights.offensive_coverage * offensive
        + weights.defensive_synergy  * defensive
        + weights.stat_distribution  * stat_dist
        + weights.role_diversity     * role_div
        + weights.moveset_quality    * moveset_q
    ), "composite_objective"

    # ---------------------------------------------------------------------------
    # Solve
    # ---------------------------------------------------------------------------
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=30)
    status = prob.solve(solver)

    solve_time = time.perf_counter() - t0

    if pulp.LpStatus[status] not in ("Optimal", "Feasible"):
        raise RuntimeError(
            f"ILP solver returned status: {pulp.LpStatus[status]}. "
            "Try relaxing constraints (larger pool, fewer anchors)."
        )

    # Extract solution
    selected = [idx_to_pokemon[i] for i in range(n) if pulp.value(x[i]) > 0.5]

    members = [
        TeamMember(pokemon=p, is_anchor=(p.name in anchor_names))
        for p in selected
    ]

    composite, breakdown = score_team(members, weights, request.play_style, request.weather_condition)

    team = Team(
        members=members,
        score=composite,
        score_breakdown=breakdown,
        solver="ilp",
        solve_time_seconds=round(solve_time, 3),
    )
    return team, solve_time


def solve_and_respond(request: OptimizeRequest) -> OptimizeResponse:
    pool = build_eligible_pool(request)
    team, _ = solve(request)
    return OptimizeResponse(
        request=request,
        teams={"ilp": team},
        pool_size=len(pool),
    )
