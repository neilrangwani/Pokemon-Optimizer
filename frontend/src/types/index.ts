// Core data types mirroring the Python models

export type PokemonType =
  | "Normal" | "Fire" | "Water" | "Electric" | "Grass" | "Ice"
  | "Fighting" | "Poison" | "Ground" | "Flying" | "Psychic" | "Bug"
  | "Rock" | "Ghost" | "Dragon" | "Dark" | "Steel" | "Fairy";

export type PlayStyle =
  | "HYPER_OFFENSE" | "BALANCED" | "STALL"
  | "WEATHER" | "TRICK_ROOM" | "SETUP_SWEEPER";

export type WeatherCondition = "RAIN" | "SUN" | "SAND" | "SNOW";

export type AvailabilityMode = "COMPETITIVE" | "CARTRIDGE" | "SOLO_RUN";

export type SolverType = "ilp" | "genetic" | "greedy" | "all";

export type PokemonRole =
  | "PHYSICAL_SWEEPER" | "SPECIAL_SWEEPER" | "PHYSICAL_WALL"
  | "SPECIAL_WALL" | "SUPPORT" | "MIXED";

export const ROLE_LABELS: Record<PokemonRole, { label: string; color: string }> = {
  PHYSICAL_SWEEPER: { label: "Physical Sweeper", color: "#EE8130" },
  SPECIAL_SWEEPER:  { label: "Special Sweeper",  color: "#F95587" },
  PHYSICAL_WALL:    { label: "Physical Wall",    color: "#6390F0" },
  SPECIAL_WALL:     { label: "Special Wall",     color: "#96D9D6" },
  SUPPORT:          { label: "Support",          color: "#7AC74C" },
  MIXED:            { label: "Mixed",            color: "#A8A77A" },
};

export interface BaseStats {
  hp: number;
  attack: number;
  defense: number;
  sp_atk: number;
  sp_def: number;
  speed: number;
  total: number;
}

export interface PokemonAbility {
  name: string;
  is_hidden: boolean;
}

export interface PokemonData {
  id: number;
  name: string;
  display_name: string;
  generation: number;
  types: PokemonType[];
  bst: number;
  stats: BaseStats;
  sprite_url: string;
  is_legendary: boolean;
  is_mythical: boolean;
  is_anchor: boolean;
  abilities: PokemonAbility[];
}

export interface TeamMemberResult {
  name: string;
  display_name: string;
  types: PokemonType[];
  bst: number;
  stats: BaseStats;
  sprite_url: string;
  is_legendary: boolean;
  is_mythical: boolean;
  is_anchor: boolean;
  abilities: PokemonAbility[];
  role?: PokemonRole;
}

export interface ScoreBreakdown {
  offensive_coverage: number;
  defensive_synergy: number;
  stat_distribution: number;
  role_diversity: number;
  moveset_quality: number;
}

export interface TeamResult {
  score: number;
  score_breakdown: ScoreBreakdown;
  solver: string;
  solve_time_seconds: number;
  members: TeamMemberResult[];
  generation_history?: GenerationStat[];
  error?: string;
}

export interface GenerationStat {
  generation: number;
  best_fitness: number;
  mean_fitness: number;
  best_team_names?: string[];
  converged?: boolean;
}

export interface OptimizeResponse {
  pool_size: number;
  results: {
    ilp?: TeamResult;
    genetic?: TeamResult;
    greedy?: TeamResult;
  };
}

export interface ScoreWeights {
  offensive_coverage: number;
  defensive_synergy: number;
  stat_distribution: number;
  role_diversity: number;
  moveset_quality: number;
}

export interface OptimizeRequest {
  generations: number[];
  games: string[];
  availability_mode: AvailabilityMode;
  play_style: PlayStyle;
  weather_condition: WeatherCondition | null;
  anchor_pokemon: string[];
  allow_legendaries: boolean;
  min_bst: number;
  required_types: PokemonType[];
  weights: ScoreWeights | null;
  solver: SolverType;
}

// Type badge colors (FRLG/Gen 3 palette)
export const TYPE_COLORS: Record<PokemonType, string> = {
  Normal:   "#A8A77A",
  Fire:     "#EE8130",
  Water:    "#6390F0",
  Electric: "#F7D02C",
  Grass:    "#7AC74C",
  Ice:      "#96D9D6",
  Fighting: "#C22E28",
  Poison:   "#A33EA1",
  Ground:   "#E2BF65",
  Flying:   "#A98FF3",
  Psychic:  "#F95587",
  Bug:      "#A6B91A",
  Rock:     "#B6A136",
  Ghost:    "#735797",
  Dragon:   "#6F35FC",
  Dark:     "#705746",
  Steel:    "#B7B7CE",
  Fairy:    "#D685AD",
};

export const ALL_TYPES: PokemonType[] = [
  "Normal","Fire","Water","Electric","Grass","Ice",
  "Fighting","Poison","Ground","Flying","Psychic","Bug",
  "Rock","Ghost","Dragon","Dark","Steel","Fairy",
];

export const GENERATION_GAMES: Record<number, string[]> = {
  1: ["Red", "Blue", "Yellow"],
  2: ["Gold", "Silver", "Crystal"],
  3: ["Ruby", "Sapphire", "Emerald", "FireRed", "LeafGreen"],
  4: ["Diamond", "Pearl", "Platinum", "HeartGold", "SoulSilver"],
  5: ["Black", "White", "Black 2", "White 2"],
  6: ["X", "Y", "Omega Ruby", "Alpha Sapphire"],
  7: ["Sun", "Moon", "Ultra Sun", "Ultra Moon", "Let's Go Pikachu", "Let's Go Eevee"],
  8: ["Sword", "Shield", "Brilliant Diamond", "Shining Pearl", "Legends: Arceus"],
  9: ["Scarlet", "Violet"],
};

export const PLAY_STYLE_LABELS: Record<PlayStyle, { label: string; icon: string; description: string }> = {
  HYPER_OFFENSE: {
    label: "Hyper Offense",
    icon: "⚡",
    description: "All-out attacking. Fast, frail Pokemon that overwhelm before the opponent reacts.",
  },
  BALANCED: {
    label: "Balanced",
    icon: "⚖️",
    description: "Mix of offense and defense. Adaptive, beginner-friendly, covers most threats.",
  },
  STALL: {
    label: "Stall",
    icon: "🛡️",
    description: "Outlast opponents through entry hazards, status moves, and chip damage.",
  },
  WEATHER: {
    label: "Weather",
    icon: "🌧️",
    description: "Build around a weather condition to empower a core of synergistic Pokemon.",
  },
  TRICK_ROOM: {
    label: "Trick Room",
    icon: "🔮",
    description: "Invert Speed priority so slow, powerful Pokemon move first.",
  },
  SETUP_SWEEPER: {
    label: "Setup Sweeper",
    icon: "📈",
    description: "Accumulate stat boosts (Swords Dance, Dragon Dance) before sweeping.",
  },
};
