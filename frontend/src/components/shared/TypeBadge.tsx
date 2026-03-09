import type { PokemonType } from "../../types";
import { TYPE_COLORS } from "../../types";

interface TypeBadgeProps {
  type: PokemonType;
  size?: "sm" | "md";
}

export function TypeBadge({ type, size = "md" }: TypeBadgeProps) {
  const bg = TYPE_COLORS[type] ?? "#A8A77A";
  const padding = size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs";

  return (
    <span
      className={`${padding} rounded font-semibold text-white inline-block font-['Inter']`}
      style={{ backgroundColor: bg }}
    >
      {type}
    </span>
  );
}
