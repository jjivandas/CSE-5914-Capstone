// src/api/client.ts

import axios from "axios";
import type { AxiosInstance } from "axios";
import type {
  RecommendationRequest,
  RecommendationResponse,
} from "./types.ts";
import {
  API_BASE_URL,
  API_TIMEOUT_MS,
  RECOMMENDATIONS_ENDPOINT,
  DEFAULT_TOP_K,
  MOCK_RECOMMENDATIONS,
} from "../constants";

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: { "Content-Type": "application/json" },
});

function buildRecommendationPayload(
  request: RecommendationRequest,
): RecommendationRequest {
  return {
    ...request,
    topK: request.topK ?? DEFAULT_TOP_K,
  };
}

function buildMockFallback(): RecommendationResponse {
  return { ...MOCK_RECOMMENDATIONS };
}

async function postRecommendations(
  payload: RecommendationRequest,
): Promise<RecommendationResponse> {
  const response = await apiClient.post<RecommendationResponse>(
    RECOMMENDATIONS_ENDPOINT,
    payload,
  );
  return response.data;
}

export async function fetchRecommendations(
  request: RecommendationRequest,
): Promise<RecommendationResponse> {
  const payload = buildRecommendationPayload(request);
  try {
    return await postRecommendations(payload);
  } catch {
    return buildMockFallback();
  }
}
