import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function ConciergePage() {
  return (
    <PlaceholderPage
      group="Bhasha Concierge"
      title="Bhasha Concierge"
      description="A multilingual guest-messaging assistant for Hindi, Hinglish and English."
      highlights={[
        "Draft replies in the guest's language",
        "Deterministic template fallback when no LLM is configured",
        "All responses clearly labelled when template-generated",
      ]}
    />
  );
}
