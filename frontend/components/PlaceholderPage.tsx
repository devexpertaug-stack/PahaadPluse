import { PageHeader, Card, Badge } from "@/components/ui";

export interface PlaceholderPageProps {
  group: string;
  title: string;
  description: string;
  highlights?: string[];
}

/**
 * Themed placeholder used by every subsystem route until its feature lands.
 * Keeps the whole website navigable end to end from day one.
 */
export function PlaceholderPage({
  group,
  title,
  description,
  highlights = [],
}: PlaceholderPageProps) {
  return (
    <div>
      <PageHeader
        eyebrow={group}
        title={title}
        description={description}
        actions={<Badge tone="dawn">Coming soon</Badge>}
      />
      <div className="grid gap-5 md:grid-cols-2">
        <Card
          title="What this page will do"
          subtitle="Scaffolded now, filled in by a later feature"
        >
          <ul className="list-disc space-y-2 pl-5 text-sm text-forest-700">
            {highlights.length > 0 ? (
              highlights.map((item) => <li key={item}>{item}</li>)
            ) : (
              <li>Content for this subsystem is on the way.</li>
            )}
          </ul>
        </Card>
        <Card
          title="One website, one design system"
          subtitle="Mussoorie / Uttarakhand hill-town theme"
        >
          <p className="text-sm text-forest-700">
            Every subsystem lives inside this single PahadPulse website and
            shares the same green/white forest theme, app shell and component
            library. Use the sidebar to move between pages.
          </p>
        </Card>
      </div>
    </div>
  );
}
