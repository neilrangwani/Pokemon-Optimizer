"""
optimizer/scoring.py — Composite team scoring functions.

Scores a team of 6 Pokemon across five objectives:
  1. Offensive coverage  — how many of the 18 types can the team hit super-effectively?
  2. Defensive synergy   — how many shared weaknesses does the team have?
  3. Stat distribution   — does the team cover multiple stat archetypes?
  4. Role diversity      — does the team fill multiple competitive roles?
  5. Moveset quality     — how well do the movesets provide coverage and utility?

Each component returns a value in [0, 1]. The composite score is a weighted sum.

All scores are deterministic and depend only on the team composition + weights.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from optimizer.models import (
    MoveCategory,
    PlayStyle,
    Pokemon,
    PokemonRole,
    PokemonType,
    ScoreWeights,
    Team,
    TeamMember,
    WeatherCondition,
)

_TYPE_CHART_PATH = Path(__file__).parent.parent / "data" / "type_chart.json"

TYPES = [t.value for t in PokemonType]

# Types weighted by competitive frequency (how often they appear as attacking types in the meta).
# Higher = more valuable to cover offensively.
TYPE_FREQUENCY_WEIGHTS: dict[str, float] = {
    "Water":    1.4,
    "Ground":   1.3,
    "Fire":     1.2,
    "Electric": 1.2,
    "Ice":      1.1,
    "Fighting": 1.1,
    "Rock":     1.0,
    "Grass":    1.0,
    "Dragon":   1.0,
    "Psychic":  0.9,
    "Flying":   0.9,
    "Dark":     0.9,
    "Steel":    0.9,
    "Ghost":    0.8,
    "Bug":      0.8,
    "Poison":   0.7,
    "Normal":   0.7,
    "Fairy":    0.9,
}

# Stat thresholds for role classification
ROLE_THRESHOLDS = {
    "speed_fast":    100,   # Speed >= this → "fast"
    "atk_high":      100,   # Attack >= this → physical attacker
    "spatk_high":    100,   # SpAtk >= this → special attacker
    "def_wall":      100,   # Defense >= this → physical wall
    "spdef_wall":    100,   # SpDef >= this → special wall
    "hp_bulk":        90,   # HP >= this → bulky
    "speed_tr":       60,   # Speed <= this → Trick Room candidate
}

# Weather synergy: which abilities / types pair with each condition
WEATHER_SYNERGY: dict[WeatherCondition, dict] = {
    WeatherCondition.RAIN: {
        "abilities": {"swift-swim", "rain-dish", "dry-skin", "hydration", "forecast"},
        "setter_abilities": {"drizzle"},
        "boost_types": {"Water"},
        "weaken_types": {"Fire"},
    },
    WeatherCondition.SUN: {
        "abilities": {"chlorophyll", "solar-power", "leaf-guard", "forecast"},
        "setter_abilities": {"drought"},
        "boost_types": {"Fire"},
        "weaken_types": {"Water"},
    },
    WeatherCondition.SAND: {
        "abilities": {"sand-rush", "sand-force", "sand-veil"},
        "setter_abilities": {"sand-stream"},
        "immune_types": {"Rock", "Ground", "Steel"},
        "spdef_bonus_types": {"Rock"},
    },
    WeatherCondition.SNOW: {
        "abilities": {"slush-rush", "snow-cloak", "forecast", "ice-body"},
        "setter_abilities": {"snow-warning"},
        "immune_types": {"Ice"},
        "def_bonus_types": {"Ice"},
    },
}


@lru_cache(maxsize=1)
def load_type_chart() -> dict[str, dict[str, float]]:
    with open(_TYPE_CHART_PATH) as f:
        raw = json.load(f)
    return raw["type_chart"]


def type_effectiveness(attacker: str, defender_types: list[str]) -> float:
    """Return the combined effectiveness of attacker type vs a Pokemon with defender_types."""
    chart = load_type_chart()
    mult = 1.0
    for dt in defender_types:
        mult *= chart[attacker][dt]
    return mult


def classify_role(p: Pokemon) -> PokemonRole:
    """Classify a Pokemon into a competitive role based on its stat profile."""
    s = p.stats
    t = ROLE_THRESHOLDS

    is_fast     = s.speed >= t["speed_fast"]
    is_physical = s.attack >= t["atk_high"]
    is_special  = s.sp_atk >= t["spatk_high"]
    is_phys_def = s.defense >= t["def_wall"] and s.hp >= t["hp_bulk"]
    is_spec_def = s.sp_def >= t["spdef_wall"] and s.hp >= t["hp_bulk"]
    is_tr_cand  = s.speed <= t["speed_tr"]

    # Pivot: moderate stats across the board, not extreme in any direction
    is_pivot = (
        not (is_physical or is_special or is_phys_def or is_spec_def)
        and s.stats.total < 500  # type: ignore[attr-defined]
    ) if hasattr(s, "stats") else False

    # Recompute without HP requirement for defense-only walls (e.g. Steelix: def=230, hp=75)
    is_phys_def_only = s.defense >= t["def_wall"]
    is_spec_def_only = s.sp_def >= t["spdef_wall"]

    if is_phys_def and is_spec_def:
        return PokemonRole.SUPPORT
    if is_phys_def and not is_special:
        return PokemonRole.PHYSICAL_WALL
    if is_phys_def_only and not is_phys_def and not is_special:
        # High defense but low HP — still a physical wall (e.g. Steelix)
        return PokemonRole.PHYSICAL_WALL
    if is_spec_def and not is_physical:
        return PokemonRole.SPECIAL_WALL
    if is_physical and is_fast and not is_phys_def:
        return PokemonRole.PHYSICAL_SWEEPER
    if is_special and is_fast and not is_spec_def:
        return PokemonRole.SPECIAL_SWEEPER
    if is_tr_cand and (is_physical or is_special):
        return PokemonRole.PHYSICAL_SWEEPER if s.attack > s.sp_atk else PokemonRole.SPECIAL_SWEEPER
    # Fallback: pick best-fitting offensive role rather than returning MIXED
    # Check if any defensive stat is dominant
    if s.defense >= 85 and s.defense >= s.attack and s.defense >= s.sp_atk:
        return PokemonRole.PHYSICAL_WALL
    if s.sp_def >= 85 and s.sp_def >= s.attack and s.sp_def >= s.sp_atk:
        return PokemonRole.SPECIAL_WALL
    return PokemonRole.PHYSICAL_SWEEPER if s.attack >= s.sp_atk else PokemonRole.SPECIAL_SWEEPER


# ---------------------------------------------------------------------------
# Individual scoring components
# ---------------------------------------------------------------------------

def score_offensive_coverage(members: list[TeamMember]) -> float:
    """
    Score = weighted fraction of 18 types the team can hit super-effectively (>=2x).

    A type is "covered" if at least one team member's STAB or moveset covers it SE.
    Uses TYPE_FREQUENCY_WEIGHTS to reward covering meta-relevant types more.

    Returns value in [0, 1].
    """
    chart = load_type_chart()
    covered: dict[str, float] = {t: 0.0 for t in TYPES}

    for member in members:
        p = member.pokemon
        # STAB coverage: check what each of the Pokemon's own types hits SE
        for ptype in p.types:
            for target_type in TYPES:
                eff = chart[ptype.value][target_type]
                if eff > covered[target_type]:
                    covered[target_type] = eff

        # Moveset coverage (if available)
        if member.moveset:
            for move in member.moveset.moves:
                if move.category != MoveCategory.STATUS and move.power:
                    for target_type in TYPES:
                        # For dual-type defenders, we score against single types here
                        # (full dual-type scoring handled in defensive component)
                        eff = chart[move.type.value][target_type]
                        if eff > covered[target_type]:
                            covered[target_type] = eff

    # Weighted score: coverage_value * frequency_weight, normalized
    total_weight = sum(TYPE_FREQUENCY_WEIGHTS.values())
    score = 0.0
    for t in TYPES:
        w = TYPE_FREQUENCY_WEIGHTS.get(t, 1.0)
        # Full SE (2x+) = 1.0 contribution, partial = 0 (we want SE, not neutral)
        if covered[t] >= 2.0:
            score += w
        elif covered[t] >= 1.0:
            score += w * 0.1  # tiny bonus for neutral coverage (at least not resisted)

    return min(score / total_weight, 1.0)


def score_defensive_synergy(members: list[TeamMember]) -> float:
    """
    Score based on minimizing shared weaknesses across the team.

    Penalty structure:
      - If 1 Pokemon is weak to type X: small penalty
      - If 2 Pokemon are weak:          medium penalty
      - If 3+ Pokemon are weak:         exponential penalty
    Bonus: for each immunity (0x) that covers a teammate's weakness.

    Returns value in [0, 1] (higher = better defensive synergy).
    """
    chart = load_type_chart()

    # For each type: count weaknesses and immunities on the team
    weakness_counts: dict[str, int] = {t: 0 for t in TYPES}
    immunity_types: set[str] = set()

    for member in members:
        defender_types = [pt.value for pt in member.pokemon.types]
        for attacker_type in TYPES:
            eff = 1.0
            for dt in defender_types:
                eff *= chart[attacker_type][dt]
            if eff == 0.0:
                immunity_types.add(attacker_type)
            elif eff > 1.0:
                weakness_counts[attacker_type] += 1

    # Penalty calculation
    total_penalty = 0.0
    max_possible_penalty = 0.0
    for t in TYPES:
        w = TYPE_FREQUENCY_WEIGHTS.get(t, 1.0)
        n = weakness_counts[t]
        if n == 0:
            penalty = 0.0
        elif n == 1:
            penalty = 0.1 * w
        elif n == 2:
            penalty = 0.3 * w
        else:
            # Exponential: 3 → 0.6w, 4 → 0.9w, 5 → 1.1w, 6 → 1.2w
            penalty = min(0.6 * w * (1.5 ** (n - 3)), 1.5 * w)
        total_penalty += penalty
        max_possible_penalty += 1.5 * w  # max penalty per type

    # Immunity bonus
    immunity_bonus = len(immunity_types) * 0.03  # small reward per immunity

    raw_score = 1.0 - (total_penalty / max(max_possible_penalty, 1.0)) + immunity_bonus
    return max(0.0, min(raw_score, 1.0))


def score_stat_distribution(members: list[TeamMember]) -> float:
    """
    Score based on coverage of stat archetypes across the team.

    Checks whether the team has at least one Pokemon in each of:
      - Fast attacker (Speed >= 100, high offensive stat)
      - Physical wall (Def >= 100, HP >= 90)
      - Special wall (SpDef >= 100, HP >= 90)
      - Bulky attacker (HP >= 80, offensive stat >= 90)
      - Speed control (very fast or very slow for Trick Room)

    Also penalizes redundancy (3+ Pokemon with same role).
    Returns value in [0, 1].
    """
    roles = [classify_role(m.pokemon) for m in members]

    archetype_checks = {
        "fast_attacker": lambda p: (
            p.stats.speed >= 100
            and (p.stats.attack >= 90 or p.stats.sp_atk >= 90)
        ),
        "physical_wall": lambda p: p.stats.defense >= 100 and p.stats.hp >= 80,
        "special_wall":  lambda p: p.stats.sp_def >= 100 and p.stats.hp >= 80,
        "bulky_attacker": lambda p: (
            p.stats.hp >= 80
            and (p.stats.attack >= 90 or p.stats.sp_atk >= 90)
            and p.stats.speed < 100
        ),
        "speed_control": lambda p: p.stats.speed >= 110 or p.stats.speed <= 55,
    }

    covered = 0
    for check in archetype_checks.values():
        if any(check(m.pokemon) for m in members):
            covered += 1

    archetype_score = covered / len(archetype_checks)

    # Redundancy penalty: count role concentrations
    from collections import Counter
    role_counts = Counter(roles)
    redundancy = sum(max(0, count - 2) for count in role_counts.values())
    redundancy_penalty = min(redundancy * 0.08, 0.3)

    return max(0.0, archetype_score - redundancy_penalty)


def score_role_diversity(
    members: list[TeamMember],
    play_style: PlayStyle = PlayStyle.BALANCED,
    weather: WeatherCondition | None = None,
) -> float:
    """
    Score based on how well the team's roles match the chosen play style.

    Returns value in [0, 1].
    """
    from collections import Counter
    roles = [classify_role(m.pokemon) for m in members]
    role_set = set(roles)
    role_counts = Counter(roles)

    # Base diversity score: reward covering 4+ distinct roles
    diversity = len(role_set) / len(PokemonRole)

    # Play style role bonuses
    style_bonus = 0.0

    if play_style == PlayStyle.HYPER_OFFENSE:
        sweepers = role_counts.get(PokemonRole.PHYSICAL_SWEEPER, 0) + role_counts.get(PokemonRole.SPECIAL_SWEEPER, 0)
        style_bonus = min(sweepers / 3, 1.0) * 0.3

    elif play_style == PlayStyle.STALL:
        walls = (
            role_counts.get(PokemonRole.PHYSICAL_WALL, 0)
            + role_counts.get(PokemonRole.SPECIAL_WALL, 0)
            + role_counts.get(PokemonRole.SUPPORT, 0)
        )
        style_bonus = min(walls / 4, 1.0) * 0.3

    elif play_style == PlayStyle.TRICK_ROOM:
        # Reward slow, powerful Pokemon
        tr_mons = sum(
            1 for m in members
            if m.pokemon.stats.speed <= ROLE_THRESHOLDS["speed_tr"]
            and (m.pokemon.stats.attack >= 90 or m.pokemon.stats.sp_atk >= 90)
        )
        style_bonus = min(tr_mons / 4, 1.0) * 0.3
        # Must have at least one Trick Room setter (support role)
        if PokemonRole.SUPPORT in role_set:
            style_bonus += 0.1

    elif play_style == PlayStyle.WEATHER and weather:
        synergy = WEATHER_SYNERGY[weather]
        # Reward weather setter + weather abusers
        setters = sum(
            1 for m in members
            if any(a.name in synergy.get("setter_abilities", set()) for a in m.pokemon.abilities)
        )
        abusers = sum(
            1 for m in members
            if any(a.name in synergy.get("abilities", set()) for a in m.pokemon.abilities)
            or any(t.value in synergy.get("boost_types", set()) for t in m.pokemon.types)
        )
        style_bonus = (min(setters, 1) * 0.15) + (min(abusers / 3, 1.0) * 0.25)

    elif play_style == PlayStyle.SETUP_SWEEPER:
        # Bonus if the team has clear win conditions (sweepers) and support to enable them
        setup_mons = role_counts.get(PokemonRole.PHYSICAL_SWEEPER, 0) + role_counts.get(PokemonRole.SPECIAL_SWEEPER, 0)
        support_mons = role_counts.get(PokemonRole.SUPPORT, 0) + role_counts.get(PokemonRole.PIVOT, 0)
        style_bonus = min(setup_mons / 3, 1.0) * 0.15 + min(support_mons / 2, 1.0) * 0.15

    return min(diversity * 0.7 + style_bonus, 1.0)


def score_moveset_quality(members: list[TeamMember]) -> float:
    """
    Score the quality and complementarity of movesets across the team.

    Without moveset data, falls back to type-based coverage estimation.
    With moveset data, checks STAB usage, coverage moves, and team synergy.

    Returns value in [0, 1].
    """
    if not any(m.moveset for m in members):
        # Fallback: estimate from STAB coverage only
        return score_offensive_coverage(members) * 0.7

    chart = load_type_chart()
    total_score = 0.0

    for member in members:
        if not member.moveset:
            total_score += 0.5
            continue

        move_score = 0.0
        stab_types = {pt.value for pt in member.pokemon.types}
        has_stab = False
        has_coverage = False
        has_utility = False

        for move in member.moveset.moves:
            if move.category == MoveCategory.STATUS:
                has_utility = True
                continue
            if not move.power:
                has_utility = True
                continue

            if move.type.value in stab_types:
                has_stab = True
                move_score += 0.3
            else:
                # Non-STAB coverage move
                # Check if it hits something the STAB doesn't cover
                for target in TYPES:
                    stab_eff = max(
                        chart[st][target] for st in stab_types
                    ) if stab_types else 1.0
                    move_eff = chart[move.type.value][target]
                    if move_eff > stab_eff:
                        has_coverage = True
                        break
                move_score += 0.2 if has_coverage else 0.1

        if has_stab:     move_score += 0.1
        if has_coverage: move_score += 0.1
        if has_utility:  move_score += 0.1

        total_score += min(move_score, 1.0)

    per_member_avg = total_score / len(members)

    # Bonus for complementary coverage across the team
    team_coverage_bonus = score_offensive_coverage(members) * 0.2

    return min(per_member_avg * 0.8 + team_coverage_bonus, 1.0)


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------

def score_team(
    members: list[TeamMember],
    weights: ScoreWeights,
    play_style: PlayStyle = PlayStyle.BALANCED,
    weather: WeatherCondition | None = None,
) -> tuple[float, dict[str, float]]:
    """
    Compute composite team score and per-component breakdown.

    Returns:
        (composite_score, breakdown_dict)
        Both are in [0, 100] for human-readable display.
    """
    components = {
        "offensive_coverage": score_offensive_coverage(members),
        "defensive_synergy":  score_defensive_synergy(members),
        "stat_distribution":  score_stat_distribution(members),
        "role_diversity":     score_role_diversity(members, play_style, weather),
        "moveset_quality":    score_moveset_quality(members),
    }

    composite = (
        weights.offensive_coverage * components["offensive_coverage"]
        + weights.defensive_synergy  * components["defensive_synergy"]
        + weights.stat_distribution  * components["stat_distribution"]
        + weights.role_diversity     * components["role_diversity"]
        + weights.moveset_quality    * components["moveset_quality"]
    )

    # Scale to [0, 100] for display
    breakdown_display = {k: round(v * 100, 1) for k, v in components.items()}
    composite_display = round(composite * 100, 1)

    return composite_display, breakdown_display


def score_pokemon_list(
    pokemon_list: list[Pokemon],
    weights: ScoreWeights,
    play_style: PlayStyle = PlayStyle.BALANCED,
    weather: WeatherCondition | None = None,
) -> tuple[float, dict[str, float]]:
    """Convenience wrapper: score a plain list of Pokemon (no movesets)."""
    members = [TeamMember(pokemon=p) for p in pokemon_list]
    return score_team(members, weights, play_style, weather)
