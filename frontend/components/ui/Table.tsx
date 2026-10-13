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
    <div className="glass-panel overflow-hidden bg-mist-white/60">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-forest-50/70 text-left text-forest-700 backdrop-blur-sm">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "px-4 py-3 font-display text-xs font-semibold uppercase tracking-wide",
                  col.className,
                )}
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
                className="px-4 py-6 text-center text-slate-400"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, index) => (
              <tr
                key={getRowKey(row, index)}
                className="border-t border-mist-200/60 transition-colors hover:bg-pp-leaf/10"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn("px-4 py-3 text-slate-700", col.className)}
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
