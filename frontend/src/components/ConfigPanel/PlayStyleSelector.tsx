/**
 * PlayStyleSelector.tsx — 6-card play style selector.
 * ? tooltips are positioned next to the label, not inside the button.
 */

import type { PlayStyle, WeatherCondition } from "../../types";
import { PLAY_STYLE_LABELS } from "../../types";
import { Tooltip } from "../shared/Tooltip";

const PLAY_STYLE_TOOLTIPS: Record<PlayStyle, React.ReactNode> = {
  HYPER_OFFENSE: "Teams of fast, frail attackers that aim to KO before taking damage. Optimizer boosts weight on Speed and offensive stats.",
  BALANCED: "A mix of offensive and defensive Pokémon that can adapt mid-battle. Weights distributed evenly — good starting point.",
  STALL: "Win by outlasting the opponent using entry hazards, status moves, and recovery. Optimizer emphasizes defensive stats and HP.",
  WEATHER: "Build around a weather setter (Drizzle, Drought, Sand Stream, Snow Warning). Pick your sub-type below.",
  TRICK_ROOM: "Trick Room reverses Speed priority for 5 turns — the slowest Pokémon move first. Optimizer rewards low Speed + high offensive stats.",
  SETUP_SWEEPER: "Accumulate stat boosts (Swords Dance, Nasty Plot, Dragon Dance) then sweep. Optimizer rewards setup-move users and pivot support.",
};

const WEATHER_OPTIONS: { label: string; value: WeatherCondition; icon: string }[] = [
  { label: "Rain",  value: "RAIN",  icon: "🌧️" },
  { label: "Sun",   value: "SUN",   icon: "☀️" },
  { label: "Sand",  value: "SAND",  icon: "🏜️" },
  { label: "Snow",  value: "SNOW",  icon: "❄️" },
];

interface Props {
  selected: PlayStyle;
  weather: WeatherCondition | null;
  onStyleChange: (style: PlayStyle) => void;
  onWeatherChange: (weather: WeatherCondition) => void;
}

export function PlayStyleSelector({ selected, weather, onStyleChange, onWeatherChange }: Props) {
  const styles = Object.keys(PLAY_STYLE_LABELS) as PlayStyle[];

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs font-semibold text-[#FAFAF2] uppercase tracking-wider">
          Play Style
        </span>
        <Tooltip title="Play Style">
          Determines how the optimizer weights team qualities. Each style shifts the
          balance between offense, defense, stat distribution, and role diversity.
        </Tooltip>
      </div>

      <div className="grid grid-cols-1 gap-1">
        {styles.map((style) => {
          const { label, icon } = PLAY_STYLE_LABELS[style];
          const active = selected === style;

          return (
            <button
              key={style}
              onClick={() => onStyleChange(style)}
              className="w-full p-2 rounded text-left transition-all duration-150 border font-['Inter'] flex items-center justify-between gap-1"
              style={{
                backgroundColor: active ? "#CC0000" : "#2A2A3E",
                borderColor: active ? "#CC0000" : "#3A3A5E",
                color: active ? "white" : "#9090B0",
              }}
            >
              <span className="flex items-center gap-1.5 min-w-0">
                <span className="text-sm leading-none flex-shrink-0">{icon}</span>
                <span className="text-[11px] font-semibold leading-tight truncate">{label}</span>
              </span>
              <Tooltip title={label}>
                {PLAY_STYLE_TOOLTIPS[style]}
              </Tooltip>
            </button>
          );
        })}
      </div>

      {selected === "WEATHER" && (
        <div className="p-2 bg-[#0F0F20] rounded border border-[#3A3A5E]">
          <p className="text-[10px] text-[#9090B0] mb-1.5">Weather condition:</p>
          <div className="grid grid-cols-2 gap-1">
            {WEATHER_OPTIONS.map(({ label, value, icon }) => (
              <button
                key={value}
                onClick={() => onWeatherChange(value)}
                className="py-1.5 px-2 rounded text-[10px] font-semibold transition-all border font-['Inter'] flex items-center gap-1"
                style={{
                  backgroundColor: weather === value ? "#CC0000" : "#2A2A3E",
                  borderColor: weather === value ? "#CC0000" : "#3A3A5E",
                  color: weather === value ? "white" : "#9090B0",
                }}
              >
                {icon} {label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
