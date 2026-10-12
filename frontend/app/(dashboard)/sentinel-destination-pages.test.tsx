import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock the API client so pages fall back to their bundled snapshots and stay
// deterministic + offline.
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  const reject = () => Promise.reject(new Error("offline test"));
  return {
    ...actual,
    api: {
      ...actual.api,
      heatmap: reject,
      hotspotQuotes: reject,
      board: reject,
      sentinelMetrics: reject,
      complaints: reject,
      resolveComplaint: reject,
      demoWhatsapp: reject,
    },
  };
});

// next/dynamic is used by the destination page for the leaflet map; render the
// loading fallback synchronously so the page is testable without leaflet.
vi.mock("next/dynamic", () => ({
  default: () => () => null,
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

import DestinationPage from "./destination/page";
import CheckoutShieldPage from "./checkout-shield/page";
import ComplaintsPage from "./complaints/page";

describe("Destination Lens + Sentinel pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the Destination Lens heatmap with theme + date filters", () => {
    render(<DestinationPage />);
    expect(screen.getByText("Destination Lens")).toBeInTheDocument();
    expect(screen.getByText("Negative-mention heatmap")).toBeInTheDocument();
    expect(screen.getByLabelText("Issue theme filter")).toBeInTheDocument();
    expect(screen.getByLabelText("Start date filter")).toBeInTheDocument();
    expect(screen.getByLabelText("End date filter")).toBeInTheDocument();
  });

  it("renders the Checkout Shield live board with risk rows", () => {
    render(<CheckoutShieldPage />);
    expect(screen.getByText("Checkout Shield")).toBeInTheDocument();
    expect(screen.getByText("High risk (≥ 0.6)")).toBeInTheDocument();
    // At least one room row renders from the snapshot.
    expect(screen.getAllByText(/Room /).length).toBeGreaterThan(0);
  });

  it("renders the Complaints queue, triage view and week metrics", () => {
    render(<ComplaintsPage />);
    expect(screen.getByText("Complaints")).toBeInTheDocument();
    expect(screen.getByText("In-stay resolution rate")).toBeInTheDocument();
    expect(screen.getByText("Repeat complaints / week")).toBeInTheDocument();
    expect(screen.getByText("Queue")).toBeInTheDocument();
  });
});
