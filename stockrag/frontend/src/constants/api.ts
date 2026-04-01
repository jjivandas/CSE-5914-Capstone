// src/constants/api.ts

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const API_TIMEOUT_MS = 10_000;   // TODO: Adjust as needed!

export const RECOMMENDATIONS_ENDPOINT = "/recommendations";

export const DEFAULT_TOP_K = 5;
