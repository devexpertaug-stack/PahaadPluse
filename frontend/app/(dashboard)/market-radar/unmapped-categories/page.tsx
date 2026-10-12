"use client";

import { useEffect, useState } from "react";
import { PageHeader, Card, Badge } from "@/components/ui";
import { UnmappedCategoriesTable } from "@/components/market-radar/UnmappedCategoriesTable";
import { api, type UnmappedCategory } from "@/lib/api";
import snapshot from "@/lib/marketRadarSnapshot.json";

const THRESHOLD = 20;
const SNAPSHOT = snapshot.unmapped as UnmappedCategory[];

export default function UnmappedCategoriesPage() {
  const [categories, setCategories] = useState<UnmappedCategory[]>(SNAPSHOT);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .unmappedCategories(THRESHOLD)
      .then((res) => {
        if (active) {
          setCategories(res.categories);
          setLive(true);
        }
      })
      .catch(() => {
        /* keep bundled snapshot */
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div>
      <PageHeader
        eyebrow="Market Radar · Admin"
        title="Unmapped categories"
        description={`Platform sub-rating categories seen more than ${THRESHOLD} times with no canonical Aspect mapping. Add them to the next mapping version.`}
        actions={
          <Badge tone={live ? "forest" : "dawn"}>
            {live ? "Live from API" : "Sample snapshot"}
          </Badge>
        }
      />

      <Card
        title={`Needs mapping (> ${THRESHOLD} occurrences)`}
        subtitle="Publishing a new mapping version re-normalises affected platforms (Req 5.8)"
      >
        <UnmappedCategoriesTable categories={categories} threshold={THRESHOLD} />
      </Card>
    </div>
  );
}
