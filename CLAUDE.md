# CLAUDE.md — Pokemon Team Optimizer

> **What is this file?**
> This is the product requirements document (PRD) and technical spec for the Pokemon Team Optimizer.
> It defines the problem, architecture, component breakdown, and implementation order.
> It also serves as context for AI-assisted development — a living spec that doubles as an engineering brief.

---

# Pokemon Team Optimizer

## Primary Goal

**This is a portfolio project targeting AI company hiring managers.**

The repo must demonstrate:
- Rigorous applied math (combinatorial optimization, ILP, evolutionary algorithms)
- Clean, well-documented code a senior engineer would respect
- A polished, interactive UI that is immediately impressive in a browser demo
- Real-world analogs articulated clearly (portfolio construction, fantasy sports drafting,
  resource allocation, workforce scheduling)

Lead with the engineering and math. Let Pokemon be the engaging application layer.

---

## Overview

Build a Pokemon team optimizer that uses constraint-based combinatorial optimization to find
optimal teams of 6 Pokemon. The tool maximizes type coverage, balances stats, minimizes shared
weaknesses, and respects a user-specified competitive play style.

---

## Core Problem

Given a pool of Pokemon (filtered by generation, game, and user constraints), select the optimal
team of 6 that optimizes across multiple objectives:

- **Type coverage** — maximize the number of the 18 types the team can hit super-effectively
- **Defensive synergy** — minimize overlapping type weaknesses across the team
- **Stat balance** — cover speed, bulk, and offense; avoid all glass cannons or all walls
- **Role coverage** — reflect the user's chosen play style archetype
- **Moveset quality** — include ideal competitive movesets per Pokemon, not just type data

This is a **multi-objective combinatorial optimization problem**. The search space is C(n, 6)
where n = number of Pokemon in the pool (800+ for the full dex), so brute force is infeasible
at scale.

---

## User-Facing Constraints & Inputs

### 1. Generation Filter (multi-select)

Users can select one or more generations to restrict the Pokemon pool:

| Generation | Games Included |
|-----------|----------------|
| Gen 1 | Red, Blue, Yellow |
| Gen 2 | Gold, Silver, Crystal |
| Gen 3 | Ruby, Sapphire, Emerald, FireRed, LeafGreen |
| Gen 4 | Diamond, Pearl, Platinum, HeartGold, SoulSilver |
| Gen 5 | Black, White, Black 2, White 2 |
| Gen 6 | X, Y, Omega Ruby, Alpha Sapphire |
| Gen 7 | Sun, Moon, Ultra Sun, Ultra Moon, Let's Go Pikachu, Let's Go Eevee |
| Gen 8 | Sword, Shield, Brilliant Diamond, Shining Pearl, Legends: Arceus |
| Gen 9 | Scarlet, Violet |

UI: Two levels of selection — first pick generation(s) via checkboxes, then optionally
drill down to specific games within a generation. Selecting a generation includes all its
games by default; deselecting a specific game removes only that game's exclusive Pokemon.

### 2. Availability Mode

Pokemon availability within a game is not binary — there are multiple tiers of obtainability.
The optimizer must model this explicitly and let the user choose their context.

**Availability tiers** (stored per Pokemon per game in the dataset):

| Tier | Code | Description | Examples |
|------|------|-------------|---------|
| Catchable | `WILD` | Obtainable in the wild or via in-game methods without trading | Pikachu in Viridian Forest |
| Tradeable | `TRADEABLE` | Requires trading with another player — version exclusives, trade evolutions | Ekans (Red only), Gengar (trade evo) |
| Event-only | `EVENT` | Required a real-world event, Mystery Gift, or promotional item no longer available | Deoxys (Aurora Ticket in FRLG), Mew (Gen 1 promo), Celebi, Jirachi |
| Transfer-only | `TRANSFER` | Exists in the game's dex but can only arrive via Bank/HOME from a prior game | Many older Pokemon in newer games |
| Unobtainable | `UNOBTAINABLE` | Not obtainable by any means in this game | Pokemon not in national dex |

**Availability Mode toggle** (shown in the UI with a `?` tooltip explaining each mode):

- **Competitive** *(default)* — Include all Pokemon that exist in the game's national dex,
  regardless of how they were obtained. Best for competitive team building where you have
  access to Pokemon Bank/HOME and a full collection. EVENT Pokemon are included but flagged.
- **Cartridge** — Include only `WILD` + `TRADEABLE` Pokemon. Suitable for planning a team
  you can actually build by trading with a friend. Trade evolutions are shown with a trade
  icon. EVENT and TRANSFER Pokemon are excluded.
- **Solo run** — Include only `WILD` Pokemon. No trades required. Best for planning a
  single-player playthrough team.

**Visual treatment in the UI:**
- EVENT Pokemon shown with a star badge and tooltip: "This Pokemon was only obtainable via
  a limited-time real-world event and is no longer available through normal means."
- TRADEABLE Pokemon shown with a trade arrow icon and tooltip explaining the requirement
- Availability mode affects the pool used by all solvers; it is not a post-filter

### 2. Anchor Pokemon (up to 5)

Users can lock in up to 5 Pokemon that must appear on the final team. The optimizer then
finds the single best 6th Pokemon to complete the team, or fills however many slots remain.

- Search by name with autocomplete, filtered to the selected generation/game pool
- Anchored Pokemon are displayed prominently in the team builder with a lock icon
- If an anchored team is already near-optimal, the optimizer explains why

### 3. Legendary Toggle

Checkbox: **Allow legendary Pokemon** (default: off for casual play, on for competitive).

Legendaries are flagged in the dataset from PokéAPI (`is_legendary`, `is_mythical` fields).

### 4. Play Style Selector

Users select their competitive play style. This adjusts the optimizer's objective weights
automatically. Each style has a tooltip (?) explaining what it means and example Pokemon.

| Play Style | Description | Optimizer Emphasis |
|-----------|-------------|-------------------|
| **Hyper Offense** | All-out attacking. Fast, frail Pokemon that overwhelm before the opponent can react. Sweep mid-to-late game. | Maximize Speed + offensive stats; reward setup sweepers; penalize low BST |
| **Balanced** | Mix of offense and defense. Adaptive, beginner-friendly, covers most threats. | Even distribution across offense/defense; reward pivots and role diversity |
| **Stall** | Outlast opponents through entry hazards, status conditions, and chip damage. Very slow-paced. | Maximize defensive stats and recovery; reward Stealth Rock/Spikes users; penalize low HP |
| **Weather** | Build around a weather condition (Rain, Sun, Sand, or Snow) to empower a core. | Reward weather setters + Swift Swim/Chlorophyll/Sand Rush/Slush Rush users; type synergy with weather |
| **Trick Room** | Invert Speed priority so slow, powerful Pokemon move first. Punishes fast teams. | Reward low Speed + high Attack/SpAtk; penalize fast frail Pokemon |
| **Setup Sweeper** | Accumulate stat boosts (Swords Dance, Nasty Plot, Dragon Dance) before sweeping. | Reward Pokemon with setup moves; favor late-game win conditions |

Sub-option for **Weather**: dropdown to pick Rain / Sun / Sand / Snow, which further filters
for Pokemon that synergize with that specific condition.

### 5. Additional Filters

- **No legendaries** — checkbox (above)
- **Minimum base stat total** — slider (e.g., filter out Pokemon below 400 BST)
- **Type requirements** — "Must include at least one [type]" dropdown (optional)

---

## Technical Architecture

### Data Layer

- **Source:** PokéAPI (https://pokeapi.co/) — pre-fetched and stored as static JSON
  to avoid runtime API dependency and ensure fast load times
- **What to store per Pokemon:**
  - Name, national dex number, sprite URL
  - Primary and secondary type
  - Base stats: HP, Atk, Def, SpAtk, SpDef, Speed, total BST
  - Abilities (including hidden ability)
  - Generation introduced, games available in
  - `is_legendary`, `is_mythical` flags
  - Egg groups (for future breeding feature)
  - **Ideal competitive moveset** — curated from Smogon or encoded as a data field:
    - 4 moves per set
    - Held item, ability, EV spread, nature
    - Multiple viable sets per Pokemon (offensive, defensive, support variants)
- **Type effectiveness matrix:** 18x18 float matrix (0, 0.25, 0.5, 1, 2, 4)
  encoding attacker → defender relationships
- **Preprocessing:**
  - Pre-compute offensive coverage vector per Pokemon (which types it hits SE)
  - Pre-compute defensive weakness vector per Pokemon (which types hit it SE)
  - Compute role classification per Pokemon (see Scoring Model below)

### Optimization Engine

Implement three solver approaches for comparison:

#### Solver 1: Integer Linear Programming (ILP)

Using **PuLP** or **Google OR-Tools**.

Binary decision variables: `x_i ∈ {0,1}` for each Pokemon `i` in the pool.

Constraints:
- Team size: `∑ x_i = 6`
- Anchor constraints: `x_i = 1` for each anchored Pokemon
- Legendary filter: `x_i = 0` for legendaries if toggle is off
- Generation filter: `x_i = 0` for Pokemon outside selected gen(s)

Objective: maximize weighted composite score (linearized — see Scoring Model).

This is the "clean" ORFE approach. Exact optimal solution for linear objectives.
Non-linear objectives (e.g., type coverage "at least one covers type X") require
auxiliary binary variables and Big-M constraints.

#### Solver 2: Genetic Algorithm (GA)

Custom implementation. Each chromosome is a team of 6 Pokemon indices.

- **Population size:** 200
- **Fitness function:** composite team score (same as ILP objective, no linearization needed)
- **Selection:** tournament selection (k=5)
- **Crossover:** uniform crossover on team slots; enforce no duplicates
- **Mutation:** random swap of one team member with a pool Pokemon (rate: 0.1)
- **Stopping criterion:** 500 generations or no improvement for 50 generations
- **Elitism:** top 10 chromosomes preserved each generation

GA handles non-linear objectives naturally. Visualizable: animate fitness over generations.

#### Solver 3: Greedy Heuristic with Local Search (baseline)

Fast O(n) baseline. Greedily add the Pokemon with the highest marginal score gain each step.
Then run local search: swap each team member with every pool Pokemon; keep improvements.
Used for benchmarking solve time and score quality vs. ILP and GA.

### Scoring Model

Composite score with tunable weights (adjusted automatically by play style, tunable manually):

```
score = w1 * offensive_coverage
      + w2 * defensive_synergy
      + w3 * stat_distribution
      + w4 * role_diversity
      + w5 * moveset_quality
```

**Offensive coverage score** (`offensive_coverage`):
- For each of 18 types: binary indicator — does any team member hit it super-effectively?
- Weighted sum: common types (Water, Fire, Ground) worth more than rare types
- Bonus for redundant coverage on the 5 most common attacking types

**Defensive synergy score** (`defensive_synergy`):
- For each type: count how many team members are weak to it
- Penalize if 3+ members share a weakness (exponential penalty)
- Reward for immunities that cover teammates (e.g., Ghost covering Normal-immune slot)

**Stat distribution score** (`stat_distribution`):
- Measure coverage across stat archetypes using k-means or threshold classification
- Reward teams that span: fast attacker (Speed > 100), physical wall (Def > 100, HP > 90),
  special wall (SpDef > 100), mixed attacker, support (high SpDef/HP, utility movepool)

**Role diversity score** (`role_diversity`):
- Classify each Pokemon into role based on stat ratios and moveset:
  - Physical Sweeper, Special Sweeper, Physical Wall, Special Wall, Support/Utility, Pivot
- Reward teams covering 4+ distinct roles
- Penalize teams with 3+ Pokemon in the same role

**Moveset quality score** (`moveset_quality`):
- For each team member's ideal moveset: score coverage, STAB moves, utility moves
- Bonus for complementary coverage between teammates (teammate A covers type gaps of teammate B)

---

## Frontend (Interactive Web UI)

### Design Language: Clean Professional + FRLG Nostalgia

The UI is a modern, professional dashboard that channels the aesthetic of Pokemon FireRed /
LeafGreen — the Gen 3 remakes that struck a balance between pixel-era charm and clean,
readable design. It should feel like something a designer at Game Freak might build if they
worked at a tech company today.

**Color palette:**

| Role | Color | Reference |
|------|-------|-----------|
| Primary accent | `#CC0000` (Pokedex Red) | FRLG Pokedex exterior |
| Dark panel background | `#1A1A2E` (deep navy) | Game Boy Advance screen border |
| Card background | `#FAFAF2` (warm cream) | FRLG text box / Pokedex interior screen |
| Secondary text | `#4A4A5A` | |
| Border / divider | `#E8E8D8` | |
| Success / super-effective | `#2ECC40` | |
| Warning / not-very-effective | `#FF851B` | |
| Danger / immune | `#FF4136` | |
| Type badge colors | Standard competitive type colors | Water=`#6890F0`, Fire=`#F08030`, etc. |

**Typography:**
- **Display / headings:** `Press Start 2P` (Google Fonts) — used sparingly for section headers
  and the app name only. Evokes the game without overwhelming the UI.
- **Body / UI:** `Inter` — clean, modern, legible at all sizes.
- **Monospace / stat numbers:** `JetBrains Mono` — used for BST values, score numbers, solver output.

**Design details that evoke FRLG without being kitsch:**
- Left sidebar styled like the Pokedex body: deep navy/dark background, red accent strip at top
- Pokemon cards use the warm cream background with a subtle `1px` red border on hover
- Type badges match the exact FRLG/Gen 3 type colors (not the newer Gen 6+ redesigns)
- Sprite images: Gen 3 / FRLG official sprites from PokeAPI (`front_default` from generation-iii)
- Section dividers use a subtle dotted pattern reminiscent of early Pokemon UI grid lines
- "Optimize" button styled like the FRLG "A button" — rounded, red, with a slight press animation

**Responsive behavior:**
- Desktop (≥1280px): Full 3-column layout — sidebar | team results | analysis charts
- Tablet (768–1280px): 2-column — sidebar | main content (charts stack below results)
- Mobile (<768px): Single column, tab-based navigation between Config / Results / Analysis

---

### Layout

Single-page React app. Three persistent columns (desktop):

```
┌─────────────────────────────────────────────────────────────┐
│  ◉ Pokemon Team Optimizer                      [dark/light] │
├──────────────┬──────────────────────┬───────────────────────┤
│              │                      │                       │
│  CONFIGURE   │   OPTIMIZED TEAM     │  ANALYSIS             │
│  [Pokedex    │                      │                       │
│   red panel] │  6 Pokemon cards     │  Type heatmap         │
│              │  with Gen 3 sprites  │  Stat radar           │
│  Gen picker  │                      │  Score breakdown      │
│  Play style  │  Score: 87/100  ?    │  Solver comparison    │
│  Anchors     │                      │  GA animation         │
│  Legendaries │  [Moveset details]   │                       │
│  Filters     │                      │  [Compare my team]    │
│              │  ILP │ GA │ Greedy   │                       │
│  [OPTIMIZE]  │  (tab selector)      │                       │
│              │                      │                       │
└──────────────┴──────────────────────┴───────────────────────┘
```

---

### Left Panel — Configuration (Pokedex-styled sidebar)

Styled as a dark navy panel with a red accent header bar. Sections separated by dotted dividers.

**Generation & Game Selector:**
- Row of 9 generation buttons (Gen I–IX), styled like FRLG menu tabs
- Multi-select; active gens highlighted in Pokedex red
- Click any gen to expand an accordion showing individual game checkboxes with game logos
- Paired games (Red/Blue, Black/Black 2) shown together with version-exclusive note

**Availability Mode:**
- Segmented control: `Competitive` | `Cartridge` | `Solo Run`
- `?` tooltip explaining each mode (see tooltip spec below)

**Play Style Selector:**
- 6 cards in a 2x3 grid, each with an icon and name
  - Hyper Offense: ⚡, Balanced: ⚖️, Stall: 🛡️, Weather: 🌧️, Trick Room: 🔮, Setup: 📈
- Selected card has red border + cream background; unselected are muted
- Each card has a `?` icon in the top-right corner
- Weather card expands to show Rain / Sun / Sand / Snow sub-picker on selection

**Anchor Pokemon (up to 5):**
- 5 empty slot tiles with dashed borders, labeled "Anchor 1" through "Anchor 5"
- Click any slot → search modal with autocomplete, filtered to current gen/game pool
- Filled slot shows: Gen 3 sprite + name + type badges + lock icon + ✕ to remove
- `?` tooltip: "These Pokemon are guaranteed to appear on your team. The optimizer fills the remaining slots."

**Additional Filters (collapsible):**
- Allow Legendaries toggle (default off)
- Min BST slider (300–600, default 0 = no filter)
- Required type dropdown ("Must include at least one [type]")
- Weight sliders for each scoring component (collapsed by default, labeled "Advanced: Tune Objective Weights")

**Optimize Button:**
- Full-width, Pokedex red, `Press Start 2P` font label: `OPTIMIZE`
- Disabled state when no generation is selected
- Loading state: animated Pokeball spinner + "Searching C(n,6) space..."

---

### Center Panel — Results

**Solver tab bar:** `ILP` | `Genetic Algorithm` | `Greedy` — switch between solver results.
Each tab shows solve time in small text: `ILP (0.4s)` | `GA (2.1s)` | `Greedy (0.02s)`.

**Team Score header:**
- Large number: `87 / 100` in `JetBrains Mono`
- `?` bubble next to it explaining the composite score formula
- Horizontal bar broken into 5 color segments (one per scoring component)

**6 Pokemon cards** (2 rows × 3 columns on desktop):
- Gen 3 / FRLG sprite (80×80px, pixelated rendering for authenticity)
- Name in `Inter` bold, National Dex number in muted text
- Type badges (2 max) using FRLG type colors
- BST bar (colored by stat archetype)
- Availability badge: star icon for EVENT, trade arrow for TRADEABLE
- Click to expand → **Moveset card** slides open below:
  - Move 1–4 with type badge and category (Physical/Special/Status)
  - Held item, ability, EV spread, nature
  - Source note: "Smogon OU recommended set" or "Curated"

---

### Right Panel — Analysis

**Type Coverage Heatmap:**
- Grid: rows = 6 Pokemon + a "Team" summary row; columns = 18 types
- Two toggle views: Offensive (which types does this Pokemon's moveset hit SE?) and Defensive
  (which types hit this Pokemon SE?)
- Cell colors: bright green = 2×, lime = 1× (neutral), orange = 0.5×, red = 0×/immune
- FRLG-style column headers using the type badge colors
- `?` tooltip on the heatmap header

**Stat Radar Chart:**
- 6-axis radar (HP, Atk, Def, SpAtk, SpDef, Speed)
- Each Pokemon as a semi-transparent colored polygon
- Legend below showing Pokemon name + color
- Toggle: show all 6 overlaid, or highlight one at a time

**Solver Comparison (tab):**
- Side-by-side comparison of ILP vs. GA team
- Columns: Team composition, Score, Solve time, Differences highlighted in red

**GA Generation Animation (tab):**
- Line chart: x = generation number, y = best fitness score
- Animates live while GA is running (via Server-Sent Events or WebSocket)
- Final frame shows the convergence point

**Compare My Team (bottom of right panel):**
- Collapsible section
- User searches and selects up to 6 Pokemon
- Their team's score + heatmap + radar overlaid against the optimizer's result

---

### Question Mark Tooltips (? bubbles)

Every `?` is a small circular button that opens a Popover (not a blocking modal).
Popovers are styled with the cream background + red header bar (FRLG text box aesthetic).

Mandatory tooltip targets:

| Element | Tooltip covers |
|---------|---------------|
| Team Score | Composite score formula, what each component contributes |
| Type Coverage heatmap | What super-effective means, why coverage matters |
| Defensive Synergy | What shared weaknesses cost you in battle |
| Stat Radar | What each stat does, what archetypes look like |
| Each Play Style card | Full archetype description, example Pokemon, when to use it |
| ILP solver tab | What integer linear programming is, why it finds the exact optimum |
| GA solver tab | What a genetic algorithm is, how fitness/crossover/mutation work |
| Anchor Pokemon | What anchoring does, constraint satisfaction explanation |
| Availability Mode | WILD vs TRADEABLE vs EVENT vs TRANSFER explanation |
| BST filter | What base stat total is, why it's a rough power proxy |
| Legendary toggle | What counts as legendary/mythical |
| STAB (in moveset card) | Same-type attack bonus explanation |

---

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Optimization backend | Python | PuLP or OR-Tools (ILP), custom GA |
| Frontend | React + TypeScript | |
| Data | Static JSON | Pre-fetched from PokéAPI; no runtime API calls needed |
| Visualization | Recharts + CSS Grid | Radar charts, heatmaps, GA animation |
| Deployment | GitHub Pages (frontend) | Pyodide for client-side Python, or FastAPI on Render/Fly.io |
| Styling | Tailwind CSS | Clean, modern look suitable for portfolio |

---

## Repo Structure

```
pokemon-team-optimizer/
├── README.md                      # Lead with optimization methodology
├── CLAUDE.md                      # This file — spec and engineering brief
├── data/
│   ├── fetch_pokeapi.py           # Script to pre-fetch and build static dataset
│   ├── pokemon.json               # Full Pokedex data (all gens)
│   ├── type_chart.json            # 18x18 effectiveness matrix
│   └── movesets.json              # Curated competitive movesets per Pokemon
├── optimizer/
│   ├── models.py                  # Data models (Pokemon, Team, MoveSet, etc.)
│   ├── scoring.py                 # Team scoring functions
│   ├── ilp_solver.py              # Integer linear programming solver
│   ├── ga_solver.py               # Genetic algorithm solver
│   ├── greedy_solver.py           # Greedy baseline with local search
│   └── constraints.py             # Constraint definitions and filter logic
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── App.tsx                # Root component, layout
│   │   ├── components/
│   │   │   ├── ConfigPanel/
│   │   │   │   ├── GenerationSelector.tsx
│   │   │   │   ├── PlayStyleSelector.tsx
│   │   │   │   ├── AnchorPicker.tsx
│   │   │   │   ├── LegendaryToggle.tsx
│   │   │   │   └── WeightSliders.tsx
│   │   │   ├── ResultsPanel/
│   │   │   │   ├── TeamDisplay.tsx
│   │   │   │   ├── MovesetCard.tsx
│   │   │   │   └── ScoreBreakdown.tsx
│   │   │   ├── AnalysisPanel/
│   │   │   │   ├── TypeHeatmap.tsx
│   │   │   │   ├── StatRadar.tsx
│   │   │   │   ├── SolverComparison.tsx
│   │   │   │   └── GAAnimation.tsx
│   │   │   └── shared/
│   │   │       ├── Tooltip.tsx    # Reusable ? bubble tooltip component
│   │   │       └── PokemonSearch.tsx
│   │   └── hooks/
│   │       ├── useOptimizer.ts
│   │       └── usePokedex.ts
├── tests/
│   ├── test_scoring.py
│   ├── test_solvers.py
│   └── test_constraints.py
└── notebooks/
    └── exploration.ipynb          # Data exploration and solver prototyping
```

---

## README Framing (important for portfolio)

Structure:

1. **What it does:** "Multi-objective combinatorial optimizer for Pokemon team composition"
2. **Why it's interesting:** C(1025, 6) ≈ 1.5 trillion possible teams; brute force impossible;
   exact ILP vs. evolutionary search vs. greedy heuristic
3. **Methodology:** ILP formulation with binary variables and linearized coverage constraints;
   GA crossover/mutation design; scoring model components
4. **Real-world analogs:** Portfolio construction, fantasy sports drafting, resource allocation,
   workforce scheduling — same mathematical structure
5. **Try it:** Link to live demo (GitHub Pages)
6. **Technical details:** Architecture, stack, solver comparison table (score, solve time)

---

## Definition of Done

- [ ] Static Pokemon dataset built from PokéAPI (all gens, with movesets)
- [ ] Type effectiveness matrix complete and tested
- [ ] ILP solver produces optimal teams for linear objectives
- [ ] GA solver produces competitive teams with live generation animation
- [ ] Greedy baseline benchmarked against both solvers
- [ ] Play style selector adjusts weights and affects team composition visibly
- [ ] Anchor Pokemon constraint works correctly in all solvers
- [ ] Legendary toggle filters correctly
- [ ] Generation + game multi-select filters correctly
- [ ] Type coverage heatmap and stat radar charts working
- [ ] Moveset cards show ideal competitive sets per Pokemon
- [ ] All ? tooltips implemented with clear, accurate explanations
- [ ] Comparison mode (user team vs. optimized team)
- [ ] Solver comparison panel shows ILP vs. GA results side-by-side
- [ ] Clean README with methodology-first framing
- [ ] Tests for scoring logic and solver correctness
- [ ] Deployed and publicly accessible

---

## Stretch Goals

- Smogon meta-game integration — weight Pokemon by competitive usage tier (OU, UU, RU, NU)
- Speed tier analysis — who outspeeds whom at +0, +1, +2 with Choice Scarf
- Team threat analysis — "your team loses to [threat X]" with suggested counter
- Export team to Pokemon Showdown format
- Dual-format support — Singles vs. VGC Doubles optimizer mode

---

## Open Questions / Areas to Refine

- [ ] **Moveset data source:** Smogon's data is community-maintained but not via a clean API.
  Options: scrape Smogon's PS! sets, use smogon npm package data, or curate manually for
  the top 150 Pokemon. Decide scope before building `movesets.json`.
- [ ] **ILP linearization:** The "at least one teammate covers type X" constraint requires
  auxiliary binary variables and Big-M. Need to write out the full LP formulation explicitly.
- [ ] **GA fitness normalization:** Each scoring component is on a different scale. Need to
  normalize before combining into a single fitness value.
- [x] **Availability tier data source — DECIDED (see below)**
- [ ] **Version exclusives at game level:** Gen selector currently operates at the game level,
  but version exclusives only matter when a specific single version is selected (e.g., Red only).
  If user selects both Red and Blue, all version exclusives become available via trade. The
  filter logic must detect single-version selection and switch to TRADEABLE mode for exclusives.
- [ ] **Deployment target:** Pyodide (client-side Python, no backend) vs. FastAPI on Render.
  Pyodide avoids infra but adds ~10MB bundle and slower startup. GA animation argues for
  streaming API responses. Lean toward FastAPI + SSE for GA animation.
- [ ] **Role classification thresholds:** Define exact stat ratio cutoffs for physical sweeper,
  special sweeper, wall, support, pivot. These need to be explicit, documented, and tunable.
- [ ] **Weather sub-mode UX:** When user selects Weather play style, show a secondary picker
  (Rain / Sun / Sand / Snow). Each choice should re-weight relevant abilities and types.

---

## Availability Tier Data: Approach

### Why this is hard

PokéAPI's `pokemon-game-indices` field tells us *which games* a Pokemon appears in, but treats
all appearances as equal. It does not distinguish between:
- A Pokemon you can catch in the wild on Route 3
- A Pokemon that requires trading with a friend (version exclusive or trade evolution)
- A Pokemon that required a real-world event ticket in 2004 that no longer exists
- A Pokemon that exists in the dex but can only arrive via Pokemon HOME from another game

This is genuinely a data engineering problem with no clean off-the-shelf solution. It is worth
calling out explicitly in the README as a non-trivial design challenge.

### Data Sources (layered approach)

We do not rely on a single source. Instead, we layer three sources in order of trust:

1. **PokéAPI** (base layer) — use `pokemon-game-indices` to establish which games a Pokemon
   exists in at all. Everything starts as `UNOBTAINABLE` until proven otherwise.

2. **veekun/pokedex** (location layer) — an open-source, community-maintained Pokemon database
   on GitHub (`github.com/veekun/pokedex`) with structured location data per game. This is the
   most comprehensive machine-readable source for WILD availability. Import from its SQLite
   database during the data build step.

3. **Hand-curated `event_pokemon.json`** (event layer) — a manually maintained file listing all
   EVENT-tier Pokemon. This is feasible because the set is small and well-documented: there are
   roughly 20–30 mythicals and special-distribution Pokemon (Mew, Celebi, Jirachi, Deoxys,
   Darkrai, Shaymin, Arceus, Victini, Keldeo, Genesect, Diancie, Hoopa, Volcanion, Magearna,
   Marshadow, Zeraora, Meltan, Melmetal, Zarude, etc.). Their event status is historical fact
   and does not change. Format:

   ```json
   {
     "mew": {
       "event_games": ["red", "blue", "yellow"],
       "note": "Gen 1 Nintendo Power/CES promotional event, 1996-1999. Not reproducible."
     },
     "deoxys": {
       "event_games": ["firered", "leafgreen"],
       "note": "Aurora Ticket via Mystery Gift. Event ended 2005.",
       "non_event_games": ["emerald", "oras"]
     }
   }
   ```

   Note that some Pokemon are EVENT in some games but WILD/obtainable in others (e.g., Deoxys
   in Emerald via Birth Island after the event). The curated file handles this per-game.

### Derivation Logic

The build script (`data/fetch_pokeapi.py`) derives the final availability tier per Pokemon per
game using this priority chain:

```
if pokemon not in game's game-indices:
    → UNOBTAINABLE

elif pokemon in event_pokemon.json for this game:
    → EVENT

elif pokemon in veekun location data for this game:
    if location requires trading (trade_flags in veekun):
        → TRADEABLE
    else:
        → WILD

elif pokemon exists in national dex but no location data:
    → TRANSFER  (present in dex, but no in-game obtainment route found)
```

### Scope and Rollout

We do not attempt to solve all 9 gens perfectly on day one. Phased approach:

| Phase | Scope | Notes |
|-------|-------|-------|
| **Phase 1** (launch) | Gen 1–3, all games | Best-documented; veekun data is complete; EVENT set small |
| **Phase 2** | Gen 4–5 | HeartGold/SoulSilver complex; Black 2/White 2 event history well-known |
| **Phase 3** | Gen 6–9 | Modern games; Pokemon HOME complicates TRANSFER tier |

For games not yet fully mapped, default to `COMPETITIVE` mode only with a UI notice:
"Availability data for this game is incomplete. Showing all Pokemon in the national dex."

### Version Exclusive Logic

When the user selects both Red AND Blue (or any paired versions), version exclusives become
`TRADEABLE` because a friend could provide them. The filter logic must detect paired-version
selection and upgrade version exclusives from their single-version `TRADEABLE` tier:

```
if len(selected_games_in_generation) >= 2 and games_are_paired(selected_games):
    version_exclusives → TRADEABLE (already were; no change to tier but UI note changes)
    # Tooltip changes from "Red version only — requires trade" to
    # "Available via trade between Red and Blue — you selected both"
```

If only a single version is selected, version exclusives for the other version are excluded
in Cartridge and Solo modes, and flagged in Competitive mode.

### What to Highlight in the README

The availability tier system is a legitimate data engineering contribution worth calling out:
- "No API provides this data in structured form — we built a derivation pipeline from three
  sources (PokéAPI, veekun, hand-curated event history)"
- "The EVENT tier required historical research into promotional campaigns spanning 1996–2024"
- "The layered trust model (PokéAPI base → veekun locations → curated events) mirrors
  real-world data pipeline design patterns"
