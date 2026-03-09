/**
 * TeamDisplay.tsx — 6-Pokemon team grid with FRLG-style cards.
 * Clicking a card selects it; detail panel appears below the grid (no push-down).
 */

import type { TeamMemberResult, ScoreBreakdown, PokemonRole } from "../../types";
import { ROLE_LABELS } from "../../types";
import { TypeBadge } from "../shared/TypeBadge";
import { Tooltip } from "../shared/Tooltip";
import { MEMBER_COLORS } from "../AnalysisPanel/StatRadar";

interface Props {
  members: TeamMemberResult[];
  score: number;
  breakdown: ScoreBreakdown;
  solver: string;
  solveTime: number;
  selectedMember: string | null;
  onSelectMember: (name: string | null) => void;
}

const SCORE_COMPONENTS = [
  { key: "offensive_coverage", label: "Offense",  color: "#EE8130" },
  { key: "defensive_synergy",  label: "Defense",  color: "#6390F0" },
  { key: "stat_distribution",  label: "Stats",    color: "#7AC74C" },
  { key: "role_diversity",     label: "Roles",    color: "#F7D02C" },
  { key: "moveset_quality",    label: "Movesets", color: "#F95587" },
] as const;

export function TeamDisplay({ members, score, breakdown, solver, solveTime, selectedMember, onSelectMember }: Props) {
  const selectedPokemon = selectedMember ? members.find((m) => m.name === selectedMember) : null;

  return (
    <div className="space-y-4">
      {/* Score header */}
      <div className="flex items-center gap-3">
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-bold text-[#FAFAF2] font-['JetBrains_Mono']">
            {score.toFixed(1)}
          </span>
          <span className="text-lg text-[#9090B0] font-['JetBrains_Mono']">/100</span>
        </div>

        <Tooltip title="Team Score">
          <p className="mb-2">Composite score (0–100) — weighted sum of five components:</p>
          <ul className="space-y-1">
            {SCORE_COMPONENTS.map(({ key, label, color }) => (
              <li key={key} className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm inline-block flex-shrink-0" style={{ backgroundColor: color }} />
                <strong>{label}</strong>: {(breakdown[key] ?? 0).toFixed(1)} / 100
              </li>
            ))}
          </ul>
        </Tooltip>

        <span className="ml-auto text-xs text-[#9090B0] font-['JetBrains_Mono'] uppercase">
          {solver} · {solveTime.toFixed(3)}s
        </span>
      </div>

      {/* Score breakdown bar */}
      <div className="flex h-2 rounded overflow-hidden gap-px">
        {SCORE_COMPONENTS.map(({ key, color }) => {
          const val = breakdown[key] ?? 0;
          return (
            <div
              key={key}
              style={{ flex: val, backgroundColor: color }}
              title={`${key}: ${val.toFixed(1)}`}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {SCORE_COMPONENTS.map(({ key, label, color }) => (
          <div key={key} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: color }} />
            <span className="text-[10px] text-[#9090B0]">
              {label}: <span className="text-[#DADAE8]">{(breakdown[key] ?? 0).toFixed(1)}</span>
            </span>
          </div>
        ))}
      </div>

      {/* Pokemon grid — always stays 3-column */}
      <div className="grid grid-cols-3 gap-2">
        {members.map((member, i) => (
          <PokemonCard
            key={member.name}
            member={member}
            color={MEMBER_COLORS[i]}
            selected={selectedMember === member.name}
            onToggle={() => onSelectMember(selectedMember === member.name ? null : member.name)}
          />
        ))}
      </div>

      {/* Detail panel — appears below grid, never pushes cards */}
      {selectedPokemon && (
        <PokemonDetail member={selectedPokemon} />
      )}
    </div>
  );
}

// ── Collapsed card ────────────────────────────────────────────────────────────

function PokemonCard({
  member,
  color,
  selected,
  onToggle,
}: {
  member: TeamMemberResult;
  color: string;
  selected: boolean;
  onToggle: () => void;
}) {
  const roleInfo = member.role ? ROLE_LABELS[member.role as PokemonRole] : null;

  return (
    <div
      className="rounded border cursor-pointer transition-all duration-150 flex flex-col items-center p-2 gap-1"
      style={{
        borderColor: selected ? color : "#E8E8D8",
        borderWidth: selected ? 2 : 1,
        backgroundColor: selected ? color + "0D" : "#FAFAF2",
        boxShadow: selected ? `0 0 12px ${color}44` : "none",
      }}
      onClick={onToggle}
    >
      {member.sprite_url ? (
        <img
          src={member.sprite_url}
          alt={member.display_name}
          className="w-14 h-14 object-contain"
          style={{ imageRendering: "pixelated" }}
        />
      ) : (
        <div className="w-14 h-14 bg-[#E8E8D8] rounded flex items-center justify-center text-xs text-[#9090B0]">?</div>
      )}
      <div className="w-full text-center">
        <div className="text-[11px] font-bold text-[#1A1A2E] font-['Inter'] truncate">
          {member.display_name}
          {member.is_anchor && <span className="ml-1 text-[#CC0000] text-[9px]">🔒</span>}
        </div>
        <div className="flex gap-0.5 justify-center mt-0.5 flex-wrap">
          {member.types.map((t) => <TypeBadge key={t} type={t} size="sm" />)}
        </div>
        {roleInfo && (
          <div className="text-[9px] mt-1 font-semibold" style={{ color: roleInfo.color }}>
            {roleInfo.label}
          </div>
        )}
        <div className="mt-1 h-1 bg-[#E0E0E8] rounded overflow-hidden">
          <div
            className="h-full rounded"
            style={{ width: `${Math.min((member.bst / 720) * 100, 100)}%`, backgroundColor: color }}
          />
        </div>
        <div className="text-[9px] text-[#9090B0] mt-0.5 font-['JetBrains_Mono']">
          BST {member.bst}
        </div>
      </div>
    </div>
  );
}

// ── Detail panel (below the grid) ─────────────────────────────────────────────

function StatBar({ label, value, max = 255, color }: { label: string; value: number; max?: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-[#9090B0] w-10 text-right flex-shrink-0 text-[10px] font-['JetBrains_Mono']">{label}</span>
      <div className="flex-1 h-1.5 bg-[#E0E0E8] rounded overflow-hidden">
        <div className="h-full rounded transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-[#4A4A5A] font-bold w-7 text-right text-[10px] font-['JetBrains_Mono']">{value}</span>
    </div>
  );
}

function PokemonDetail({ member }: { member: TeamMemberResult }) {
  const roleInfo = member.role ? ROLE_LABELS[member.role as PokemonRole] : null;
  const color = "#CC0000"; // accent color for stat bars in detail panel

  return (
    <div
      className="rounded border p-4 bg-[#FAFAF2] transition-all"
      style={{ borderColor: "#CC0000" }}
    >
      <div className="flex gap-5">
        {/* Left: sprite + name + types + role */}
        <div className="flex flex-col items-center gap-1.5 flex-shrink-0 w-24">
          {member.sprite_url ? (
            <img
              src={member.sprite_url}
              alt={member.display_name}
              className="w-20 h-20 object-contain"
              style={{ imageRendering: "pixelated" }}
            />
          ) : (
            <div className="w-20 h-20 bg-[#E8E8D8] rounded flex items-center justify-center text-sm text-[#9090B0]">?</div>
          )}
          <span className="text-xs font-bold text-[#1A1A2E] font-['Inter'] text-center leading-tight">
            {member.display_name}
            {member.is_anchor && <span className="ml-1 text-[#CC0000]">🔒</span>}
            {(member.is_legendary || member.is_mythical) && <span className="ml-1">⭐</span>}
          </span>
          <div className="flex gap-1 flex-wrap justify-center">
            {member.types.map((t) => <TypeBadge key={t} type={t} size="sm" />)}
          </div>
          {roleInfo && (
            <span
              className="text-[9px] font-bold px-2 py-0.5 rounded-full text-center"
              style={{ backgroundColor: roleInfo.color + "22", color: roleInfo.color }}
            >
              {roleInfo.label}
            </span>
          )}
        </div>

        {/* Middle: stat bars */}
        <div className="flex-1 space-y-1.5 min-w-0">
          <p className="text-[9px] font-semibold text-[#9090B0] uppercase tracking-wider mb-2">
            Base Stats — BST {member.bst}
          </p>
          <StatBar label="HP"    value={member.stats.hp}      max={255} color={color} />
          <StatBar label="Atk"   value={member.stats.attack}  max={190} color={color} />
          <StatBar label="Def"   value={member.stats.defense} max={230} color={color} />
          <StatBar label="SpAtk" value={member.stats.sp_atk}  max={194} color={color} />
          <StatBar label="SpDef" value={member.stats.sp_def}  max={230} color={color} />
          <StatBar label="Speed" value={member.stats.speed}   max={200} color={color} />
        </div>

        {/* Right: abilities */}
        {member.abilities.length > 0 && (
          <div className="flex-shrink-0 min-w-[100px]">
            <p className="text-[9px] font-semibold text-[#9090B0] uppercase tracking-wider mb-2">
              Abilities
            </p>
            <div className="space-y-1">
              {member.abilities.map((ab) => (
                <div key={ab.name} className="text-[10px] font-['Inter']">
                  <span className="text-[#1A1A2E] font-semibold capitalize">
                    {ab.name.replace(/-/g, " ")}
                  </span>
                  {ab.is_hidden && (
                    <span className="ml-1 text-[9px] text-[#9090B0]">(hidden)</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
