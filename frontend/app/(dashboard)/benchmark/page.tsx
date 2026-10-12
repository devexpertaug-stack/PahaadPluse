import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function BenchmarkPage() {
  return (
    <PlaceholderPage
      group="Bhasha Concierge"
      title="Hinglish Benchmark"
      description="Model quality on the labelled Hinglish test set (Deep feature F12)."
      highlights={[
        "Benchmark table across sentiment models",
        "Hinglish test set kept separate from tuning data",
        "Transparent, reproducible evaluation harness",
      ]}
    />
  );
}
