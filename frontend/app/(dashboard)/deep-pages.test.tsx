import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock the API client so pages fall back to their bundled snapshots and the
// tests stay deterministic + offline.
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  const reject = () => Promise.reject(new Error("offline test"));
  return {
    ...actual,
    api: {
      ...actual.api,
      reviewCounts: reject,
      trends: reject,
      decomposition: reject,
      changepoints: reject,
      whatIfModel: reject,
      whatIfProject: reject,
      timeMachine: reject,
      playbook: reject,
      gapFinder: reject,
      benchmark: reject,
    },
  };
});

import WhatIfPage from "./what-if/page";
import TimeMachinePage from "./time-machine/page";
import PlaybookPage from "./playbook/page";
import GapFinderPage from "./gap-finder/page";
import BenchmarkPage from "./benchmark/page";
import MarketRadarPage from "./market-radar/page";

// next/navigation is referenced by the layout but not these pages directly.
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("Market Radar Deep feature pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the What-If Simulator with driver weights and sliders", () => {
    render(<WhatIfPage />);
    expect(screen.getByText("Rating What-If Simulator")).toBeInTheDocument();
    expect(screen.getByText("Driver weights")).toBeInTheDocument();
    expect(screen.getByText("Current rating")).toBeInTheDocument();
    // one slider per aspect
    expect(screen.getByLabelText("Food slider")).toBeInTheDocument();
  });

  it("renders the Time Machine with a changepoint and causes", () => {
    render(<TimeMachinePage />);
    expect(screen.getByText("Root-Cause Time Machine")).toBeInTheDocument();
    expect(screen.getByText("Nearest changepoint")).toBeInTheDocument();
  });

  it("renders the Playbook with a lagging aspect and action", () => {
    render(<PlaybookPage />);
    expect(screen.getByText("Steal-the-Winner Playbook")).toBeInTheDocument();
    expect(screen.getByText("Suggested action")).toBeInTheDocument();
    expect(screen.getByText("template-generated")).toBeInTheDocument();
  });

  it("renders the Gap Finder with ranked themes", () => {
    render(<GapFinderPage />);
    expect(screen.getByText("Market Gap Finder")).toBeInTheDocument();
    // Service is a cluster-wide weak aspect in the sample data.
    expect(screen.getAllByText(/Service/i).length).toBeGreaterThan(0);
  });

  it("renders the Benchmark table and confusion matrix", () => {
    render(<BenchmarkPage />);
    expect(screen.getByText("Hinglish Accuracy Benchmark")).toBeInTheDocument();
    expect(screen.getByText("Results by system")).toBeInTheDocument();
    expect(screen.getByText("Per-aspect confusion matrix")).toBeInTheDocument();
  });

  it("renders Market Radar trends and decomposition panels", () => {
    render(<MarketRadarPage />);
    expect(screen.getByText("Aspect sentiment trends")).toBeInTheDocument();
    expect(
      screen.getByText("Market-wide vs property-specific decomposition"),
    ).toBeInTheDocument();
  });
});
