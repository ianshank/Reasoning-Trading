import React, { HTMLAttributes, forwardRef } from 'react';

/**
 * Spinner size types
 */
export type SpinnerSize = 'sm' | 'md' | 'lg' | 'xl';

/**
 * Spinner variant types
 */
export type SpinnerVariant = 'spinner' | 'dots' | 'pulse';

/**
 * Spinner component props interface
 */
export interface SpinnerProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Size of the spinner
   * @default 'md'
   */
  size?: SpinnerSize;

  /**
   * Variant of the spinner
   * @default 'spinner'
   */
  variant?: SpinnerVariant;

  /**
   * Color of the spinner
   * @default 'blue'
   */
  color?: string;

  /**
   * Loading text to display
   */
  label?: string;

  /**
   * Whether to center the spinner
   * @default false
   */
  centered?: boolean;
}

const sizeClasses: Record<SpinnerSize, string> = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
  xl: 'w-16 h-16',
};

const dotSizeClasses: Record<SpinnerSize, string> = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2.5 h-2.5',
  lg: 'w-3.5 h-3.5',
  xl: 'w-5 h-5',
};

/**
 * Loading spinner component
 *
 * @example
 * ```tsx
 * <Spinner size="lg" label="Loading..." />
 * ```
 */
export const Spinner = forwardRef<HTMLDivElement, SpinnerProps>(
  (
    {
      size = 'md',
      variant = 'spinner',
      color = 'blue',
      label,
      centered = false,
      className = '',
      ...props
    },
    ref
  ) => {
    const containerClasses = centered
      ? 'flex items-center justify-center'
      : 'inline-flex items-center';

    const renderSpinner = () => {
      switch (variant) {
        case 'dots':
          return (
            <div className="flex space-x-1" aria-hidden="true">
              <div
                className={`${dotSizeClasses[size]} bg-${color}-600 dark:bg-${color}-400 rounded-full animate-bounce`}
                style={{ animationDelay: '0ms' }}
              />
              <div
                className={`${dotSizeClasses[size]} bg-${color}-600 dark:bg-${color}-400 rounded-full animate-bounce`}
                style={{ animationDelay: '150ms' }}
              />
              <div
                className={`${dotSizeClasses[size]} bg-${color}-600 dark:bg-${color}-400 rounded-full animate-bounce`}
                style={{ animationDelay: '300ms' }}
              />
            </div>
          );

        case 'pulse':
          return (
            <div
              className={`${sizeClasses[size]} bg-${color}-600 dark:bg-${color}-400 rounded-full animate-pulse`}
              aria-hidden="true"
            />
          );

        case 'spinner':
        default:
          return (
            <svg
              className={`${sizeClasses[size]} animate-spin text-${color}-600 dark:text-${color}-400`}
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          );
      }
    };

    return (
      <div
        ref={ref}
        className={`${containerClasses} ${className}`}
        role="status"
        aria-live="polite"
        aria-busy="true"
        {...props}
      >
        {renderSpinner()}
        {label && (
          <span className="ml-3 text-sm font-medium text-gray-700 dark:text-gray-300">
            {label}
          </span>
        )}
        <span className="sr-only">{label || 'Loading...'}</span>
      </div>
    );
  }
);

Spinner.displayName = 'Spinner';
