import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatTile } from "./StatTile";
import { Badge } from "./Badge";

describe("design-system components", () => {
  it("renders a StatTile with its label, value and hint", () => {
    render(<StatTile label="Properties tracked" value="12" hint="demo" trend="up" />);
    expect(screen.getByText("Properties tracked")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("demo")).toBeInTheDocument();
  });

  it("applies the forest tone to a Badge by default", () => {
    render(<Badge>Baseline</Badge>);
    const badge = screen.getByText("Baseline");
    expect(badge.className).toContain("text-forest-800");
  });
});
