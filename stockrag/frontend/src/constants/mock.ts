// src/constants/mock.ts

import type { RecommendationResponse } from "../api/types.ts";

export const MOCK_RECOMMENDATIONS: RecommendationResponse = {
  message: "Mock data — backend unavailable. Showing sample results.",
  recommendations: [
    {
      companyName: "Intuitive Surgical",
      ticker: "ISRG",
      exchange: "NASDAQ",
      matchPercent: 92,
      sector: "Healthcare Technology",
      industry: "Medical Robotics",
      marketCap: "$158.2B",
      employees: 12_000,
      founded: 1995,
      peRatio: "68.4",
      whyFits:
        "Industry leader in robotic-assisted surgery with da Vinci systems.",
      detailsUrl: "https://finance.yahoo.com/quote/ISRG",
    },
    {
      companyName: "Palantir Technologies",
      ticker: "PLTR",
      exchange: "NYSE",
      matchPercent: 85,
      sector: "Technology",
      industry: "Software — Infrastructure",
      marketCap: "$54.8B",
      employees: 3_700,
      founded: 2003,
      peRatio: "240.1",
      whyFits:
        "AI-driven data analytics platform used across government and enterprise.",
      detailsUrl: "https://finance.yahoo.com/quote/PLTR",
    },
    {
      companyName: "Enphase Energy",
      ticker: "ENPH",
      exchange: "NASDAQ",
      matchPercent: 78,
      sector: "Energy",
      industry: "Solar",
      marketCap: "$14.1B",
      employees: 5_600,
      founded: 2006,
      peRatio: "45.2",
      whyFits:
        "Designs microinverters for the solar photovoltaics industry.",
      detailsUrl: "https://finance.yahoo.com/quote/ENPH",
    },
  ],
};
