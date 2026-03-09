"""
tests/test_scoring.py — Unit tests for the scoring module.

Tests use hand-crafted Pokemon objects (no file I/O) to verify
scoring logic in isolation. All tests are deterministic.
"""

import pytest

from optimizer.models import (
    Ability,
    BaseStats,
    MoveCategory,
    Move,
    MoveSet,
    PlayStyle,
    Pokemon,
    PokemonRole,
    PokemonType,
    ScoreWeights,
    TeamMember,
    WeatherCondition,
)
from optimizer.scoring import (
    classify_role,
    score_defensive_synergy,
    score_offensive_coverage,
    score_role_diversity,
    score_stat_distribution,
    score_team,
)


# ---------------------------------------------------------------------------
# Test fixtures — hand-crafted Pokemon
# ---------------------------------------------------------------------------

def make_pokemon(
    name: str,
    types: list[str],
    hp=80, attack=80, defense=80, sp_atk=80, sp_def=80, speed=80,
    is_legendary=False,
) -> Pokemon:
    total = hp + attack + defense + sp_atk + sp_def + speed
    return Pokemon(
        id=1,
        name=name,
        display_name=name.title(),
        generation=1,
        types=[PokemonType(t) for t in types],
        stats=BaseStats(
            hp=hp, attack=attack, defense=defense,
            sp_atk=sp_atk, sp_def=sp_def, speed=speed, total=total,
        ),
        abilities=[Ability(name="test-ability")],
        is_legendary=is_legendary,
    )


def make_member(pokemon: Pokemon, moveset: MoveSet | None = None) -> TeamMember:
    return TeamMember(pokemon=pokemon, moveset=moveset)


def make_move(name: str, type_: str, category: str = "Physical", power: int = 80) -> Move:
    return Move(
        name=name,
        type=PokemonType(type_),
        category=MoveCategory(category),
        power=power,
    )


# Classic Gen 1 team for tests
@pytest.fixture
def gen1_team() -> list[TeamMember]:
    charizard  = make_pokemon("charizard",  ["Fire",    "Flying"], hp=78,  attack=84,  defense=78,  sp_atk=109, sp_def=85,  speed=100)
    blastoise  = make_pokemon("blastoise",  ["Water"],             hp=79,  attack=83,  defense=100, sp_atk=85,  sp_def=105, speed=78)
    venusaur   = make_pokemon("venusaur",   ["Grass",  "Poison"],  hp=80,  attack=82,  defense=83,  sp_atk=100, sp_def=100, speed=80)
    gengar     = make_pokemon("gengar",     ["Ghost",  "Poison"],  hp=60,  attack=65,  defense=60,  sp_atk=130, sp_def=75,  speed=110)
    alakazam   = make_pokemon("alakazam",   ["Psychic"],           hp=55,  attack=50,  defense=45,  sp_atk=135, sp_def=95,  speed=120)
    snorlax    = make_pokemon("snorlax",    ["Normal"],            hp=160, attack=110, defense=65,  sp_atk=65,  sp_def=110, speed=30)
    return [make_member(p) for p in [charizard, blastoise, venusaur, gengar, alakazam, snorlax]]


@pytest.fixture
def mono_fire_team() -> list[TeamMember]:
    """All-Fire team — terrible defensive synergy, great Fire coverage."""
    members = [
        make_pokemon(f"fire_{i}", ["Fire"], hp=80, attack=100, sp_atk=100, speed=90)
        for i in range(6)
    ]
    return [make_member(p) for p in members]


# ---------------------------------------------------------------------------
# Scoring component tests
# ---------------------------------------------------------------------------

class TestOffensiveCoverage:
    def test_diverse_team_scores_higher_than_mono(self, gen1_team, mono_fire_team):
        diverse_score = score_offensive_coverage(gen1_team)
        mono_score = score_offensive_coverage(mono_fire_team)
        assert diverse_score > mono_score, "Diverse team should cover more types"

    def test_score_in_range(self, gen1_team):
        score = score_offensive_coverage(gen1_team)
        assert 0.0 <= score <= 1.0

    def test_mono_fire_doesnt_cover_water(self, mono_fire_team):
        from optimizer.scoring import load_type_chart
        score = score_offensive_coverage(mono_fire_team)
        # Fire hits Water for 0.5x, so a mono-Fire team should score low
        assert score < 0.7, f"Mono-Fire should miss many types, got {score}"

    def test_with_coverage_moveset(self):
        """A Pokemon with a coverage move should score higher than STAB-only."""
        water_mon = make_pokemon("squirtle", ["Water"], attack=80, sp_atk=80)
        moveset = MoveSet(
            pokemon_name="squirtle",
            set_name="coverage",
            moves=[
                make_move("surf",          "Water",   "Special"),
                make_move("ice-beam",      "Ice",     "Special"),    # covers Grass
                make_move("thunderbolt",   "Electric","Special"),    # covers Water
                make_move("focus-blast",   "Fighting","Special"),    # covers Rock, Steel
            ],
        )
        member_with_moves = TeamMember(pokemon=water_mon, moveset=moveset)
        member_no_moves   = TeamMember(pokemon=water_mon)
        score_with = score_offensive_coverage([member_with_moves])
        score_without = score_offensive_coverage([member_no_moves])
        assert score_with > score_without


class TestDefensiveSynergy:
    def test_score_in_range(self, gen1_team, mono_fire_team):
        for team in (gen1_team, mono_fire_team):
            score = score_defensive_synergy(team)
            assert 0.0 <= score <= 1.0

    def test_shared_weaknesses_penalized(self, mono_fire_team):
        """6 Fire types → all share Water/Rock/Ground weaknesses → penalty applied.
        Penalty is normalized across all 18 types so even worst-case is ~20% deduction.
        The key invariant is that this scores strictly lower than a diverse team.
        """
        score = score_defensive_synergy(mono_fire_team)
        assert score < 0.9, f"Mono-Fire should incur shared-weakness penalty, got {score}"

    def test_diverse_team_better_synergy(self, gen1_team, mono_fire_team):
        gen1_score  = score_defensive_synergy(gen1_team)
        mono_score  = score_defensive_synergy(mono_fire_team)
        assert gen1_score > mono_score

    def test_immunity_rewarded(self):
        """Normal type is immune to Ghost — replacing a Psychic type (Ghost-weak) with
        Normal should improve defensive synergy since Normal removes a Ghost weakness."""
        shared_5 = [
            make_member(make_pokemon("lapras",   ["Water", "Ice"])),
            make_member(make_pokemon("machamp",  ["Fighting"])),
            make_member(make_pokemon("arcanine", ["Fire"])),
            make_member(make_pokemon("jolteon",  ["Electric"])),
            make_member(make_pokemon("venusaur", ["Grass", "Poison"])),
        ]
        # Psychic is weak to Bug, Ghost, Dark
        team_psychic = shared_5 + [make_member(make_pokemon("alakazam", ["Psychic"]))]
        # Normal is immune to Ghost, not weak to Bug/Dark
        team_normal  = shared_5 + [make_member(make_pokemon("snorlax",  ["Normal"]))]

        score_with_immunity = score_defensive_synergy(team_normal)
        score_with_weakness = score_defensive_synergy(team_psychic)
        assert score_with_immunity > score_with_weakness


class TestStatDistribution:
    def test_score_in_range(self, gen1_team):
        score = score_stat_distribution(gen1_team)
        assert 0.0 <= score <= 1.0

    def test_balanced_team_scores_higher(self, gen1_team):
        # Gen1 team has fast attackers (Alakazam 120 spd), walls (Snorlax), etc.
        mono_attackers = [
            make_member(make_pokemon(f"mon_{i}", ["Normal"], speed=120, attack=130, defense=50, hp=60))
            for i in range(6)
        ]
        gen1_score  = score_stat_distribution(gen1_team)
        mono_score  = score_stat_distribution(mono_attackers)
        assert gen1_score > mono_score

    def test_redundancy_penalty_applied(self):
        """6 identical sweepers should be penalized for redundancy."""
        sweepers = [
            make_member(make_pokemon(f"sweeper_{i}", ["Normal"], speed=120, attack=130, defense=50, hp=60))
            for i in range(6)
        ]
        score = score_stat_distribution(sweepers)
        assert score < 0.8, f"All-sweeper team should be penalized for redundancy, got {score}"


class TestRoleDiversity:
    def test_score_in_range(self, gen1_team):
        score = score_role_diversity(gen1_team)
        assert 0.0 <= score <= 1.0

    def test_trick_room_rewards_slow_pokemon(self):
        tr_team = [
            make_member(make_pokemon(f"slow_{i}", ["Normal"], speed=30, attack=130, defense=80, hp=100))
            for i in range(6)
        ]
        normal_team = [
            make_member(make_pokemon(f"fast_{i}", ["Normal"], speed=110, attack=120))
            for i in range(6)
        ]
        tr_score_tr_style   = score_role_diversity(tr_team, PlayStyle.TRICK_ROOM)
        tr_score_normal     = score_role_diversity(normal_team, PlayStyle.TRICK_ROOM)
        assert tr_score_tr_style > tr_score_normal

    def test_stall_rewards_walls(self):
        stall_team = [
            make_member(make_pokemon(f"wall_{i}", ["Steel"], defense=130, sp_def=120, hp=100, attack=50, speed=30))
            for i in range(6)
        ]
        ho_team = [
            make_member(make_pokemon(f"sweeper_{i}", ["Normal"], speed=130, attack=140, defense=40, hp=55))
            for i in range(6)
        ]
        stall_stall  = score_role_diversity(stall_team, PlayStyle.STALL)
        stall_ho     = score_role_diversity(ho_team,    PlayStyle.STALL)
        assert stall_stall > stall_ho


class TestRoleClassification:
    def test_fast_attacker_classified_as_sweeper(self):
        fast_attacker = make_pokemon("jolteon", ["Electric"], speed=130, attack=65, sp_atk=110, defense=60, hp=65)
        role = classify_role(fast_attacker)
        assert role in (PokemonRole.SPECIAL_SWEEPER, PokemonRole.PHYSICAL_SWEEPER, PokemonRole.MIXED)

    def test_bulky_classified_as_wall(self):
        wall = make_pokemon("steelix", ["Steel","Ground"], defense=200, sp_def=65, hp=75, attack=85, speed=30, sp_atk=55)
        role = classify_role(wall)
        assert role == PokemonRole.PHYSICAL_WALL

    def test_support_has_high_both_defenses(self):
        support = make_pokemon("blissey", ["Normal"], hp=255, defense=10, sp_def=135, sp_atk=75, attack=10, speed=55)
        role = classify_role(support)
        # High HP + high SpDef → special wall or support
        assert role in (PokemonRole.SPECIAL_WALL, PokemonRole.SUPPORT, PokemonRole.MIXED)


class TestCompositeScore:
    def test_returns_0_to_100(self, gen1_team):
        weights = ScoreWeights()
        composite, breakdown = score_team(gen1_team, weights)
        assert 0 <= composite <= 100
        for v in breakdown.values():
            assert 0 <= v <= 100

    def test_breakdown_has_all_components(self, gen1_team):
        weights = ScoreWeights()
        _, breakdown = score_team(gen1_team, weights)
        expected = {"offensive_coverage", "defensive_synergy", "stat_distribution", "role_diversity", "moveset_quality"}
        assert set(breakdown.keys()) == expected

    def test_weight_presets_differ(self, gen1_team):
        ho_weights   = ScoreWeights.for_play_style(PlayStyle.HYPER_OFFENSE)
        stall_weights = ScoreWeights.for_play_style(PlayStyle.STALL)
        ho_score, _    = score_team(gen1_team, ho_weights,    PlayStyle.HYPER_OFFENSE)
        stall_score, _ = score_team(gen1_team, stall_weights, PlayStyle.STALL)
        # Same team, different weights → different scores
        assert ho_score != stall_score
