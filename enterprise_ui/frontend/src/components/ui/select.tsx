import React, { SelectHTMLAttributes, forwardRef } from 'react';

/**
 * Select size types
 */
export type SelectSize = 'sm' | 'md' | 'lg';

/**
 * Select option interface
 */
export interface SelectOption {
  /**
   * Option value
   */
  value: string;

  /**
   * Option label
   */
  label: string;

  /**
   * Whether the option is disabled
   */
  disabled?: boolean;
}

/**
 * Select component props interface
 */
export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  /**
   * Size of the select
   * @default 'md'
   */
  selectSize?: SelectSize;

  /**
   * Label for the select
   */
  label?: string;

  /**
   * Error message to display
   */
  error?: string;

  /**
   * Helper text to display below select
   */
  helperText?: string;

  /**
   * Whether the select is in an error state
   * @default false
   */
  hasError?: boolean;

  /**
   * Options to display
   */
  options?: SelectOption[];

  /**
   * Placeholder text
   */
  placeholder?: string;

  /**
   * Full width select
   * @default false
   */
  fullWidth?: boolean;
}

const sizeClasses: Record<SelectSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-5 py-3 text-lg',
};

/**
 * Dropdown select component
 *
 * @example
 * ```tsx
 * <Select
 *   label="Country"
 *   options={[
 *     { value: 'us', label: 'United States' },
 *     { value: 'uk', label: 'United Kingdom' }
 *   ]}
 *   placeholder="Select a country"
 * />
 * ```
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      selectSize = 'md',
      label,
      error,
      helperText,
      hasError = false,
      options = [],
      placeholder,
      fullWidth = false,
      className = '',
      id,
      children,
      ...props
    },
    ref
  ) => {
    const selectId = id || `select-${Math.random().toString(36).substring(2, 9)}`;
    const isError = hasError || Boolean(error);

    const baseClasses = 'rounded-lg border transition-colors duration-200 focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed bg-white dark:bg-gray-800 appearance-none';

    const stateClasses = isError
      ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500'
      : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500';

    const textClasses = 'text-gray-900 dark:text-gray-100';
    const widthClass = fullWidth ? 'w-full' : '';

    const selectClasses = [
      baseClasses,
      stateClasses,
      textClasses,
      sizeClasses[selectSize],
      widthClass,
      'pr-10',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div className={fullWidth ? 'w-full' : ''}>
        {label && (
          <label
            htmlFor={selectId}
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            {label}
          </label>
        )}

        <div className="relative">
          <select
            ref={ref}
            id={selectId}
            className={selectClasses}
            aria-invalid={isError}
            aria-describedby={
              error ? `${selectId}-error` : helperText ? `${selectId}-helper` : undefined
            }
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}

            {options.map((option) => (
              <option
                key={option.value}
                value={option.value}
                disabled={option.disabled}
              >
                {option.label}
              </option>
            ))}

            {children}
          </select>

          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400 dark:text-gray-500">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
        </div>

        {error && (
          <p
            id={`${selectId}-error`}
            className="mt-1 text-sm text-red-600 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}

        {helperText && !error && (
          <p
            id={`${selectId}-helper`}
            className="mt-1 text-sm text-gray-500 dark:text-gray-400"
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';
