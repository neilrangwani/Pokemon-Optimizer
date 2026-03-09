import { useState, useCallback } from "react";
import type { OptimizeRequest, OptimizeResponse, TeamResult } from "../types";

export type OptimizerStatus = "idle" | "running" | "done" | "error";

export interface OptimizerState {
  status: OptimizerStatus;
  team: TeamResult | null;
  error: string | null;
  poolSize: number | null;
}

export function useOptimizer() {
  const [state, setState] = useState<OptimizerState>({
    status: "idle",
    team: null,
    error: null,
    poolSize: null,
  });

  const cancel = useCallback(() => {
    setState((s) => ({ ...s, status: "idle" }));
  }, []);

  const optimize = useCallback(async (request: OptimizeRequest) => {
    setState({ status: "running", team: null, error: null, poolSize: null });

    try {
      const API = import.meta.env.VITE_API_URL ?? "";
      const resp = await fetch(`${API}/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...request, solver: "ilp" }),
      });

      if (!resp.ok) {
        const err = await resp.text();
        setState({ status: "error", team: null, error: err, poolSize: null });
        return;
      }

      const data: OptimizeResponse = await resp.json();
      const team = data.results.ilp ?? null;

      if (team?.error) {
        setState({ status: "error", team: null, error: team.error, poolSize: data.pool_size });
        return;
      }

      setState({ status: "done", team, error: null, poolSize: data.pool_size });
    } catch (e) {
      setState({ status: "error", team: null, error: String(e), poolSize: null });
    }
  }, []);

  return { state, optimize, cancel };
}
