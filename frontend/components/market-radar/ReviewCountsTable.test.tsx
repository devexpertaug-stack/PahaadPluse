import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReviewCountsTable } from "./ReviewCountsTable";
import { UnmappedCategoriesTable } from "./UnmappedCategoriesTable";
import type { PropertyCounts, UnmappedCategory } from "@/lib/api";

const PROPERTIES: PropertyCounts[] = [
  {
    property_id: "mus-pineview",
    property_name: "Pine View Inn",
    total: 5,
    per_platform: {
      Google: 1,
      MakeMyTrip: 1,
      "Booking.com": 1,
      TripAdvisor: 1,
      Agoda: 1,
    },
    missing_source_url: 0,
  },
];

const UNMAPPED: UnmappedCategory[] = [
  { platform: "Google", category: "Parking", count: 23 },
];

describe("Market Radar tables", () => {
  it("renders per-property, per-platform review counts", () => {
    render(<ReviewCountsTable properties={PROPERTIES} />);
    expect(screen.getByText("Pine View Inn")).toBeInTheDocument();
    expect(screen.getByText("Google")).toBeInTheDocument();
    // Total column shows 5.
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("renders an empty message when there are no reviews", () => {
    render(<ReviewCountsTable properties={[]} />);
    expect(screen.getByText("No reviews collected yet.")).toBeInTheDocument();
  });

  it("renders the unmapped categories admin surface", () => {
    render(<UnmappedCategoriesTable categories={UNMAPPED} threshold={20} />);
    expect(screen.getByText("Parking")).toBeInTheDocument();
    expect(screen.getByText("23")).toBeInTheDocument();
  });
});
