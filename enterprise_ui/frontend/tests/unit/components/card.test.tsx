import React from 'react';
import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardBody, CardFooter } from '../../../src/components/ui/card';

describe('Card', () => {
  describe('Card component', () => {
    it('should render card with children', () => {
      render(<Card>Card content</Card>);
      expect(screen.getByText('Card content')).toBeInTheDocument();
    });

    it('should render with border by default', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass('border');
    });

    it('should render without border when bordered is false', () => {
      const { container } = render(<Card bordered={false}>Content</Card>);
      const card = container.firstChild as HTMLElement;
      expect(card).not.toHaveClass('border');
    });

    it('should render with shadow by default', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass('shadow-md');
    });

    it('should render without shadow when shadow is false', () => {
      const { container } = render(<Card shadow={false}>Content</Card>);
      const card = container.firstChild as HTMLElement;
      expect(card).not.toHaveClass('shadow-md');
    });

    it('should render with hover effect when hoverable is true', () => {
      const { container } = render(<Card hoverable>Content</Card>);
      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass('hover:shadow-lg', 'hover:scale-[1.01]');
    });

    it('should render with custom className', () => {
      const { container } = render(<Card className="custom-class">Content</Card>);
      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass('custom-class');
    });
  });

  describe('CardHeader component', () => {
    it('should render header with title', () => {
      render(<CardHeader title="Test Title" />);
      expect(screen.getByText('Test Title')).toBeInTheDocument();
    });

    it('should render header with children', () => {
      render(
        <CardHeader>
          <span>Custom header content</span>
        </CardHeader>
      );
      expect(screen.getByText('Custom header content')).toBeInTheDocument();
    });

    it('should render header with actions', () => {
      render(
        <CardHeader
          title="Title"
          actions={<button>Action</button>}
        />
      );
      expect(screen.getByRole('button', { name: /action/i })).toBeInTheDocument();
    });

    it('should have border bottom by default', () => {
      const { container } = render(<CardHeader title="Title" />);
      const header = container.firstChild as HTMLElement;
      expect(header).toHaveClass('border-b');
    });
  });

  describe('CardBody component', () => {
    it('should render body with children', () => {
      render(<CardBody>Body content</CardBody>);
      expect(screen.getByText('Body content')).toBeInTheDocument();
    });

    it('should have padding by default', () => {
      const { container } = render(<CardBody>Content</CardBody>);
      const body = container.firstChild as HTMLElement;
      expect(body).toHaveClass('px-6', 'py-4');
    });

    it('should render without padding when padding is false', () => {
      const { container } = render(<CardBody padding={false}>Content</CardBody>);
      const body = container.firstChild as HTMLElement;
      expect(body).not.toHaveClass('px-6', 'py-4');
    });
  });

  describe('CardFooter component', () => {
    it('should render footer with children', () => {
      render(<CardFooter>Footer content</CardFooter>);
      expect(screen.getByText('Footer content')).toBeInTheDocument();
    });

    it('should have border top by default', () => {
      const { container } = render(<CardFooter>Footer</CardFooter>);
      const footer = container.firstChild as HTMLElement;
      expect(footer).toHaveClass('border-t');
    });

    it('should render without border when bordered is false', () => {
      const { container } = render(<CardFooter bordered={false}>Footer</CardFooter>);
      const footer = container.firstChild as HTMLElement;
      expect(footer).not.toHaveClass('border-t');
    });
  });

  describe('Composed Card', () => {
    it('should render complete card with all sections', () => {
      render(
        <Card>
          <CardHeader title="Card Title" />
          <CardBody>Card body content</CardBody>
          <CardFooter>Card footer content</CardFooter>
        </Card>
      );

      expect(screen.getByText('Card Title')).toBeInTheDocument();
      expect(screen.getByText('Card body content')).toBeInTheDocument();
      expect(screen.getByText('Card footer content')).toBeInTheDocument();
    });

    it('should render card with only header and body', () => {
      render(
        <Card>
          <CardHeader title="Title" />
          <CardBody>Content</CardBody>
        </Card>
      );

      expect(screen.getByText('Title')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
    });
  });

  describe('Ref forwarding', () => {
    it('should forward ref to card element', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<Card ref={ref}>Content</Card>);

      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });

    it('should forward ref to card header element', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<CardHeader ref={ref} title="Title" />);

      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });

    it('should forward ref to card body element', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<CardBody ref={ref}>Content</CardBody>);

      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });

    it('should forward ref to card footer element', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<CardFooter ref={ref}>Footer</CardFooter>);

      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });
  });
});
