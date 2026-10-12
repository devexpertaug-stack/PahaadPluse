import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function ComplaintsPage() {
  return (
    <PlaceholderPage
      group="In-Stay Sentinel"
      title="Complaints"
      description="Live in-stay complaints captured and routed to resolution."
      highlights={[
        "Inbound complaints via the WhatsApp gateway (mock in demo)",
        "Triage by severity and category",
        "Track resolution and guest follow-up",
      ]}
    />
  );
}
