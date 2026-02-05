// src/api/types.ts

export type Role = "user" | "assistant";

//TODO: Adjust as API Contract changes
export interface StockProfile {
  companyName: string;
  ticker: string;
  exchange?: string;        // "NASDAQ"

  matchPercent: number;     // 0..100

  sector?: string;          // "Healthcare Technology"
  industry?: string;        // "Medical Robotics"

  marketCap?: string;       // "$2.4B" (string so backend can format)
  employees?: number;       // 850
  founded?: number;         // 2009
  peRatio?: string;         // "32.5" or "—"

  whyFits?: string;
  detailsUrl?: string;
}

export interface AssistantContent {
  text: string;
  stocks?: StockProfile[];
}

export interface ChatMessage {
  id: string;
  role: Role;
  createdAt: number;

  // user uses text
  text?: string;

  // assistant uses content
  content?: AssistantContent;

  status?: "sending" | "sent" | "error";
}

/** request -> backend */
export interface RecommendationRequest {
  query: string;
  topK?: number;
  sessionId?: string;
}

/** response <- backend */
export interface RecommendationResponse {
  message: string;
  recommendations: StockProfile[];
}
