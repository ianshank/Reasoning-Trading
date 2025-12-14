import React, { HTMLAttributes, forwardRef } from 'react';

/**
 * Progress size types
 */
export type ProgressSize = 'sm' | 'md' | 'lg';

/**
 * Progress variant types
 */
export type ProgressVariant = 'default' | 'success' | 'warning' | 'danger';

/**
 * Progress component props interface
 */
export interface ProgressProps extends Omit<HTMLAttributes<HTMLDivElement>, 'color'> {
  /**
   * Current progress value (0-100)
   */
  value: number;

  /**
   * Maximum value
   * @default 100
   */
  max?: number;

  /**
   * Size of the progress bar
   * @default 'md'
   */
  size?: ProgressSize;

  /**
   * Variant of the progress bar
   * @default 'default'
   */
  variant?: ProgressVariant;

  /**
   * Whether to show percentage label
   * @default false
   */
  showLabel?: boolean;

  /**
   * Custom label text
   */
  label?: string;

  /**
   * Whether to show striped animation
   * @default false
   */
  striped?: boolean;

  /**
   * Whether the progress bar is animated
   * @default false
   */
  animated?: boolean;
}

const sizeClasses: Record<ProgressSize, string> = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
};

const variantClasses: Record<ProgressVariant, string> = {
  default: 'bg-blue-600 dark:bg-blue-500',
  success: 'bg-green-600 dark:bg-green-500',
  warning: 'bg-yellow-600 dark:bg-yellow-500',
  danger: 'bg-red-600 dark:bg-red-500',
};

/**
 * Progress bar component
 *
 * @example
 * ```tsx
 * <Progress value={75} showLabel />
 * <Progress value={50} variant="success" striped animated />
 * ```
 */
export const Progress = forwardRef<HTMLDivElement, ProgressProps>(
  (
    {
      value,
      max = 100,
      size = 'md',
      variant = 'default',
      showLabel = false,
      label,
      striped = false,
      animated = false,
      className = '',
      ...props
    },
    ref
  ) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
    const displayLabel = label || `${Math.round(percentage)}%`;

    const stripedClass = striped
      ? 'bg-gradient-to-r from-transparent via-white/20 to-transparent bg-[length:1rem_100%]'
      : '';

    const animatedClass = animated && striped ? 'animate-progress-stripes' : '';

    return (
      <div ref={ref} className={className} {...props}>
        {showLabel && (
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {displayLabel}
            </span>
          </div>
        )}

        <div
          className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden ${sizeClasses[size]}`}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-label={label || `Progress: ${percentage}%`}
        >
          <div
            className={`h-full transition-all duration-300 ease-out rounded-full ${variantClasses[variant]} ${stripedClass} ${animatedClass}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    );
  }
);

Progress.displayName = 'Progress';
