/**
 * StatRadar.tsx — Recharts RadarChart overlaying all 6 team members' base stats.
 *
 * Axes: HP · Attack · Defense · Sp.Atk · Sp.Def · Speed
 * Selected member is highlighted; others are dimmed.
 */

import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import type { TeamMemberResult } from "../../types";

export const MEMBER_COLORS = [
  "#CC0000", "#6390F0", "#7AC74C", "#F7D02C", "#F95587", "#EE8130",
];

interface Props {
  members: TeamMemberResult[];
  selectedMember: string | null;
  onSelectMember: (name: string | null) => void;
}

export function StatRadar({ members, selectedMember, onSelectMember }: Props) {
  const axes = [
    { key: "hp",      label: "HP" },
    { key: "attack",  label: "Atk" },
    { key: "defense", label: "Def" },
    { key: "sp_atk",  label: "SpAtk" },
    { key: "sp_def",  label: "SpDef" },
    { key: "speed",   label: "Speed" },
  ] as const;

  const MAX: Record<string, number> = {
    hp: 255, attack: 190, defense: 230, sp_atk: 194, sp_def: 230, speed: 200,
  };

  const data = axes.map(({ key, label }) => {
    const entry: Record<string, number | string> = { stat: label };
    members.forEach((m, i) => {
      const raw = m.stats[key as keyof typeof m.stats] as number;
      entry[`m${i}`] = Math.round((raw / MAX[key]) * 100);
    });
    return entry;
  });

  return (
    <div>
      <ResponsiveContainer width="100%" height={200}>
        <RadarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
          <PolarGrid stroke="#3A3A5E" />
          <PolarAngleAxis
            dataKey="stat"
            tick={{ fill: "#9090B0", fontSize: 10, fontFamily: "JetBrains Mono" }}
          />
          {members.map((m, i) => {
            const isSelected = selectedMember === m.name;
            const isOther = selectedMember !== null && !isSelected;
            return (
              <Radar
                key={m.name}
                name={m.display_name}
                dataKey={`m${i}`}
                stroke={MEMBER_COLORS[i]}
                fill={MEMBER_COLORS[i]}
                fillOpacity={isOther ? 0.03 : isSelected ? 0.3 : 0.12}
                strokeWidth={isSelected ? 2.5 : 1.5}
                strokeOpacity={isOther ? 0.2 : 1}
              />
            );
          })}
        </RadarChart>
      </ResponsiveContainer>

      {/* Clickable legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1">
        {members.map((m, i) => {
          const isSelected = selectedMember === m.name;
          return (
            <button
              key={m.name}
              onClick={() => onSelectMember(isSelected ? null : m.name)}
              className="flex items-center gap-1 rounded px-1 transition-colors"
              style={{
                opacity: selectedMember && !isSelected ? 0.45 : 1,
                backgroundColor: isSelected ? MEMBER_COLORS[i] + "22" : "transparent",
              }}
            >
              <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: MEMBER_COLORS[i] }} />
              <span
                className="text-[9px] font-['JetBrains_Mono'] truncate max-w-[72px]"
                style={{ color: isSelected ? MEMBER_COLORS[i] : "#9090B0" }}
              >
                {m.display_name}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
