import React, { HTMLAttributes, forwardRef } from 'react';

/**
 * Card component props interface
 */
export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Whether the card has a border
   * @default true
   */
  bordered?: boolean;

  /**
   * Whether the card has a shadow
   * @default true
   */
  shadow?: boolean;

  /**
   * Whether the card is hoverable (shows hover effect)
   * @default false
   */
  hoverable?: boolean;
}

/**
 * Card header props interface
 */
export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Header title
   */
  title?: string;

  /**
   * Header action elements
   */
  actions?: React.ReactNode;
}

/**
 * Card body props interface
 */
export interface CardBodyProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Body padding
   * @default true
   */
  padding?: boolean;
}

/**
 * Card footer props interface
 */
export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Footer border top
   * @default true
   */
  bordered?: boolean;
}

/**
 * Card container component with header, body, and footer slots
 *
 * @example
 * ```tsx
 * <Card>
 *   <CardHeader title="Card Title" />
 *   <CardBody>Card content</CardBody>
 *   <CardFooter>Footer content</CardFooter>
 * </Card>
 * ```
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      bordered = true,
      shadow = true,
      hoverable = false,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = 'rounded-lg bg-white dark:bg-gray-800 transition-all duration-200';
    const borderClass = bordered ? 'border border-gray-200 dark:border-gray-700' : '';
    const shadowClass = shadow ? 'shadow-md' : '';
    const hoverClass = hoverable ? 'hover:shadow-lg hover:scale-[1.01]' : '';

    const cardClasses = [
      baseClasses,
      borderClass,
      shadowClass,
      hoverClass,
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div ref={ref} className={cardClasses} {...props}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

/**
 * Card header component
 */
export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ title, actions, className = '', children, ...props }, ref) => {
    const headerClasses = `px-6 py-4 border-b border-gray-200 dark:border-gray-700 ${className}`;

    return (
      <div ref={ref} className={headerClasses} {...props}>
        <div className="flex items-center justify-between">
          {title && (
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {title}
            </h3>
          )}
          {children}
          {actions && (
            <div className="flex items-center space-x-2">{actions}</div>
          )}
        </div>
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

/**
 * Card body component
 */
export const CardBody = forwardRef<HTMLDivElement, CardBodyProps>(
  ({ padding = true, className = '', children, ...props }, ref) => {
    const paddingClass = padding ? 'px-6 py-4' : '';
    const bodyClasses = `${paddingClass} ${className}`.trim();

    return (
      <div ref={ref} className={bodyClasses} {...props}>
        {children}
      </div>
    );
  }
);

CardBody.displayName = 'CardBody';

/**
 * Card footer component
 */
export const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({ bordered = true, className = '', children, ...props }, ref) => {
    const borderClass = bordered ? 'border-t border-gray-200 dark:border-gray-700' : '';
    const footerClasses = `px-6 py-4 ${borderClass} ${className}`.trim();

    return (
      <div ref={ref} className={footerClasses} {...props}>
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';
