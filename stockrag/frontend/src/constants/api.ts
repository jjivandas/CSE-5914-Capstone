// src/constants/api.ts

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const API_TIMEOUT_MS = 60_000;   // Pipeline needs 15-30s for 3 LLM calls

export const RECOMMENDATIONS_ENDPOINT = "/api/recommendations";

export const DEFAULT_TOP_K = 5;
