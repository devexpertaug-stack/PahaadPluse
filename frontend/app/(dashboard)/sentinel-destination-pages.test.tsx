import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// Live-first contract: these pages render data straight from the API client.
// We mock the client to return resort-shaped payloads, then add a test that an
// API failure shows an error state instead of a stale baked snapshot.

const heatmap = {
  destination: "Mussoorie",
  theme: null,
  themes_available: ["traffic", "parking"],
  start: null,
  end: null,
  total_negative_mentions: 42,
  hotspots: [
    {
      canonical: "mall-road",
      label: "Mall Road",
      latitude: 30.45,
      longitude: 78.08,
      negative_count: 20,
      total_count: 60,
      themes: { traffic: 12, parking: 8 },
      distinct_properties: 3,
    },
  ],
};

const board = {
  generated_at: "2024-05-01T10:00:00Z",
  high_risk_threshold: 0.6,
  rows: [
    {
      stay_id: "stay-1",
      room: "201",
      guest_pseudonym: "guest-ab12",
      hours_to_checkout: 3.5,
      score: 0.72,
      high_risk: true,
      pinned: true,
      top_factors: [{ label: "open P1 complaint", contribution: 0.3 }],
      top_open_complaint: {
        id: "c-1",
        issue_type: "Hot water",
        urgency: "P1",
        department: "Maintenance",
        text: "no hot water",
      },
      responsible_department: "Maintenance",
      sop_action: "Dispatch technician within 15 min",
    },
  ],
};

const sentinelMetrics = {
  avg_complaint_to_department_seconds: 4.2,
  in_stay_resolution_rate: 0.78,
  repeat_complaints_this_week: 1,
  total_complaints: 20,
  resolved_complaints: 15,
  open_complaints: 5,
};

const complaints = {
  complaints: [
    {
      id: "c-1",
      stay_id: "stay-1",
      room: "201",
      guest_pseudonym: "guest-ab12",
      channel: "whatsapp",
      text: "no hot water in the room",
      language: "en",
      transcript: null,
      transcript_translation_en: null,
      transcription_confidence: null,
      flagged_for_staff: false,
      created_at: "2024-05-01T09:00:00Z",
      assigned_at: "2024-05-01T09:01:00Z",
      resolved_at: null,
      department: "Maintenance",
      original_predicted_department: "Maintenance",
      department_confidence: 0.9,
      urgency: "P1",
      issue_type: "Hot water",
      requires_manual_assignment: false,
      state: "assigned",
      is_recurrence: false,
      recurrence_of: null,
      escalated: false,
      resolution_note: null,
      reassignments: [],
      sop: {
        department: "Maintenance",
        issue_type: "Hot water",
        corrective_steps: ["Check geyser breaker", "Dispatch technician"],
        target_resolution_minutes: 15,
      },
    },
  ],
};

const readyApi = {
  heatmap: () => Promise.resolve(heatmap),
  hotspotQuotes: () => Promise.resolve({ canonical: "mall-road", quotes: [] }),
  board: () => Promise.resolve(board),
  sentinelMetrics: () => Promise.resolve(sentinelMetrics),
  complaints: () => Promise.resolve(complaints),
  resolveComplaint: () => Promise.resolve({}),
  demoWhatsapp: () => Promise.resolve({}),
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

function setApi(overrides: Record<string, unknown>) {
  for (const k of Object.keys(mockApi)) delete mockApi[k];
  Object.assign(mockApi, readyApi, overrides);
}

describe("Destination Lens + Sentinel pages (live-first)", () => {
  beforeEach(() => {
    setApi({});
    vi.clearAllMocks();
  });

  it("renders the Destination Lens heatmap with live filters", async () => {
    render(<DestinationPage />);
    expect(screen.getByText("Destination Lens")).toBeInTheDocument();
    expect(screen.getByLabelText("Issue theme filter")).toBeInTheDocument();
    expect(screen.getByLabelText("Start date filter")).toBeInTheDocument();
    expect(screen.getByLabelText("End date filter")).toBeInTheDocument();
    await screen.findByText("Negative-mention heatmap");
  });

  it("renders the Checkout Shield live board with risk rows", async () => {
    render(<CheckoutShieldPage />);
    expect(screen.getByText("Checkout Shield")).toBeInTheDocument();
    await screen.findByText("High risk (≥ 0.6)");
    expect(screen.getAllByText(/Room /).length).toBeGreaterThan(0);
  });

  it("renders the Complaints queue, triage and week metrics from live data", async () => {
    render(<ComplaintsPage />);
    expect(screen.getByText("Complaints")).toBeInTheDocument();
    await screen.findByText("In-stay resolution rate");
    expect(screen.getByText("Repeat complaints / week")).toBeInTheDocument();
    expect(screen.getByText("Queue")).toBeInTheDocument();
  });

  it("shows an error state (not stale snapshot) when the board API fails", async () => {
    setApi({ board: () => Promise.reject(new Error("backend down")) });
    render(<CheckoutShieldPage />);
    expect(screen.getByText("Checkout Shield")).toBeInTheDocument();
    await screen.findAllByText("Backend unavailable");
    // No baked snapshot rows leak through on failure.
    expect(screen.queryByText(/Room 201/)).not.toBeInTheDocument();
  });
});
