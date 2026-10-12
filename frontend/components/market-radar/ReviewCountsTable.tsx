import { Table, type TableColumn } from "@/components/ui";
import type { PropertyCounts } from "@/lib/api";
import { PLATFORMS } from "@/lib/api";

export interface ReviewCountsTableProps {
  properties: PropertyCounts[];
}

/**
 * Per-property, per-platform review counts (Req 1.10). Pure presentational
 * component so it can be unit-tested without the network.
 */
export function ReviewCountsTable({ properties }: ReviewCountsTableProps) {
  const columns: TableColumn<PropertyCounts>[] = [
    {
      key: "property",
      header: "Property",
      render: (row) => (
        <span className="font-medium text-forest-800">{row.property_name}</span>
      ),
    },
    ...PLATFORMS.map((platform) => ({
      key: platform,
      header: platform,
      className: "text-center",
      render: (row: PropertyCounts) => (
        <span className="tabular-nums">{row.per_platform[platform] ?? 0}</span>
      ),
    })),
    {
      key: "total",
      header: "Total",
      className: "text-center",
      render: (row) => (
        <span className="font-semibold tabular-nums text-forest-800">
          {row.total}
        </span>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      rows={properties}
      getRowKey={(row) => row.property_id}
      emptyMessage="No reviews collected yet."
    />
  );
}
