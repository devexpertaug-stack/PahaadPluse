import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function PlaybookPage() {
  return (
    <PlaceholderPage
      group="Market Radar"
      title="Playbook"
      description="Recommended actions mapped to the signals Market Radar detects (Deep feature F5)."
      highlights={[
        "Prioritised, evidence-backed recommendations",
        "Clear owner and expected impact per action",
        "Track which plays were run and their outcomes",
      ]}
    />
  );
}
