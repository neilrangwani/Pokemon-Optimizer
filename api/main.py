"""
api/main.py — FastAPI server for the Pokemon Team Optimizer.

Endpoints
---------
POST /optimize        — Run ILP and return the optimal team.
POST /pokemon/pool    — Return the filtered eligible pool for given constraints.
GET  /health          — Health check.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from optimizer import ilp_solver
from optimizer.constraints import build_eligible_pool, load_all_pokemon
from optimizer.scoring import classify_role
from optimizer.models import (
    OptimizeRequest,
    Pokemon,
    ScoreWeights,
    Team,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load Pokemon data on startup so first request is fast
    try:
        load_all_pokemon()
    except FileNotFoundError:
        print(
            "[warn] pokemon.json not found. Run: uv run python data/fetch_pokeapi.py\n"
            "       Optimizer endpoints will fail until data is built."
        )
    yield


app = FastAPI(
    title="Pokemon Team Optimizer API",
    description="Multi-objective combinatorial optimizer for Pokemon team composition.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Pokemon pool endpoint
# ---------------------------------------------------------------------------

class PoolRequest(BaseModel):
    generations: list[int] = list(range(1, 10))
    games: list[str] = []
    availability_mode: str = "COMPETITIVE"
    allow_legendaries: bool = False
    min_bst: int = 0


@app.post("/pokemon/pool", response_model=list[dict])
async def get_pool(req: PoolRequest):
    """Return the filtered Pokemon pool for the given constraints (no optimization)."""
    from optimizer.models import AvailabilityMode

    opt_req = OptimizeRequest(
        generations=req.generations,
        games=req.games,
        availability_mode=AvailabilityMode(req.availability_mode),
        allow_legendaries=req.allow_legendaries,
        min_bst=req.min_bst,
    )
    pool = build_eligible_pool(opt_req)
    return [
        {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "generation": p.generation,
            "types": [t.value for t in p.types],
            "bst": p.bst,
            "stats": p.stats.model_dump(),
            "sprite_url": p.sprite_url,
            "is_legendary": p.is_legendary,
            "is_mythical": p.is_mythical,
        }
        for p in pool
    ]


# ---------------------------------------------------------------------------
# ILP optimization
# ---------------------------------------------------------------------------

@app.post("/optimize", response_model=dict)
async def optimize(request: OptimizeRequest):
    """Run ILP optimization and return the optimal team."""
    pool = build_eligible_pool(request)

    try:
        team, _ = await asyncio.to_thread(ilp_solver.solve, request)
        result = _team_to_dict(team)
    except Exception as e:
        result = {"error": str(e)}

    return {
        "pool_size": len(pool),
        "results": {"ilp": result},
    }


# ---------------------------------------------------------------------------
# Score a user-provided team (for comparison mode)
# ---------------------------------------------------------------------------

class ScoreRequest(BaseModel):
    pokemon_names: list[str]
    play_style: str = "BALANCED"
    weights: dict[str, float] | None = None


@app.post("/score")
async def score_team_endpoint(req: ScoreRequest):
    """Score an arbitrary team provided by the user. Used for comparison mode."""
    from optimizer.models import PlayStyle
    from optimizer.scoring import score_team
    from optimizer.models import TeamMember

    all_pokemon = {p.name: p for p in load_all_pokemon()}
    members = []
    missing = []
    for name in req.pokemon_names:
        if name in all_pokemon:
            members.append(TeamMember(pokemon=all_pokemon[name]))
        else:
            missing.append(name)

    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown Pokemon: {missing}")
    if len(members) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 Pokemon per team.")

    try:
        play_style = PlayStyle(req.play_style)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid play_style: {req.play_style}")

    weights = ScoreWeights.for_play_style(play_style)
    if req.weights:
        weights = ScoreWeights(**req.weights)

    composite, breakdown = score_team(members, weights, play_style)
    return {
        "score": composite,
        "breakdown": breakdown,
        "team": [
            {
                "name": m.pokemon.name,
                "display_name": m.pokemon.display_name,
                "types": [t.value for t in m.pokemon.types],
                "bst": m.pokemon.bst,
                "sprite_url": m.pokemon.sprite_url,
            }
            for m in members
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _team_to_dict(team: Team) -> dict:
    return {
        "score": team.score,
        "score_breakdown": team.score_breakdown,
        "solver": team.solver,
        "solve_time_seconds": team.solve_time_seconds,
        "members": [
            {
                "name": m.pokemon.name,
                "display_name": m.pokemon.display_name,
                "types": [t.value for t in m.pokemon.types],
                "bst": m.pokemon.bst,
                "stats": m.pokemon.stats.model_dump(),
                "sprite_url": m.pokemon.sprite_url,
                "is_legendary": m.pokemon.is_legendary,
                "is_mythical": m.pokemon.is_mythical,
                "is_anchor": m.is_anchor,
                "abilities": [{"name": a.name, "is_hidden": a.is_hidden} for a in m.pokemon.abilities],
                "role": classify_role(m.pokemon).value,
            }
            for m in team.members
        ],
    }


# ---------------------------------------------------------------------------
# Static files — serve the built React frontend (production / Vercel)
# Must be mounted LAST so API routes take priority.
# ---------------------------------------------------------------------------

_static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
