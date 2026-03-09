"""
optimizer/models.py — Core data models for the Pokemon Team Optimizer.

All data crossing module boundaries uses these Pydantic models.
No raw dicts. No implicit coercions.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class PokemonType(str, Enum):
    Normal   = "Normal"
    Fire     = "Fire"
    Water    = "Water"
    Electric = "Electric"
    Grass    = "Grass"
    Ice      = "Ice"
    Fighting = "Fighting"
    Poison   = "Poison"
    Ground   = "Ground"
    Flying   = "Flying"
    Psychic  = "Psychic"
    Bug      = "Bug"
    Rock     = "Rock"
    Ghost    = "Ghost"
    Dragon   = "Dragon"
    Dark     = "Dark"
    Steel    = "Steel"
    Fairy    = "Fairy"

    @classmethod
    def all(cls) -> list["PokemonType"]:
        return list(cls)


class AvailabilityTier(str, Enum):
    WILD          = "WILD"          # Catchable in the wild / in-game without trading
    TRADEABLE     = "TRADEABLE"     # Requires trading with another player
    EVENT         = "EVENT"         # Required a real-world event (no longer available)
    TRANSFER      = "TRANSFER"      # Only via Bank/HOME from a prior game
    UNOBTAINABLE  = "UNOBTAINABLE"  # Not obtainable by any means in this game


class AvailabilityMode(str, Enum):
    COMPETITIVE = "COMPETITIVE"  # All Pokemon in the national dex
    CARTRIDGE   = "CARTRIDGE"   # WILD + TRADEABLE only
    SOLO_RUN    = "SOLO_RUN"    # WILD only


class PlayStyle(str, Enum):
    HYPER_OFFENSE  = "HYPER_OFFENSE"
    BALANCED       = "BALANCED"
    STALL          = "STALL"
    WEATHER        = "WEATHER"
    TRICK_ROOM     = "TRICK_ROOM"
    SETUP_SWEEPER  = "SETUP_SWEEPER"


class WeatherCondition(str, Enum):
    RAIN = "RAIN"
    SUN  = "SUN"
    SAND = "SAND"
    SNOW = "SNOW"


class PokemonRole(str, Enum):
    PHYSICAL_SWEEPER  = "PHYSICAL_SWEEPER"
    SPECIAL_SWEEPER   = "SPECIAL_SWEEPER"
    PHYSICAL_WALL     = "PHYSICAL_WALL"
    SPECIAL_WALL      = "SPECIAL_WALL"
    SUPPORT           = "SUPPORT"
    PIVOT             = "PIVOT"
    MIXED             = "MIXED"


class MoveCategory(str, Enum):
    PHYSICAL = "Physical"
    SPECIAL  = "Special"
    STATUS   = "Status"


# ---------------------------------------------------------------------------
# Pokemon data (loaded from pokemon.json)
# ---------------------------------------------------------------------------

class BaseStats(BaseModel):
    hp:     int = Field(ge=1, le=255)
    attack: int = Field(ge=1, le=255)
    defense: int = Field(ge=1, le=255)
    sp_atk: int = Field(ge=1, le=255)
    sp_def: int = Field(ge=1, le=255)
    speed:  int = Field(ge=1, le=255)
    total:  int = Field(ge=6, le=1530)


class Ability(BaseModel):
    name: str
    is_hidden: bool = False


class Pokemon(BaseModel):
    id: int                                  # National Dex number
    name: str                                # PokéAPI slug (e.g. "charizard")
    display_name: str                        # Human-readable (e.g. "Charizard")
    generation: int = Field(ge=1, le=9)
    types: list[PokemonType] = Field(min_length=1, max_length=2)
    stats: BaseStats
    abilities: list[Ability]
    sprite_url: str = ""
    is_legendary: bool = False
    is_mythical: bool = False
    # availability[game_slug] = AvailabilityTier
    availability: dict[str, AvailabilityTier] = Field(default_factory=dict)

    @property
    def primary_type(self) -> PokemonType:
        return self.types[0]

    @property
    def secondary_type(self) -> PokemonType | None:
        return self.types[1] if len(self.types) > 1 else None

    @property
    def bst(self) -> int:
        return self.stats.total

    @model_validator(mode="after")
    def validate_bst(self) -> "Pokemon":
        expected = (
            self.stats.hp + self.stats.attack + self.stats.defense
            + self.stats.sp_atk + self.stats.sp_def + self.stats.speed
        )
        if self.stats.total != expected:
            self.stats.total = expected
        return self


# ---------------------------------------------------------------------------
# Movesets
# ---------------------------------------------------------------------------

class Move(BaseModel):
    name: str
    type: PokemonType
    category: MoveCategory
    power: int | None = None     # None for status moves
    accuracy: int | None = None  # None for moves that never miss


class MoveSet(BaseModel):
    """A single competitive set for one Pokemon."""
    pokemon_name: str
    set_name: str                         # e.g. "Choice Specs", "Swords Dance Sweeper"
    moves: list[Move] = Field(min_length=1, max_length=4)
    held_item: str | None = None
    ability: str | None = None
    nature: str | None = None
    ev_spread: dict[str, int] = Field(default_factory=dict)  # {"speed": 252, "sp_atk": 252, "hp": 4}
    source: str = "curated"               # "smogon-ou", "smogon-uu", "curated", etc.


# ---------------------------------------------------------------------------
# Computed coverage profiles (pre-processed from type chart)
# ---------------------------------------------------------------------------

class CoverageProfile(BaseModel):
    """Pre-computed offensive and defensive coverage for a Pokemon."""
    pokemon_name: str
    # offensive_coverage[type] = max effectiveness this Pokemon can hit that type
    # (considering all moves in its ideal moveset, not just STABs)
    offensive_coverage: dict[str, float] = Field(default_factory=dict)
    # defensive_weaknesses[type] = effectiveness of that type attacking this Pokemon
    defensive_weaknesses: dict[str, float] = Field(default_factory=dict)
    # Derived role classification
    role: PokemonRole = PokemonRole.MIXED


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------

class TeamMember(BaseModel):
    pokemon: Pokemon
    moveset: MoveSet | None = None
    coverage: CoverageProfile | None = None
    is_anchor: bool = False       # Was this Pokemon locked in by the user?


class Team(BaseModel):
    members: list[TeamMember] = Field(min_length=1, max_length=6)
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    solver: str = ""              # "ilp", "genetic", "greedy"
    solve_time_seconds: float = 0.0

    @property
    def pokemon_names(self) -> list[str]:
        return [m.pokemon.name for m in self.members]


# ---------------------------------------------------------------------------
# Optimizer request / response
# ---------------------------------------------------------------------------

class ScoreWeights(BaseModel):
    """Tunable weights for each scoring component. Must sum to ~1.0."""
    offensive_coverage: float = Field(default=0.30, ge=0.0, le=1.0)
    defensive_synergy:  float = Field(default=0.25, ge=0.0, le=1.0)
    stat_distribution:  float = Field(default=0.20, ge=0.0, le=1.0)
    role_diversity:     float = Field(default=0.15, ge=0.0, le=1.0)
    moveset_quality:    float = Field(default=0.10, ge=0.0, le=1.0)

    @classmethod
    def for_play_style(cls, style: PlayStyle, weather: WeatherCondition | None = None) -> "ScoreWeights":
        """Return preset weights tuned for each competitive play style."""
        presets: dict[PlayStyle, dict] = {
            PlayStyle.HYPER_OFFENSE: dict(
                offensive_coverage=0.40, defensive_synergy=0.10,
                stat_distribution=0.25, role_diversity=0.15, moveset_quality=0.10,
            ),
            PlayStyle.BALANCED: dict(
                offensive_coverage=0.25, defensive_synergy=0.25,
                stat_distribution=0.20, role_diversity=0.20, moveset_quality=0.10,
            ),
            PlayStyle.STALL: dict(
                offensive_coverage=0.10, defensive_synergy=0.40,
                stat_distribution=0.25, role_diversity=0.15, moveset_quality=0.10,
            ),
            PlayStyle.WEATHER: dict(
                offensive_coverage=0.35, defensive_synergy=0.20,
                stat_distribution=0.15, role_diversity=0.20, moveset_quality=0.10,
            ),
            PlayStyle.TRICK_ROOM: dict(
                offensive_coverage=0.30, defensive_synergy=0.20,
                stat_distribution=0.25, role_diversity=0.15, moveset_quality=0.10,
            ),
            PlayStyle.SETUP_SWEEPER: dict(
                offensive_coverage=0.35, defensive_synergy=0.15,
                stat_distribution=0.20, role_diversity=0.20, moveset_quality=0.10,
            ),
        }
        return cls(**presets.get(style, {}))


class OptimizeRequest(BaseModel):
    """Full specification of a team optimization request from the frontend."""
    generations: list[int] = Field(default_factory=lambda: list(range(1, 10)))
    games: list[str] = Field(default_factory=list)  # empty = all games in selected gens
    availability_mode: AvailabilityMode = AvailabilityMode.COMPETITIVE
    play_style: PlayStyle = PlayStyle.BALANCED
    weather_condition: WeatherCondition | None = None  # only relevant if WEATHER play style
    anchor_pokemon: list[str] = Field(default_factory=list, max_length=5)  # pokemon name slugs
    allow_legendaries: bool = False
    min_bst: int = Field(default=0, ge=0, le=800)
    required_types: list[PokemonType] = Field(default_factory=list)
    weights: ScoreWeights | None = None   # None = use play_style defaults
    solver: Literal["ilp", "genetic", "greedy", "all"] = "ilp"

    @model_validator(mode="after")
    def set_default_weights(self) -> "OptimizeRequest":
        if self.weights is None:
            self.weights = ScoreWeights.for_play_style(self.play_style, self.weather_condition)
        return self


class OptimizeResponse(BaseModel):
    request: OptimizeRequest
    teams: dict[str, Team]        # solver name → best team found
    pool_size: int                 # number of eligible Pokemon after filtering
