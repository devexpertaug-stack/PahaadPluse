"use client";

import { PageHeader, Card, Badge } from "@/components/ui";
import { UnmappedCategoriesTable } from "@/components/market-radar/UnmappedCategoriesTable";
import { LoadState, liveBadgeProps } from "@/components/common/LoadState";
import { useLiveData } from "@/lib/useLiveData";
import { api, type UnmappedCategory } from "@/lib/api";

const THRESHOLD = 20;

export default function UnmappedCategoriesPage() {
  const { status, data, reload } = useLiveData<UnmappedCategory[]>(async () => {
    const res = await api.unmappedCategories(THRESHOLD);
    return res.categories;
  });
  const badge = liveBadgeProps(status);

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · Admin"
        title="Unmapped categories"
        description={`Platform sub-rating categories seen more than ${THRESHOLD} times with no canonical Aspect mapping. Add them to the next mapping version.`}
        actions={<Badge tone={badge.tone}>{badge.label}</Badge>}
      />

      <Card
        title={`Needs mapping (> ${THRESHOLD} occurrences)`}
        subtitle="Publishing a new mapping version re-normalises affected platforms (Req 5.8)"
      >
        <LoadState
          status={status}
          onRetry={reload}
          emptyTitle="No unmapped categories"
          emptyBody="Every platform sub-rating category above the threshold is already mapped to a canonical Aspect."
        >
          <UnmappedCategoriesTable
            categories={data ?? []}
            threshold={THRESHOLD}
          />
        </LoadState>
      </Card>
    </div>
  );
}
