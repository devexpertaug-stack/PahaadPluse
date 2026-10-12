import { Table, Badge, type TableColumn } from "@/components/ui";
import type { UnmappedCategory } from "@/lib/api";

export interface UnmappedCategoriesTableProps {
  categories: UnmappedCategory[];
  threshold: number;
}

/**
 * Admin surface for unmapped sub-rating categories seen more than the
 * threshold number of times (Req 5.7). Pure presentational component.
 */
export function UnmappedCategoriesTable({
  categories,
  threshold,
}: UnmappedCategoriesTableProps) {
  const columns: TableColumn<UnmappedCategory>[] = [
    {
      key: "platform",
      header: "Platform",
      render: (row) => <span className="font-medium">{row.platform}</span>,
    },
    {
      key: "category",
      header: "Unmapped category",
      render: (row) => row.category,
    },
    {
      key: "count",
      header: "Occurrences",
      className: "text-center",
      render: (row) => (
        <Badge tone="dawn" className="tabular-nums">
          {row.count}
        </Badge>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      rows={categories}
      getRowKey={(row) => `${row.platform}:${row.category}`}
      emptyMessage={`No unmapped categories above ${threshold} occurrences.`}
    />
  );
}
