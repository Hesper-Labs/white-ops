import { useState, useMemo } from 'react';
import { Search, ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Skeleton } from './Skeleton';
import { EmptyState } from './EmptyState';

interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (value: any, row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  pageSize?: number;
  searchable?: boolean;
  searchPlaceholder?: string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  loading?: boolean;
  actions?: (row: T) => React.ReactNode;
}

type SortDir = 'asc' | 'desc' | null;

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  pageSize = 10,
  searchable = false,
  searchPlaceholder = 'Search...',
  onRowClick,
  emptyMessage = 'No data found',
  loading = false,
  actions,
}: DataTableProps<T>) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);
  const [page, setPage] = useState(0);

  // Filter
  const filtered = useMemo(() => {
    if (!search.trim()) return data;
    const q = search.toLowerCase();
    return data.filter((row) =>
      Object.values(row).some(
        (v) => typeof v === 'string' && v.toLowerCase().includes(q),
      ),
    );
  }, [data, search]);

  // Sort
  const sorted = useMemo(() => {
    if (!sortKey || !sortDir) return filtered;
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }
      const aStr = String(aVal).toLowerCase();
      const bStr = String(bVal).toLowerCase();
      return sortDir === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
    });
  }, [filtered, sortKey, sortDir]);

  // Paginate
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, totalPages - 1);
  const paged = sorted.slice(safePage * pageSize, (safePage + 1) * pageSize);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : d === 'desc' ? null : 'asc'));
      if (sortDir === 'desc') setSortKey(null);
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
    setPage(0);
  };

  const allColumns = actions
    ? [...columns, { key: '__actions', label: '', sortable: false } as Column<T>]
    : columns;

  if (loading) {
    return (
      <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 overflow-hidden bg-white dark:bg-neutral-800">
        <div className="p-4 space-y-3">
          <Skeleton variant="rect" height={36} />
          <Skeleton variant="text" count={5} />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 overflow-hidden bg-white dark:bg-neutral-800">
      {/* Search */}
      {searchable && (
        <div className="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" aria-hidden="true" />
            <input
              type="search"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              placeholder={searchPlaceholder}
              aria-label={searchPlaceholder}
              role="searchbox"
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-neutral-200 bg-neutral-50 text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-300 dark:border-neutral-600 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 dark:focus:ring-neutral-500"
            />
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto" role="region" aria-label="Data table" tabIndex={0}>
        <table className="w-full text-sm" role="table">
          <thead className="sticky top-0 z-10">
            <tr className="bg-neutral-50 dark:bg-neutral-900/50 border-b border-neutral-200 dark:border-neutral-700">
              {allColumns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={sortKey === col.key ? (sortDir === 'asc' ? 'ascending' : sortDir === 'desc' ? 'descending' : 'none') : undefined}
                  className={cn(
                    'px-4 py-3 text-left text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider whitespace-nowrap',
                    col.sortable && 'cursor-pointer select-none hover:text-neutral-700 dark:hover:text-neutral-300',
                    col.className,
                  )}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  onKeyDown={col.sortable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort(col.key); } } : undefined}
                  tabIndex={col.sortable ? 0 : undefined}
                  role={col.sortable ? 'columnheader button' : 'columnheader'}
                  aria-label={col.sortable ? `Sort by ${col.label}` : col.label}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {col.sortable && (
                      <span className="text-neutral-300 dark:text-neutral-600" aria-hidden="true">
                        {sortKey === col.key && sortDir === 'asc' ? (
                          <ChevronUp className="h-3.5 w-3.5 text-neutral-700 dark:text-neutral-300" />
                        ) : sortKey === col.key && sortDir === 'desc' ? (
                          <ChevronDown className="h-3.5 w-3.5 text-neutral-700 dark:text-neutral-300" />
                        ) : (
                          <ChevronsUpDown className="h-3.5 w-3.5" />
                        )}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100 dark:divide-neutral-700">
            {paged.length === 0 ? (
              <tr>
                <td colSpan={allColumns.length}>
                  <EmptyState title={emptyMessage} />
                </td>
              </tr>
            ) : (
              paged.map((row, i) => (
                <tr
                  key={i}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cn(
                    'transition-colors',
                    onRowClick && 'cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-700/50',
                  )}
                >
                  {columns.map((col) => (
                    <td key={col.key} className={cn('px-4 py-3 text-neutral-700 dark:text-neutral-300', col.className)}>
                      {col.render ? col.render(row[col.key], row) : row[col.key]}
                    </td>
                  ))}
                  {actions && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">{actions(row)}</div>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {sorted.length > pageSize && (
        <nav className="flex items-center justify-between px-4 py-3 border-t border-neutral-200 dark:border-neutral-700" aria-label="Table pagination">
          <span className="text-xs text-neutral-500 dark:text-neutral-400" aria-live="polite">
            {safePage * pageSize + 1}-{Math.min((safePage + 1) * pageSize, sorted.length)} of {sorted.length}
          </span>
          <div className="flex items-center gap-1" role="group" aria-label="Pagination controls">
            <button
              disabled={safePage === 0}
              onClick={() => setPage((p) => p - 1)}
              aria-label="Previous page"
              className="p-1.5 rounded-md text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 disabled:opacity-40 disabled:pointer-events-none dark:hover:text-neutral-300 dark:hover:bg-neutral-700"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                onClick={() => setPage(i)}
                className={cn(
                  'h-7 min-w-[28px] rounded-md text-xs font-medium transition-colors',
                  i === safePage
                    ? 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900'
                    : 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700',
                )}
              >
                {i + 1}
              </button>
            ))}
            <button
              disabled={safePage >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
              aria-label="Next page"
              className="p-1.5 rounded-md text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 disabled:opacity-40 disabled:pointer-events-none dark:hover:text-neutral-300 dark:hover:bg-neutral-700"
            >
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </nav>
      )}
    </div>
  );
}
