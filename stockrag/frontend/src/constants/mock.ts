// src/constants/mock.ts

import type { RecommendationResponse } from "../api/types.ts";

export const MOCK_RECOMMENDATIONS: RecommendationResponse = {
  message: "Mock data — backend unavailable. Showing sample results.",
  recommendations: [
    {
      cik: "0001035267",
      companyName: "Intuitive Surgical",
      ticker: "ISRG",
      exchange: "NASDAQ",
      sector: "Healthcare Technology",
      whyFits:
        "Industry leader in robotic-assisted surgery with da Vinci systems.",
      sourceDocTypes: ["company_profile", "annual_snapshot"],
    },
    {
      cik: "0001321655",
      companyName: "Palantir Technologies",
      ticker: "PLTR",
      exchange: "NYSE",
      sector: "Technology",
      whyFits:
        "AI-driven data analytics platform used across government and enterprise.",
      sourceDocTypes: ["company_profile", "company_description"],
    },
    {
      cik: "0001463101",
      companyName: "Enphase Energy",
      ticker: "ENPH",
      exchange: "NASDAQ",
      sector: "Energy",
      whyFits:
        "Designs microinverters for the solar photovoltaics industry.",
      sourceDocTypes: ["company_profile", "company_description"],
    },
  ],
};
