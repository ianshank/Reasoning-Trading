import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { Table } from '../../../src/components/ui/table';
import type { TableColumn } from '../../../src/components/ui/table';

interface TestData {
  id: number;
  name: string;
  age: number;
  email: string;
}

const mockData: TestData[] = [
  { id: 1, name: 'John Doe', age: 30, email: 'john@example.com' },
  { id: 2, name: 'Jane Smith', age: 25, email: 'jane@example.com' },
  { id: 3, name: 'Bob Johnson', age: 35, email: 'bob@example.com' },
];

const mockColumns: TableColumn<TestData>[] = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'age', label: 'Age', sortable: true },
  { key: 'email', label: 'Email' },
];

describe('Table', () => {
  describe('Rendering', () => {
    it('should render table with data', () => {
      render(<Table columns={mockColumns} data={mockData} />);

      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('Bob Johnson')).toBeInTheDocument();
    });

    it('should render column headers', () => {
      render(<Table columns={mockColumns} data={mockData} />);

      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Age')).toBeInTheDocument();
      expect(screen.getByText('Email')).toBeInTheDocument();
    });

    it('should render empty message when no data', () => {
      render(<Table columns={mockColumns} data={[]} emptyMessage="No data found" />);

      expect(screen.getByText('No data found')).toBeInTheDocument();
    });

    it('should render loading state', () => {
      render(<Table columns={mockColumns} data={[]} loading />);

      const loadingElement = screen.getByRole('row', { name: '' });
      expect(loadingElement).toBeInTheDocument();
    });
  });

  describe('Sorting', () => {
    it('should show sort indicators for sortable columns', () => {
      render(<Table columns={mockColumns} data={mockData} />);

      const nameHeader = screen.getByRole('button', { name: /name/i });
      const ageHeader = screen.getByRole('button', { name: /age/i });

      expect(nameHeader).toBeInTheDocument();
      expect(ageHeader).toBeInTheDocument();
    });

    it('should sort data ascending when clicking sortable column', () => {
      render(<Table columns={mockColumns} data={mockData} />);

      const nameHeader = screen.getByRole('button', { name: /name/i });
      fireEvent.click(nameHeader);

      const rows = screen.getAllByRole('row').slice(1);
      expect(within(rows[0]).getByText('Bob Johnson')).toBeInTheDocument();
      expect(within(rows[1]).getByText('Jane Smith')).toBeInTheDocument();
      expect(within(rows[2]).getByText('John Doe')).toBeInTheDocument();
    });

    it('should sort data descending when clicking sorted column again', () => {
      render(<Table columns={mockColumns} data={mockData} />);

      const nameHeader = screen.getByRole('button', { name: /name/i });
      fireEvent.click(nameHeader);
      fireEvent.click(nameHeader);

      const rows = screen.getAllByRole('row').slice(1);
      expect(within(rows[0]).getByText('John Doe')).toBeInTheDocument();
      expect(within(rows[1]).getByText('Jane Smith')).toBeInTheDocument();
      expect(within(rows[2]).getByText('Bob Johnson')).toBeInTheDocument();
    });

    it('should call onSort callback when sorting', () => {
      const handleSort = jest.fn();
      render(<Table columns={mockColumns} data={mockData} onSort={handleSort} />);

      const nameHeader = screen.getByRole('button', { name: /name/i });
      fireEvent.click(nameHeader);

      expect(handleSort).toHaveBeenCalledWith('name', 'asc');
    });

    it('should update aria-sort attribute', () => {
      render(<Table columns={mockColumns} data={mockData} />);

      const nameHeader = screen.getByRole('button', { name: /name/i });
      fireEvent.click(nameHeader);

      expect(nameHeader).toHaveAttribute('aria-sort', 'ascending');
    });
  });

  describe('Pagination', () => {
    const largeMockData = Array.from({ length: 25 }, (_, i) => ({
      id: i + 1,
      name: `User ${i + 1}`,
      age: 20 + i,
      email: `user${i + 1}@example.com`,
    }));

    it('should render pagination controls', () => {
      render(<Table columns={mockColumns} data={largeMockData} pagination pageSize={10} />);

      expect(screen.getByLabelText('Previous page')).toBeInTheDocument();
      expect(screen.getByLabelText('Next page')).toBeInTheDocument();
    });

    it('should display correct page info', () => {
      render(<Table columns={mockColumns} data={largeMockData} pagination pageSize={10} />);

      expect(screen.getByText(/Showing 1 to 10 of 25 results/)).toBeInTheDocument();
    });

    it('should navigate to next page', () => {
      render(<Table columns={mockColumns} data={largeMockData} pagination pageSize={10} />);

      const nextButton = screen.getByLabelText('Next page');
      fireEvent.click(nextButton);

      expect(screen.getByText(/Showing 11 to 20 of 25 results/)).toBeInTheDocument();
    });

    it('should navigate to previous page', () => {
      render(<Table columns={mockColumns} data={largeMockData} pagination pageSize={10} />);

      const nextButton = screen.getByLabelText('Next page');
      const prevButton = screen.getByLabelText('Previous page');

      fireEvent.click(nextButton);
      fireEvent.click(prevButton);

      expect(screen.getByText(/Showing 1 to 10 of 25 results/)).toBeInTheDocument();
    });

    it('should disable previous button on first page', () => {
      render(<Table columns={mockColumns} data={largeMockData} pagination pageSize={10} />);

      const prevButton = screen.getByLabelText('Previous page');
      expect(prevButton).toBeDisabled();
    });

    it('should disable next button on last page', () => {
      render(<Table columns={mockColumns} data={largeMockData} pagination pageSize={10} />);

      const nextButton = screen.getByLabelText('Next page');
      fireEvent.click(nextButton);
      fireEvent.click(nextButton);

      expect(nextButton).toBeDisabled();
    });

    it('should call onPageChange callback', () => {
      const handlePageChange = jest.fn();
      render(
        <Table
          columns={mockColumns}
          data={largeMockData}
          pagination
          pageSize={10}
          onPageChange={handlePageChange}
        />
      );

      const nextButton = screen.getByLabelText('Next page');
      fireEvent.click(nextButton);

      expect(handlePageChange).toHaveBeenCalledWith(2);
    });
  });

  describe('Custom rendering', () => {
    it('should use custom render function for cells', () => {
      const customColumns: TableColumn<TestData>[] = [
        {
          key: 'name',
          label: 'Name',
          render: (value) => <strong>{value}</strong>,
        },
      ];

      render(<Table columns={customColumns} data={mockData} />);

      expect(screen.getByText('John Doe').tagName).toBe('STRONG');
    });

    it('should apply custom column alignment', () => {
      const alignedColumns: TableColumn<TestData>[] = [
        { key: 'name', label: 'Name', align: 'left' },
        { key: 'age', label: 'Age', align: 'center' },
        { key: 'email', label: 'Email', align: 'right' },
      ];

      const { container } = render(<Table columns={alignedColumns} data={mockData} />);

      const headers = container.querySelectorAll('th');
      expect(headers[0]).toHaveClass('text-left');
      expect(headers[1]).toHaveClass('text-center');
      expect(headers[2]).toHaveClass('text-right');
    });
  });

  describe('Row interactions', () => {
    it('should call onRowClick when row is clicked', () => {
      const handleRowClick = jest.fn();
      render(<Table columns={mockColumns} data={mockData} onRowClick={handleRowClick} />);

      const rows = screen.getAllByRole('row').slice(1);
      fireEvent.click(rows[0]);

      expect(handleRowClick).toHaveBeenCalledWith(mockData[0], 0);
    });

    it('should apply hover styles when hoverable is true', () => {
      const { container } = render(<Table columns={mockColumns} data={mockData} hoverable />);

      const rows = container.querySelectorAll('tbody tr');
      expect(rows[0]).toHaveClass('hover:bg-gray-100');
    });

    it('should apply striped styles when striped is true', () => {
      const { container } = render(<Table columns={mockColumns} data={mockData} striped />);

      const rows = container.querySelectorAll('tbody tr');
      expect(rows[1]).toHaveClass('bg-gray-50');
    });
  });

  describe('Accessibility', () => {
    it('should have proper table structure', () => {
      render(<Table columns={mockColumns} data={mockData} />);

      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
    });

    it('should have proper ARIA attributes for sortable columns', () => {
      render(<Table columns={mockColumns} data={mockData} />);

      const nameHeader = screen.getByRole('button', { name: /name/i });
      expect(nameHeader).toHaveAttribute('role', 'button');
      expect(nameHeader).toHaveAttribute('tabIndex', '0');
    });

    it('should support keyboard navigation for sorting', () => {
      render(<Table columns={mockColumns} data={mockData} />);

      const nameHeader = screen.getByRole('button', { name: /name/i });
      fireEvent.keyDown(nameHeader, { key: 'Enter' });

      expect(nameHeader).toHaveAttribute('aria-sort', 'ascending');
    });

    it('should support keyboard navigation for row clicks', () => {
      const handleRowClick = jest.fn();
      render(<Table columns={mockColumns} data={mockData} onRowClick={handleRowClick} />);

      const rows = screen.getAllByRole('row').slice(1);
      fireEvent.keyDown(rows[0], { key: 'Enter' });

      expect(handleRowClick).toHaveBeenCalledWith(mockData[0], 0);
    });
  });

  describe('Ref forwarding', () => {
    it('should forward ref to table element', () => {
      const ref = React.createRef<HTMLTableElement>();
      render(<Table ref={ref} columns={mockColumns} data={mockData} />);

      expect(ref.current).toBeInstanceOf(HTMLTableElement);
      expect(ref.current?.tagName).toBe('TABLE');
    });
  });
});
