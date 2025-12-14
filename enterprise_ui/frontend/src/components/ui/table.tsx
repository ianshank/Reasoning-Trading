import React, { HTMLAttributes, forwardRef, useState, useMemo } from 'react';

/**
 * Sort direction type
 */
export type SortDirection = 'asc' | 'desc' | null;

/**
 * Column definition interface
 */
export interface TableColumn<T = any> {
  /**
   * Column key (must match data property)
   */
  key: string;

  /**
   * Column header label
   */
  label: string;

  /**
   * Whether the column is sortable
   * @default false
   */
  sortable?: boolean;

  /**
   * Custom render function for cell content
   */
  render?: (value: any, row: T, index: number) => React.ReactNode;

  /**
   * Column width
   */
  width?: string | number;

  /**
   * Column alignment
   * @default 'left'
   */
  align?: 'left' | 'center' | 'right';
}

/**
 * Table component props interface
 */
export interface TableProps<T = any> extends HTMLAttributes<HTMLTableElement> {
  /**
   * Table columns configuration
   */
  columns: TableColumn<T>[];

  /**
   * Table data
   */
  data: T[];

  /**
   * Whether to show striped rows
   * @default false
   */
  striped?: boolean;

  /**
   * Whether to show hover effect on rows
   * @default true
   */
  hoverable?: boolean;

  /**
   * Whether to show borders
   * @default true
   */
  bordered?: boolean;

  /**
   * Enable pagination
   * @default false
   */
  pagination?: boolean;

  /**
   * Rows per page
   * @default 10
   */
  pageSize?: number;

  /**
   * Current page (controlled)
   */
  currentPage?: number;

  /**
   * Page change handler
   */
  onPageChange?: (page: number) => void;

  /**
   * Sort change handler
   */
  onSort?: (key: string, direction: SortDirection) => void;

  /**
   * Row click handler
   */
  onRowClick?: (row: T, index: number) => void;

  /**
   * Loading state
   * @default false
   */
  loading?: boolean;

  /**
   * Empty state message
   */
  emptyMessage?: string;
}

/**
 * Data table component with sorting and pagination
 *
 * @example
 * ```tsx
 * <Table
 *   columns={[
 *     { key: 'name', label: 'Name', sortable: true },
 *     { key: 'age', label: 'Age', sortable: true }
 *   ]}
 *   data={users}
 *   pagination
 *   pageSize={10}
 * />
 * ```
 */
export const Table = forwardRef(<T extends Record<string, any>>(
  {
    columns,
    data,
    striped = false,
    hoverable = true,
    bordered = true,
    pagination = false,
    pageSize = 10,
    currentPage: controlledPage,
    onPageChange,
    onSort,
    onRowClick,
    loading = false,
    emptyMessage = 'No data available',
    className = '',
    ...props
  }: TableProps<T>,
  ref: React.Ref<HTMLTableElement>
) => {
  const [internalPage, setInternalPage] = useState(1);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  const currentPage = controlledPage ?? internalPage;

  const handleSort = (key: string) => {
    const column = columns.find((col) => col.key === key);
    if (!column?.sortable) return;

    let newDirection: SortDirection = 'asc';
    if (sortKey === key) {
      if (sortDirection === 'asc') newDirection = 'desc';
      else if (sortDirection === 'desc') newDirection = null;
    }

    setSortKey(newDirection ? key : null);
    setSortDirection(newDirection);
    onSort?.(key, newDirection);
  };

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDirection) return data;

    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];

      if (aVal === bVal) return 0;

      const comparison = aVal > bVal ? 1 : -1;
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [data, sortKey, sortDirection]);

  const paginatedData = useMemo(() => {
    if (!pagination) return sortedData;

    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return sortedData.slice(start, end);
  }, [sortedData, pagination, currentPage, pageSize]);

  const totalPages = Math.ceil(data.length / pageSize);

  const handlePageChange = (page: number) => {
    setInternalPage(page);
    onPageChange?.(page);
  };

  const alignmentClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  const baseClasses = 'w-full text-sm';
  const borderClass = bordered ? 'border-collapse' : '';

  const tableClasses = [baseClasses, borderClass, className]
    .filter(Boolean)
    .join(' ');

  return (
    <div className="w-full">
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table ref={ref} className={tableClasses} {...props}>
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={`px-6 py-3 font-semibold text-gray-700 dark:text-gray-300 ${
                    alignmentClasses[column.align || 'left']
                  } ${bordered ? 'border-b border-gray-200 dark:border-gray-700' : ''}`}
                  style={{ width: column.width }}
                  onClick={() => column.sortable && handleSort(column.key)}
                  role={column.sortable ? 'button' : undefined}
                  aria-sort={
                    sortKey === column.key && sortDirection
                      ? sortDirection === 'asc'
                        ? 'ascending'
                        : 'descending'
                      : undefined
                  }
                  tabIndex={column.sortable ? 0 : undefined}
                  onKeyDown={(e) => {
                    if (column.sortable && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      handleSort(column.key);
                    }
                  }}
                >
                  <div className={`flex items-center ${column.align === 'right' ? 'justify-end' : column.align === 'center' ? 'justify-center' : ''}`}>
                    {column.label}
                    {column.sortable && (
                      <span className="ml-2" aria-hidden="true">
                        {sortKey === column.key ? (
                          sortDirection === 'asc' ? '↑' : '↓'
                        ) : (
                          <span className="text-gray-400">↕</span>
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-6 py-12 text-center text-gray-500 dark:text-gray-400"
                >
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                  </div>
                </td>
              </tr>
            ) : paginatedData.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-6 py-12 text-center text-gray-500 dark:text-gray-400"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paginatedData.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  className={`
                    ${striped && rowIndex % 2 === 1 ? 'bg-gray-50 dark:bg-gray-900' : ''}
                    ${hoverable ? 'hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150' : ''}
                    ${onRowClick ? 'cursor-pointer' : ''}
                  `}
                  onClick={() => onRowClick?.(row, rowIndex)}
                  role={onRowClick ? 'button' : undefined}
                  tabIndex={onRowClick ? 0 : undefined}
                  onKeyDown={(e) => {
                    if (onRowClick && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      onRowClick(row, rowIndex);
                    }
                  }}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={`px-6 py-4 text-gray-900 dark:text-gray-100 ${
                        alignmentClasses[column.align || 'left']
                      }`}
                    >
                      {column.render
                        ? column.render(row[column.key], row, rowIndex)
                        : row[column.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 rounded-b-lg">
          <div className="text-sm text-gray-700 dark:text-gray-300">
            Showing {(currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, data.length)} of {data.length} results
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Previous page"
            >
              Previous
            </button>
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}) as <T extends Record<string, any>>(
  props: TableProps<T> & { ref?: React.Ref<HTMLTableElement> }
) => JSX.Element;

Table.displayName = 'Table';
