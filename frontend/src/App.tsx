/**
 * App.tsx — Root component. Three-column dashboard layout.
 *
 * Design: Clean professional + FRLG nostalgia.
 * Left:   Dark navy Pokédex-styled config sidebar (scrollable).
 * Center: ILP team result.
 * Right:  Analysis panel (radar chart, type coverage, ILP formulation).
 */

import { useState } from "react";
import type { OptimizeRequest } from "./types";
import { GenerationSelector } from "./components/ConfigPanel/GenerationSelector";
import { PlayStyleSelector } from "./components/ConfigPanel/PlayStyleSelector";
import { AnchorPicker } from "./components/ConfigPanel/AnchorPicker";
import { TeamDisplay } from "./components/ResultsPanel/TeamDisplay";
import { StatRadar } from "./components/AnalysisPanel/StatRadar";
import { TypeCoverage } from "./components/AnalysisPanel/TypeCoverage";
import { Tooltip } from "./components/shared/Tooltip";
import { useOptimizer } from "./hooks/useOptimizer";

const DEFAULT_REQUEST: OptimizeRequest = {
  generations: [1],
  games: [],
  availability_mode: "COMPETITIVE",
  play_style: "BALANCED",
  weather_condition: null,
  anchor_pokemon: [],
  allow_legendaries: false,
  min_bst: 0,
  required_types: [],
  weights: null,
  solver: "ilp",
};

export default function App() {
  const [request, setRequest] = useState<OptimizeRequest>(DEFAULT_REQUEST);
  const [selectedMember, setSelectedMember] = useState<string | null>(null);
  const { state, optimize, cancel } = useOptimizer();

  const updateRequest = (patch: Partial<OptimizeRequest>) =>
    setRequest((r) => ({ ...r, ...patch }));

  const handleOptimize = () => {
    setSelectedMember(null);
    optimize(request);
  };

  return (
    <div className="h-screen bg-[#0D0D1A] flex flex-col font-['Inter'] overflow-hidden">
      {/* Top nav */}
      <header className="bg-[#1A1A2E] border-b border-[#CC0000] px-6 py-3 flex items-center gap-3 flex-shrink-0">
        <span className="text-[#CC0000] text-lg">◉</span>
        <h1 className="text-xs font-['Press_Start_2P'] text-[#FAFAF2] tracking-wide">
          Pokemon Team Optimizer
        </h1>
        <span className="ml-auto flex items-center gap-4">
          <span className="text-[10px] text-[#9090B0] font-['JetBrains_Mono'] hidden sm:block">
            Multi-objective combinatorial optimizer · C(n,6) search space · ILP exact solver
          </span>
          <a
            href="https://github.com/neilrangwani/Pokemon-Optimizer"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-[#CC0000] hover:text-[#FF3333] font-['JetBrains_Mono'] transition-colors flex-shrink-0"
          >
            README →
          </a>
        </span>
      </header>

      {/* Main 3-column layout — each panel scrolls independently */}
      <div className="flex flex-1 overflow-hidden min-h-0">

        {/* LEFT: Config sidebar */}
        <aside className="w-64 bg-[#1A1A2E] border-r border-[#2A2A3E] flex flex-col flex-shrink-0 overflow-hidden">
          <div className="bg-[#CC0000] h-1 w-full flex-shrink-0" />
          <div className="flex-1 overflow-y-auto">
            <div className="p-4 space-y-5">
              {/* Generation + Games */}
              <GenerationSelector
                selectedGens={request.generations}
                selectedGames={request.games}
                onChange={(gens, games) => updateRequest({ generations: gens, games })}
              />

              <div className="border-t border-dotted border-[#3A3A5E]" />

              {/* Availability mode */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-[#FAFAF2] uppercase tracking-wider">
                    Availability
                  </span>
                  <Tooltip title="Availability Mode">
                    <p className="mb-1.5"><strong>Competitive</strong> — Full national dex. Best with Pokémon HOME.</p>
                    <p className="mb-1.5"><strong>Cartridge</strong> — Wild-catchable + tradeable only.</p>
                    <p><strong>Solo Run</strong> — Only Pokémon you can catch yourself in-game.</p>
                  </Tooltip>
                </div>
                <div className="flex rounded overflow-hidden border border-[#3A3A5E]">
                  {([
                    { mode: "COMPETITIVE", label: "Competitive" },
                    { mode: "CARTRIDGE",   label: "Cartridge"   },
                    { mode: "SOLO_RUN",    label: "Solo Run"    },
                  ] as const).map(({ mode, label }) => (
                    <button
                      key={mode}
                      onClick={() => updateRequest({ availability_mode: mode })}
                      className="flex-1 py-1.5 text-[10px] font-semibold transition-colors"
                      style={{
                        backgroundColor: request.availability_mode === mode ? "#CC0000" : "#2A2A3E",
                        color: request.availability_mode === mode ? "white" : "#9090B0",
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="border-t border-dotted border-[#3A3A5E]" />

              {/* Play Style */}
              <PlayStyleSelector
                selected={request.play_style}
                weather={request.weather_condition}
                onStyleChange={(style) => updateRequest({ play_style: style })}
                onWeatherChange={(weather) => updateRequest({ weather_condition: weather })}
              />

              <div className="border-t border-dotted border-[#3A3A5E]" />

              {/* Anchor Pokémon */}
              <AnchorPicker
                anchors={request.anchor_pokemon}
                onChange={(anchors) => updateRequest({ anchor_pokemon: anchors })}
              />

              <div className="border-t border-dotted border-[#3A3A5E]" />

              {/* Legendaries toggle */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-[#FAFAF2]">Legendaries</span>
                  <Tooltip title="Allow Legendaries">
                    Legendary and Mythical Pokémon (Mewtwo, Lugia, Arceus, etc.) are excluded
                    by default. Enable to include them in the optimization pool.
                  </Tooltip>
                </div>
                <button
                  onClick={() => updateRequest({ allow_legendaries: !request.allow_legendaries })}
                  className="w-9 h-5 rounded-full transition-colors relative flex-shrink-0"
                  style={{ backgroundColor: request.allow_legendaries ? "#CC0000" : "#3A3A5E" }}
                  aria-checked={request.allow_legendaries}
                  role="switch"
                >
                  <span
                    className="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform"
                    style={{ transform: request.allow_legendaries ? "translateX(16px)" : "translateX(2px)" }}
                  />
                </button>
              </div>

              {state.poolSize !== null && (
                <div className="text-[10px] text-[#9090B0] font-['JetBrains_Mono']">
                  Pool: <span className="text-[#FAFAF2]">{state.poolSize}</span> eligible Pokémon
                </div>
              )}
            </div>
          </div>

          {/* Optimize button — pinned at bottom */}
          <div className="p-4 border-t border-[#2A2A3E] flex-shrink-0">
            {state.status === "running" ? (
              <button
                onClick={cancel}
                className="w-full py-3 rounded text-xs font-['Press_Start_2P'] transition-colors"
                style={{ backgroundColor: "#3A3A5E", color: "#9090B0" }}
              >
                CANCEL
              </button>
            ) : (
              <button
                onClick={handleOptimize}
                disabled={request.generations.length === 0}
                className="w-full py-3 rounded text-xs font-['Press_Start_2P'] transition-all duration-150"
                style={{
                  backgroundColor: request.generations.length === 0 ? "#3A3A5E" : "#CC0000",
                  color: request.generations.length === 0 ? "#9090B0" : "white",
                  cursor: request.generations.length === 0 ? "not-allowed" : "pointer",
                  boxShadow: request.generations.length > 0 ? "0 4px 24px rgba(204,0,0,0.3)" : "none",
                }}
              >
                {state.status === "done" ? "RE-OPTIMIZE" : "OPTIMIZE"}
              </button>
            )}
            {state.status === "running" && (
              <p className="text-[9px] text-[#9090B0] text-center mt-2 font-['JetBrains_Mono'] animate-pulse">
                Solving ILP…
              </p>
            )}
          </div>
        </aside>

        {/* CENTER: Results panel */}
        <main className="flex-1 overflow-y-auto p-5 min-w-0">
          {state.status === "idle" && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="text-5xl">◉</div>
                <p className="text-[#9090B0] text-sm">
                  Configure constraints and hit{" "}
                  <span className="font-['Press_Start_2P'] text-[#CC0000] text-[10px]">OPTIMIZE</span>
                </p>
                <p className="text-[#4A4A5A] text-xs font-['JetBrains_Mono']">
                  ILP exact solver · C(n, 6) combinatorial search
                </p>
              </div>
            </div>
          )}

          {state.status === "running" && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="text-[#CC0000] text-xs font-['Press_Start_2P'] animate-pulse">
                  SOLVING…
                </div>
                <p className="text-[#9090B0] text-xs font-['JetBrains_Mono']">
                  CBC branch-and-bound · finding global optimum
                </p>
              </div>
            </div>
          )}

          {state.error && (
            <div className="bg-red-900/20 border border-red-700 rounded p-3 text-red-300 text-xs mb-4 font-['JetBrains_Mono']">
              {state.error}
            </div>
          )}

          {state.team && (
            <TeamDisplay
              members={state.team.members}
              score={state.team.score}
              breakdown={state.team.score_breakdown}
              solver={state.team.solver}
              solveTime={state.team.solve_time_seconds}
              selectedMember={selectedMember}
              onSelectMember={setSelectedMember}
            />
          )}
        </main>

        {/* RIGHT: Analysis panel */}
        <aside className="w-72 bg-[#1A1A2E] border-l border-[#2A2A3E] flex-shrink-0 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto p-4">
            <h2 className="text-[10px] font-['Press_Start_2P'] text-[#FAFAF2] mb-4">
              ANALYSIS
            </h2>

            {/* Radar chart */}
            {state.team && state.team.members.length > 0 && (
              <>
                <div className="mb-5">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-semibold text-[#FAFAF2]">Stat Radar</span>
                    <Tooltip title="Stat Radar Chart">
                      Overlays all 6 team members' base stats. Click a Pokémon card or a legend
                      entry to highlight that member. A well-rounded team fills multiple regions.
                    </Tooltip>
                  </div>
                  <div className="bg-[#0F0F20] rounded border border-[#3A3A5E] p-2">
                    <StatRadar
                      members={state.team.members}
                      selectedMember={selectedMember}
                      onSelectMember={setSelectedMember}
                    />
                  </div>
                </div>

                {/* Type coverage */}
                <div className="mb-5">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-semibold text-[#FAFAF2]">Type Coverage</span>
                    <Tooltip title="Type Coverage">
                      <p className="mb-1.5"><strong>Offensive:</strong> Types the team can hit super-effectively via STAB. Colored = covered.</p>
                      <p><strong>Vulnerabilities:</strong> Types where 3+ team members are weak — potential threats to address.</p>
                    </Tooltip>
                  </div>
                  <div className="bg-[#0F0F20] rounded border border-[#3A3A5E] p-3">
                    <TypeCoverage members={state.team.members} />
                  </div>
                </div>
              </>
            )}

            {/* ILP formulation */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-[#FAFAF2]">ILP Formulation</span>
                <Tooltip title="Integer Linear Programming">
                  <p className="mb-1.5">This optimizer solves an <strong>Integer Linear Program</strong> using the CBC branch-and-bound solver via PuLP.</p>
                  <p className="mb-1.5">ILP guarantees a <strong>globally optimal</strong> solution within the time limit — not a heuristic approximation.</p>
                  <p>Real-world analogs: portfolio construction, sports drafting, crew scheduling, supply chain allocation.</p>
                </Tooltip>
              </div>
              <div className="bg-[#0F0F20] rounded border border-[#3A3A5E] p-3 space-y-2 font-['JetBrains_Mono'] text-[10px]">
                <div>
                  <span className="text-[#CC0000] font-bold">Variables</span>
                  <div className="mt-1 text-[#9090B0] space-y-0.5 pl-2">
                    <div><span className="text-[#FAFAF2]">x_i</span> ∈ {"{"} 0, 1 {"}"} &nbsp; team membership</div>
                    <div><span className="text-[#FAFAF2]">y_t</span> ∈ {"{"} 0, 1 {"}"} &nbsp; type t covered</div>
                    <div><span className="text-[#FAFAF2]">z_r</span> ∈ {"{"} 0, 1 {"}"} &nbsp; role r filled</div>
                  </div>
                </div>
                <div>
                  <span className="text-[#CC0000] font-bold">Objective</span>
                  <div className="mt-1 text-[#9090B0] pl-2 space-y-0.5">
                    <div>max  Σ w_k · f_k(x, y, z)</div>
                    <div className="text-[9px]">offense + defense + stats + roles</div>
                  </div>
                </div>
                <div>
                  <span className="text-[#CC0000] font-bold">Constraints</span>
                  <div className="mt-1 text-[#9090B0] pl-2 space-y-0.5">
                    <div>Σ x_i = 6 &nbsp;&nbsp; (team size)</div>
                    <div>y_t ≤ Σ cov(i,t) · x_i</div>
                    <div>x_i = 1 for anchors</div>
                  </div>
                </div>
              </div>
            </div>

            {state.status === "idle" && (
              <p className="text-xs text-[#4A4A5A]">
                Run the optimizer to see the stat radar chart and team analysis.
              </p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
