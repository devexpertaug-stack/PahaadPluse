import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface TableColumn<Row> {
  key: string;
  header: ReactNode;
  render: (row: Row) => ReactNode;
  className?: string;
}

export interface TableProps<Row> {
  columns: TableColumn<Row>[];
  rows: Row[];
  getRowKey: (row: Row, index: number) => string;
  emptyMessage?: string;
}

export function Table<Row>({
  columns,
  rows,
  getRowKey,
  emptyMessage = "No data yet.",
}: TableProps<Row>) {
  return (
    <div className="overflow-hidden rounded-2xl border border-mist-300 bg-mist-50 shadow-tile">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-forest-50 text-left text-forest-700">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn("px-4 py-3 font-semibold", col.className)}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-6 text-center text-forest-600/70"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, index) => (
              <tr
                key={getRowKey(row, index)}
                className="border-t border-mist-200 hover:bg-mist-100"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn("px-4 py-3 text-forest-800", col.className)}
                  >
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
