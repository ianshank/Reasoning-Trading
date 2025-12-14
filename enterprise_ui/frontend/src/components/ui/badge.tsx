import React, { HTMLAttributes, forwardRef } from 'react';

/**
 * Badge color variants
 */
export type BadgeVariant =
  | 'default'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'primary'
  | 'secondary';

/**
 * Badge size types
 */
export type BadgeSize = 'sm' | 'md' | 'lg';

/**
 * Badge component props interface
 */
export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  /**
   * Color variant of the badge
   * @default 'default'
   */
  variant?: BadgeVariant;

  /**
   * Size of the badge
   * @default 'md'
   */
  size?: BadgeSize;

  /**
   * Whether the badge has a dot indicator
   * @default false
   */
  dot?: boolean;

  /**
   * Whether the badge is outlined (not filled)
   * @default false
   */
  outlined?: boolean;
}

const variantClasses: Record<BadgeVariant, { filled: string; outlined: string }> = {
  default: {
    filled: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    outlined: 'border-gray-300 text-gray-700 dark:border-gray-600 dark:text-gray-400',
  },
  primary: {
    filled: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    outlined: 'border-blue-300 text-blue-700 dark:border-blue-600 dark:text-blue-400',
  },
  secondary: {
    filled: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    outlined: 'border-gray-300 text-gray-700 dark:border-gray-600 dark:text-gray-400',
  },
  success: {
    filled: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    outlined: 'border-green-300 text-green-700 dark:border-green-600 dark:text-green-400',
  },
  warning: {
    filled: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
    outlined: 'border-yellow-300 text-yellow-700 dark:border-yellow-600 dark:text-yellow-400',
  },
  danger: {
    filled: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    outlined: 'border-red-300 text-red-700 dark:border-red-600 dark:text-red-400',
  },
  info: {
    filled: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-300',
    outlined: 'border-cyan-300 text-cyan-700 dark:border-cyan-600 dark:text-cyan-400',
  },
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

const dotSizeClasses: Record<BadgeSize, string> = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-2.5 h-2.5',
};

/**
 * Badge component for displaying status indicators and labels
 *
 * @example
 * ```tsx
 * <Badge variant="success">Active</Badge>
 * <Badge variant="danger" dot>Error</Badge>
 * ```
 */
export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      variant = 'default',
      size = 'md',
      dot = false,
      outlined = false,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = 'inline-flex items-center font-medium rounded-full';
    const variantClass = outlined
      ? `border ${variantClasses[variant].outlined}`
      : variantClasses[variant].filled;

    const badgeClasses = [
      baseClasses,
      variantClass,
      sizeClasses[size],
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <span
        ref={ref}
        className={badgeClasses}
        role="status"
        aria-label={typeof children === 'string' ? children : undefined}
        {...props}
      >
        {dot && (
          <span
            className={`${dotSizeClasses[size]} rounded-full bg-current mr-1.5`}
            aria-hidden="true"
          />
        )}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';
