import Link from "next/link";
import { PageHeader, StatTile, Card, Button, Badge } from "@/components/ui";
import { navItems } from "@/lib/theme";

export default function MetricsOverviewPage() {
  const subsystemLinks = navItems.filter((item) => item.href !== "/");

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Metrics Overview"
        description="A single pane over every PahadPulse subsystem. Numbers are placeholders until later features wire in live data; the whole platform already runs on local fallbacks with no third-party credentials."
        actions={<Badge tone="forest">Baseline</Badge>}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Properties tracked" value="—" hint="Seeded by demo" trend="flat" />
        <StatTile label="Reviews analysed" value="—" hint="Sentinel pipeline" trend="flat" />
        <StatTile label="Open complaints" value="—" hint="In-Stay Sentinel" trend="flat" />
        <StatTile label="Checkout risk saved" value="—" hint="Checkout Shield" trend="flat" />
      </div>

      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-forest-800">
          Explore the platform
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {subsystemLinks.map((item) => (
            <Card
              key={item.href}
              title={item.label}
              subtitle={item.group}
              footer={
                <Link href={item.href}>
                  <Button variant="ghost" size="sm">
                    Open {item.label} →
                  </Button>
                </Link>
              }
            >
              <p className="text-sm text-forest-700">{item.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
