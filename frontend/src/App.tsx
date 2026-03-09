/**
 * App.tsx — Root component. Three-column dashboard layout.
 *
 * Design: Clean professional + FRLG nostalgia.
 * Left:   Dark navy Pokédex-styled config sidebar (scrollable).
 * Center: ILP team result.
 * Right:  Analysis panel (radar chart, type coverage, ILP formulation).
 */

import { useState, useEffect } from "react";
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
  games: ["Yellow"],
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

type MobileTab = "config" | "results" | "analysis";

export default function App() {
  const [request, setRequest] = useState<OptimizeRequest>(DEFAULT_REQUEST);
  // selectedMember — the ONE member whose detail pane is open (card/radar click)
  const [selectedMember, setSelectedMember] = useState<string | null>(null);
  // highlightedMembers — cards with a colored border (can be multiple, e.g. after clicking a type vulnerability)
  const [highlightedMembers, setHighlightedMembers] = useState<string[]>([]);
  // Mobile tab navigation
  const [activeTab, setActiveTab] = useState<MobileTab>("config");
  const [poolCandidates, setPoolCandidates] = useState<{ name: string; display_name: string }[]>([]);
  const { state, optimize, cancel } = useOptimizer();

  // Fetch eligible Pokémon names whenever generation/availability filters change,
  // so the anchor picker autocomplete always reflects the current constraints.
  const generationsKey = JSON.stringify(request.generations);
  const gamesKey = JSON.stringify(request.games);
  useEffect(() => {
    const API = import.meta.env.VITE_API_URL ?? "";
    fetch(`${API}/pokemon/pool`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        generations: request.generations,
        games: request.games,
        availability_mode: request.availability_mode,
        allow_legendaries: request.allow_legendaries,
        min_bst: request.min_bst,
      }),
    })
      .then((r) => r.ok ? r.json() : [])
      .then((data: { name: string; display_name: string }[]) => setPoolCandidates(data))
      .catch(() => {});
  }, [generationsKey, gamesKey, request.availability_mode, request.allow_legendaries, request.min_bst]);

  const updateRequest = (patch: Partial<OptimizeRequest>) =>
    setRequest((r) => ({ ...r, ...patch }));

  // Single-member selection: opens detail pane + highlights that one card
  const handleSelectMember = (name: string | null) => {
    setSelectedMember(name);
    setHighlightedMembers(name ? [name] : []);
  };

  // Multi-member highlight: highlights multiple cards, closes detail pane
  const handleHighlightMembers = (names: string[]) => {
    setSelectedMember(null);
    setHighlightedMembers(names);
  };

  const handleOptimize = () => {
    setSelectedMember(null);
    setHighlightedMembers([]);
    optimize(request);
  };

  // Auto-switch to results tab on mobile when optimization completes
  useEffect(() => {
    if (state.status === "done") setActiveTab("results");
  }, [state.status]);

  return (
    <div className="h-screen bg-[#0D0D1A] flex flex-col font-['Inter'] overflow-hidden">
      {/* Top nav */}
      <header className="bg-[#1A1A2E] border-b border-[#CC0000] px-6 py-3 flex items-center gap-3 flex-shrink-0">
        <span className="text-[#CC0000] text-lg">◉</span>
        <h1 className="text-xs font-['Press_Start_2P'] text-[#FAFAF2] tracking-wide">
          Pokémon Team Optimizer
        </h1>
        <span className="ml-auto flex items-center gap-4">
          <span className="text-[10px] text-[#9090B0] font-['JetBrains_Mono'] hidden sm:block">
            2.5B possible teams · exact optimal solution · &lt;3s
          </span>
          <a
            href="https://github.com/neilrangwani/Pokemon-Optimizer"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#CC0000] text-[10px] font-semibold text-[#CC0000] hover:bg-[#CC0000] hover:text-white transition-all flex-shrink-0 font-['JetBrains_Mono']"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            README
          </a>
        </span>
      </header>

      {/* Main layout — 3 columns on desktop, 2 on tablet, tab-based on mobile */}
      <div className="flex flex-1 overflow-hidden min-h-0">

        {/* LEFT: Config sidebar — full width on mobile (config tab), fixed w-64 on md+ */}
        <aside className={`bg-[#1A1A2E] border-r border-[#2A2A3E] flex-col flex-shrink-0 overflow-hidden md:flex md:w-64 ${activeTab === "config" ? "flex flex-1 w-full" : "hidden"}`}>
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
                candidates={poolCandidates}
                onChange={(anchors) => updateRequest({ anchor_pokemon: anchors })}
              />

              <div className="border-t border-dotted border-[#3A3A5E]" />

              {/* Legendaries toggle */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-[#FAFAF2] uppercase tracking-wider">
                    Legendaries
                  </span>
                  <Tooltip title="Allow Legendaries">
                    Legendary and Mythical Pokémon (Mewtwo, Lugia, Arceus, etc.) are excluded
                    by default. Enable to include them in the optimization pool.
                  </Tooltip>
                </div>
                <div className="flex rounded overflow-hidden border border-[#3A3A5E]">
                  {([
                    { value: false, label: "Exclude" },
                    { value: true,  label: "Allow"   },
                  ] as const).map(({ value, label }) => (
                    <button
                      key={label}
                      onClick={() => updateRequest({ allow_legendaries: value })}
                      className="flex-1 py-1.5 text-[10px] font-semibold transition-colors"
                      style={{
                        backgroundColor: request.allow_legendaries === value ? "#CC0000" : "#2A2A3E",
                        color: request.allow_legendaries === value ? "white" : "#9090B0",
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {poolCandidates.length > 0 && (
                <div className="text-[10px] text-[#9090B0] font-['JetBrains_Mono']">
                  Pool: <span className="text-[#FAFAF2]">{poolCandidates.length}</span> eligible Pokémon
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

        {/* RIGHT AREA: Results + Analysis — hidden on mobile when config tab active */}
        <div className={`flex-1 flex overflow-hidden min-w-0 flex-col xl:flex-row md:flex ${activeTab === "config" ? "hidden" : "flex"}`}>

        {/* CENTER: Results panel — hidden on mobile when analysis tab active */}
        <main className={`flex-1 overflow-y-auto p-5 min-w-0 xl:flex-1 ${activeTab === "analysis" ? "hidden xl:block" : ""}`}>
          {state.status === "idle" && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-4">
                <div className="text-5xl">◉</div>
                <p className="text-[#9090B0] text-sm">
                  Configure constraints and hit{" "}
                  <span className="font-['Press_Start_2P'] text-[#CC0000] text-[10px]">OPTIMIZE</span>
                </p>
                <a
                  href="https://github.com/neilrangwani/Pokemon-Optimizer"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded border border-[#3A3A5E] text-[11px] text-[#9090B0] hover:border-[#CC0000] hover:text-[#CC0000] transition-all font-['JetBrains_Mono'] mt-2"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
                  </svg>
                  How it works — README
                </a>
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
              highlightedMembers={highlightedMembers}
              onSelectMember={handleSelectMember}
            />
          )}
        </main>

        {/* RIGHT: Analysis panel — full width on mobile (analysis tab), stacks below results on tablet, fixed sidebar on desktop */}
        <aside className={`bg-[#1A1A2E] flex-col overflow-hidden xl:flex xl:w-72 xl:flex-shrink-0 xl:border-l xl:border-[#2A2A3E] md:border-t md:border-[#2A2A3E] md:flex md:flex-shrink-0 ${activeTab === "analysis" ? "flex flex-1" : "hidden"}`}>
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
                      onSelectMember={handleSelectMember}
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
                    <TypeCoverage
                      members={state.team.members}
                      selectedMember={selectedMember}
                      highlightedMembers={highlightedMembers}
                      onSelectMember={handleSelectMember}
                      onHighlightMembers={handleHighlightMembers}
                    />
                  </div>
                </div>
              </>
            )}

            {/* ILP formulation */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-[#FAFAF2]">ILP Formulation</span>
                <Tooltip title="Integer Linear Programming">
                  <p className="mb-1.5">This optimizer solves an <strong>Integer Linear Program (ILP)</strong>. ILP guarantees a <strong>globally optimal</strong> solution, not a heuristic approximation, to an optimization problem framed as a series of linear equations.</p>
                  <p className="mb-1.5">Real-world analogs: portfolio construction, sports drafting, crew scheduling, supply chain allocation.</p>
                  <p>For more information, <a href="https://github.com/neilrangwani/Pokemon-Optimizer/blob/main/README.md" target="_blank" rel="noopener noreferrer" style={{ color: "#CC0000" }} className="underline">click here</a>.</p>
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
        </div>{/* end right-area */}
      </div>{/* end main columns */}

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden flex-shrink-0 flex border-t border-[#2A2A3E] bg-[#1A1A2E]">
        {([
          { tab: "config",   label: "Configure", icon: "⚙" },
          { tab: "results",  label: "Team",      icon: "◉" },
          { tab: "analysis", label: "Analysis",  icon: "📊" },
        ] as const).map(({ tab, label, icon }) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="flex-1 py-3 flex flex-col items-center gap-1 transition-colors"
            style={{ color: activeTab === tab ? "#CC0000" : "#4A4A5A" }}
          >
            <span className="text-base leading-none">{icon}</span>
            <span className="text-[9px] font-['Press_Start_2P']">{label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
