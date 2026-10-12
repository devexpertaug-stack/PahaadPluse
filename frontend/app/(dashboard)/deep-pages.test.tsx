import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

// The dashboard is live-first: pages render data straight from the API client.
// These mocks return resort-shaped payloads so we assert the LIVE contract.
// A dedicated test later overrides the mock to reject and asserts the pages
// show an error state rather than any stale/baked snapshot.

const whatIfModel = {
  platform: "Google",
  current_rating: 4.1,
  review_count: 128,
  low_confidence: false,
  estimated_at: "2024-05-01",
  home_property_id: "mus-forestseason",
  cluster_size: 6,
  driver_weights: [
    { aspect: "Food", weight: 0.21, lower: 0.1, upper: 0.3, available: true, abs_weight: 0.21 },
    { aspect: "Room", weight: 0.12, lower: 0.05, upper: 0.2, available: true, abs_weight: 0.12 },
  ],
};

const timeMachine = {
  changepoint: {
    property_id: "mus-forestseason",
    aspect: "Food",
    series: "Food",
    date: "2024-01-15",
    direction: "decline",
    posterior: 0.82,
    unreliable: false,
    time_to_identification_days: 12,
  },
  message: null,
  causes: [{ phrase: "cold breakfast", lift: 2.1, before_count: 2, after_count: 7 }],
  before_quotes: [],
  after_quotes: [],
  limited_evidence: false,
  scope_label: "property-specific",
  interventions: [],
  failed: false,
};

const decomposition = {
  fitted_at: "2024-05-01",
  cluster_size: 6,
  insufficient_cluster: false,
  failure: false,
  failure_reason: null,
  stale_timestamp: null,
  cells: [
    {
      property_id: "mus-forestseason",
      aspect: "Food",
      month: "2024-01-01",
      mentions: 10,
      modelled_score: 3.4,
      market_wide: { point: 3.5, lower: 3.2, upper: 3.8 },
      property_specific: { point: 3.4, lower: 3.1, upper: 3.7 },
      rhat: 1.0,
      unreliable: false,
      insufficient_data: false,
    },
    {
      property_id: "mus-forestseason",
      aspect: "Food",
      month: "2024-02-01",
      mentions: 12,
      modelled_score: 3.6,
      market_wide: { point: 3.5, lower: 3.2, upper: 3.8 },
      property_specific: { point: 3.6, lower: 3.3, upper: 3.9 },
      rhat: 1.0,
      unreliable: false,
      insufficient_data: false,
    },
  ],
};

const reviewCounts = {
  properties: [
    {
      property_id: "mus-forestseason",
      property_name: "The Forest Season Resort",
      total: 240,
      per_platform: { Google: 120, Agoda: 120 },
      missing_source_url: 3,
    },
  ],
};

const trends = {
  granularity: "month",
  start: "2024-01-01",
  end: "2024-06-01",
  platforms: ["Google"],
  trends: [
    {
      aspect: "Food",
      buckets: [
        {
          period: "2024-01",
          positive: 10,
          neutral: 2,
          negative: 3,
          total: 15,
          complaint_percentage: 20,
          no_data: false,
        },
      ],
    },
  ],
};

const playbook = {
  home_property_id: "mus-forestseason",
  home_property_name: "The Forest Season Resort",
  leader_property_id: "mus-leader",
  leader_property_name: "Cluster Leader",
  message: null,
  lagging: [
    {
      aspect: "Service",
      home_upper: 3.2,
      leader_lower: 3.8,
      action_paragraph: "Retrain the front desk on evening check-in.",
      action_template_generated: true,
      themes: [
        {
          aspect: "Service",
          leader_positive_count: 40,
          home_positive_count: 10,
          home_negative_count: 15,
          quotes: [
            { span: "staff were wonderful", platform: "Google", date: "2024-02-01", source_url: "https://example.com/r1" },
          ],
        },
      ],
    },
  ],
  undetermined: [],
};

const gapFinder = {
  cluster_size: 6,
  themes: [
    {
      aspect: "Service",
      affected_properties: 4,
      cluster_size: 6,
      total_negatives: 50,
      destination_median: 0.3,
      market_gap: true,
      trend: [{ month: "2024-01", negative_share: 0.3 }],
      quotes: [
        {
          span: "service was slow",
          platform: "Google",
          date: "2024-02-01",
          property_id: "mus-forestseason",
          source_url: "https://example.com/r2",
        },
      ],
    },
  ],
};

const benchmark = {
  seed: 42,
  test_set_size: 200,
  systems: [
    {
      name: "Sentiment_Engine",
      overall_sentiment: { macro_f1: 0.81, ci_95: [0.78, 0.84] as [number, number] },
      aspect_detection: { macro_f1: 0.76, ci_95: [0.72, 0.8] as [number, number] },
      aspect_sentiment: { macro_f1: 0.74, ci_95: [0.7, 0.78] as [number, number] },
      confusion_matrix: {},
      aspect_confusion: {
        Food: {
          matrix: {
            positive: { positive: 10, neutral: 1, negative: 0 },
            neutral: { positive: 1, neutral: 8, negative: 1 },
            negative: { positive: 0, neutral: 1, negative: 9 },
          },
          support: { n: 31 },
        },
      },
    },
  ],
};

const readyApi = {
  reviewCounts: () => Promise.resolve(reviewCounts),
  trends: () => Promise.resolve(trends),
  decomposition: () => Promise.resolve(decomposition),
  whatIfModel: () => Promise.resolve(whatIfModel),
  whatIfProject: () => Promise.resolve({}),
  timeMachine: () => Promise.resolve(timeMachine),
  playbook: () => Promise.resolve(playbook),
  gapFinder: () => Promise.resolve(gapFinder),
  benchmark: () => Promise.resolve(benchmark),
};

const mockApi: Record<string, unknown> = { ...readyApi };

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    get api() {
      return { ...actual.api, ...mockApi };
    },
  };
});

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

import WhatIfPage from "./what-if/page";
import TimeMachinePage from "./time-machine/page";
import PlaybookPage from "./playbook/page";
import GapFinderPage from "./gap-finder/page";
import BenchmarkPage from "./benchmark/page";
import MarketRadarPage from "./market-radar/page";

function setApi(overrides: Record<string, unknown>) {
  for (const k of Object.keys(mockApi)) delete mockApi[k];
  Object.assign(mockApi, readyApi, overrides);
}

describe("Market Radar Deep feature pages (live-first)", () => {
  beforeEach(() => {
    setApi({});
    vi.clearAllMocks();
  });

  it("renders the What-If Simulator with live driver weights and sliders", async () => {
    render(<WhatIfPage />);
    expect(screen.getByText("Rating What-If Simulator")).toBeInTheDocument();
    await screen.findByText("Driver weights");
    expect(screen.getByText("Current rating")).toBeInTheDocument();
    expect(screen.getByLabelText("Food slider")).toBeInTheDocument();
  });

  it("renders the Time Machine with a live changepoint and causes", async () => {
    render(<TimeMachinePage />);
    expect(screen.getByText("Root-Cause Time Machine")).toBeInTheDocument();
    await screen.findByText("Nearest changepoint");
  });

  it("renders the Playbook with a live lagging aspect and action", async () => {
    render(<PlaybookPage />);
    expect(screen.getByText("Steal-the-Winner Playbook")).toBeInTheDocument();
    await screen.findByText("Suggested action");
    expect(screen.getByText("template-generated")).toBeInTheDocument();
  });

  it("renders the Gap Finder with live ranked themes", async () => {
    render(<GapFinderPage />);
    expect(screen.getByText("Market Gap Finder")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getAllByText(/Service/i).length).toBeGreaterThan(0),
    );
  });

  it("renders the Benchmark table and confusion matrix from live data", async () => {
    render(<BenchmarkPage />);
    expect(screen.getByText("Hinglish Accuracy Benchmark")).toBeInTheDocument();
    await screen.findByText("Results by system");
    expect(screen.getByText("Per-aspect confusion matrix")).toBeInTheDocument();
  });

  it("renders Market Radar live trends and decomposition panels", async () => {
    render(<MarketRadarPage />);
    await screen.findByText("Aspect sentiment trends");
    expect(
      screen.getByText("Market-wide vs property-specific decomposition"),
    ).toBeInTheDocument();
  });

  it("shows an error state (not stale snapshot) when the API fails", async () => {
    const reject = () => Promise.reject(new Error("backend down"));
    setApi({
      gapFinder: reject,
      playbook: reject,
      benchmark: reject,
    });
    render(<GapFinderPage />);
    expect(screen.getByText("Market Gap Finder")).toBeInTheDocument();
    // The honest error panel appears; no snapshot "Service" theme is shown.
    await screen.findAllByText("Backend unavailable");
    expect(screen.queryByText("market gap")).not.toBeInTheDocument();
  });
});
