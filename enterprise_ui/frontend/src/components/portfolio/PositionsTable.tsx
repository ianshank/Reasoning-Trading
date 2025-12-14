/**
 * Positions Table Component
 *
 * Displays all open positions in a sortable data table
 */

import React, { useState, useMemo } from 'react';
import type { Position } from '../../types/portfolio';
import { Table } from '../ui/Table';
import { Button } from '../ui/Button';

interface PositionsTableProps {
  positions: Position[];
  onClosePosition?: (positionId: string) => void;
  onModifyPosition?: (positionId: string) => void;
}

type SortField =
  | 'symbol'
  | 'quantity'
  | 'entry_price'
  | 'current_price'
  | 'unrealized_pnl'
  | 'unrealized_pnl_pct'
  | 'time_held';

type SortDirection = 'asc' | 'desc';

export const PositionsTable: React.FC<PositionsTableProps> = ({
  positions,
  onClosePosition,
  onModifyPosition,
}) => {
  const [sortField, setSortField] = useState<SortField>('unrealized_pnl_pct');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const calculateTimeHeld = (entryTime: string): string => {
    const entry = new Date(entryTime);
    const now = new Date();
    const diffMs = now.getTime() - entry.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) {
      return `${diffDays}d ${diffHours % 24}h`;
    }
    return `${diffHours}h`;
  };

  const sortedPositions = useMemo(() => {
    return [...positions].sort((a, b) => {
      let aValue: number | string;
      let bValue: number | string;

      switch (sortField) {
        case 'symbol':
          aValue = a.symbol;
          bValue = b.symbol;
          break;
        case 'quantity':
          aValue = a.quantity;
          bValue = b.quantity;
          break;
        case 'entry_price':
          aValue = a.entry_price;
          bValue = b.entry_price;
          break;
        case 'current_price':
          aValue = a.current_price;
          bValue = b.current_price;
          break;
        case 'unrealized_pnl':
          aValue = a.unrealized_pnl;
          bValue = b.unrealized_pnl;
          break;
        case 'unrealized_pnl_pct':
          aValue = a.unrealized_pnl_pct;
          bValue = b.unrealized_pnl_pct;
          break;
        case 'time_held':
          aValue = new Date(a.entry_time).getTime();
          bValue = new Date(b.entry_time).getTime();
          break;
        default:
          return 0;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }

      return 0;
    });
  }, [positions, sortField, sortDirection]);

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getPnLColorClass = (value: number): string => {
    if (value > 0) return 'text-green-600 dark:text-green-400';
    if (value < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const SortIcon: React.FC<{ field: SortField }> = ({ field }) => {
    if (sortField !== field) {
      return (
        <span className="ml-1 text-gray-400" aria-hidden="true">
          ⇅
        </span>
      );
    }
    return (
      <span className="ml-1" aria-hidden="true">
        {sortDirection === 'asc' ? '↑' : '↓'}
      </span>
    );
  };

  if (positions.length === 0) {
    return (
      <div
        className="bg-white dark:bg-gray-800 rounded-lg p-8 text-center"
        role="status"
      >
        <p className="text-gray-500 dark:text-gray-400">No open positions</p>
      </div>
    );
  }

  const columns = [
    {
      header: (
        <button
          onClick={() => handleSort('symbol')}
          className="flex items-center font-semibold hover:text-blue-600 dark:hover:text-blue-400"
          aria-label="Sort by symbol"
        >
          Symbol
          <SortIcon field="symbol" />
        </button>
      ),
      accessorKey: 'symbol',
      cell: (position: Position) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-white">
            {position.symbol}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {position.side.toUpperCase()}
          </div>
        </div>
      ),
    },
    {
      header: (
        <button
          onClick={() => handleSort('quantity')}
          className="flex items-center font-semibold hover:text-blue-600 dark:hover:text-blue-400"
          aria-label="Sort by quantity"
        >
          Quantity
          <SortIcon field="quantity" />
        </button>
      ),
      accessorKey: 'quantity',
      cell: (position: Position) => (
        <span className="text-gray-900 dark:text-white">
          {position.quantity.toLocaleString()}
        </span>
      ),
    },
    {
      header: (
        <button
          onClick={() => handleSort('entry_price')}
          className="flex items-center font-semibold hover:text-blue-600 dark:hover:text-blue-400"
          aria-label="Sort by entry price"
        >
          Entry Price
          <SortIcon field="entry_price" />
        </button>
      ),
      accessorKey: 'entry_price',
      cell: (position: Position) => (
        <span className="text-gray-900 dark:text-white">
          {formatCurrency(position.entry_price)}
        </span>
      ),
    },
    {
      header: (
        <button
          onClick={() => handleSort('current_price')}
          className="flex items-center font-semibold hover:text-blue-600 dark:hover:text-blue-400"
          aria-label="Sort by current price"
        >
          Current Price
          <SortIcon field="current_price" />
        </button>
      ),
      accessorKey: 'current_price',
      cell: (position: Position) => (
        <span className="text-gray-900 dark:text-white">
          {formatCurrency(position.current_price)}
        </span>
      ),
    },
    {
      header: (
        <button
          onClick={() => handleSort('unrealized_pnl')}
          className="flex items-center font-semibold hover:text-blue-600 dark:hover:text-blue-400"
          aria-label="Sort by profit and loss"
        >
          P&L
          <SortIcon field="unrealized_pnl" />
        </button>
      ),
      accessorKey: 'unrealized_pnl',
      cell: (position: Position) => (
        <div>
          <div className={`font-medium ${getPnLColorClass(position.unrealized_pnl)}`}>
            {formatCurrency(position.unrealized_pnl)}
          </div>
          <div className={`text-sm ${getPnLColorClass(position.unrealized_pnl_pct)}`}>
            {formatPercent(position.unrealized_pnl_pct)}
          </div>
        </div>
      ),
    },
    {
      header: <span className="font-semibold">Stop Loss / Take Profit</span>,
      accessorKey: 'stop_loss',
      cell: (position: Position) => (
        <div className="text-sm">
          {position.stop_loss_price && (
            <div className="text-red-600 dark:text-red-400">
              SL: {formatCurrency(position.stop_loss_price)}
            </div>
          )}
          {position.take_profit_price && (
            <div className="text-green-600 dark:text-green-400">
              TP: {formatCurrency(position.take_profit_price)}
            </div>
          )}
          {!position.stop_loss_price && !position.take_profit_price && (
            <span className="text-gray-400">-</span>
          )}
        </div>
      ),
    },
    {
      header: (
        <button
          onClick={() => handleSort('time_held')}
          className="flex items-center font-semibold hover:text-blue-600 dark:hover:text-blue-400"
          aria-label="Sort by time held"
        >
          Time Held
          <SortIcon field="time_held" />
        </button>
      ),
      accessorKey: 'entry_time',
      cell: (position: Position) => (
        <span className="text-gray-600 dark:text-gray-400">
          {calculateTimeHeld(position.entry_time)}
        </span>
      ),
    },
    {
      header: <span className="font-semibold">Actions</span>,
      accessorKey: 'actions',
      cell: (position: Position) => (
        <div className="flex gap-2">
          {onModifyPosition && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onModifyPosition(position.position_id)}
              aria-label={`Modify position ${position.symbol}`}
            >
              Modify
            </Button>
          )}
          {onClosePosition && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onClosePosition(position.position_id)}
              className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              aria-label={`Close position ${position.symbol}`}
            >
              Close
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
      <Table
        data={sortedPositions}
        columns={columns}
        aria-label="Open positions table"
      />
    </div>
  );
};
