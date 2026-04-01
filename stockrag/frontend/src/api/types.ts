// src/api/types.ts

export type Role = "user" | "assistant";

//TODO: Adjust as API Contract changes
export interface StockProfile {
  cik: string;
  companyName: string;
  ticker: string;
  exchange?: string;        // "NASDAQ"

  sector?: string;          // "Healthcare Technology"
  whyFits?: string;
  sourceDocTypes?: string[];

  // Financial metrics from most recent filing
  revenue?: number | null;
  netIncome?: number | null;
  profitMargin?: string | null;
  grossMargin?: string | null;
  epsD?: number | null;
  totalAssets?: number | null;
  cash?: number | null;
  equity?: number | null;
  grossProfit?: number | null;
  operatingIncome?: number | null;
  totalLiabilities?: number | null;
  ocf?: number | null;
  ocfMargin?: string | null;
  currentRatio?: string | null;
  fiscalYear?: number | null;

  // Live price / external link
  currentPrice?: number | null;
  edgarUrl?: string | null;
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
