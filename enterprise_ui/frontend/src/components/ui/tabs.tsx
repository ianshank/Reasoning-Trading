import React, { HTMLAttributes, useState, createContext, useContext } from 'react';

/**
 * Tab item interface
 */
export interface TabItem {
  /**
   * Unique tab key
   */
  key: string;

  /**
   * Tab label
   */
  label: string;

  /**
   * Tab content
   */
  content: React.ReactNode;

  /**
   * Whether the tab is disabled
   */
  disabled?: boolean;

  /**
   * Icon to display before label
   */
  icon?: React.ReactNode;
}

/**
 * Tabs component props interface
 */
export interface TabsProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onChange'> {
  /**
   * Tab items
   */
  items?: TabItem[];

  /**
   * Active tab key (controlled)
   */
  activeKey?: string;

  /**
   * Default active tab key
   * @default first tab key
   */
  defaultActiveKey?: string;

  /**
   * Tab change handler
   */
  onChange?: (key: string) => void;

  /**
   * Tab variant
   * @default 'line'
   */
  variant?: 'line' | 'pills';

  /**
   * Full width tabs
   * @default false
   */
  fullWidth?: boolean;
}

/**
 * Tab panel props interface
 */
export interface TabPanelProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Tab key
   */
  value: string;

  /**
   * Tab label
   */
  label: string;

  /**
   * Whether the tab is disabled
   */
  disabled?: boolean;

  /**
   * Icon to display before label
   */
  icon?: React.ReactNode;
}

interface TabsContextValue {
  activeKey: string;
  setActiveKey: (key: string) => void;
  variant: 'line' | 'pills';
}

const TabsContext = createContext<TabsContextValue | null>(null);

const useTabsContext = () => {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('Tab components must be used within Tabs');
  }
  return context;
};

/**
 * Tab navigation component
 *
 * @example
 * ```tsx
 * <Tabs
 *   items={[
 *     { key: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
 *     { key: 'tab2', label: 'Tab 2', content: <div>Content 2</div> }
 *   ]}
 *   defaultActiveKey="tab1"
 * />
 * ```
 */
export const Tabs: React.FC<TabsProps> = ({
  items = [],
  activeKey: controlledActiveKey,
  defaultActiveKey,
  onChange,
  variant = 'line',
  fullWidth = false,
  className = '',
  children,
  ...props
}) => {
  const [internalActiveKey, setInternalActiveKey] = useState(
    defaultActiveKey || items[0]?.key || ''
  );

  const activeKey = controlledActiveKey ?? internalActiveKey;

  const handleTabChange = (key: string) => {
    setInternalActiveKey(key);
    onChange?.(key);
  };

  const contextValue: TabsContextValue = {
    activeKey,
    setActiveKey: handleTabChange,
    variant,
  };

  return (
    <TabsContext.Provider value={contextValue}>
      <div className={className} {...props}>
        {items.length > 0 ? (
          <>
            <TabList fullWidth={fullWidth}>
              {items.map((item) => (
                <Tab
                  key={item.key}
                  value={item.key}
                  disabled={item.disabled}
                  icon={item.icon}
                >
                  {item.label}
                </Tab>
              ))}
            </TabList>
            <div className="mt-4">
              {items.map((item) => (
                <TabPanel key={item.key} value={item.key}>
                  {item.content}
                </TabPanel>
              ))}
            </div>
          </>
        ) : (
          children
        )}
      </div>
    </TabsContext.Provider>
  );
};

/**
 * Tab list component
 */
export const TabList: React.FC<
  HTMLAttributes<HTMLDivElement> & { fullWidth?: boolean }
> = ({ fullWidth = false, className = '', children, ...props }) => {
  const { variant } = useTabsContext();

  const baseClasses = 'flex';
  const variantClasses =
    variant === 'line'
      ? 'border-b border-gray-200 dark:border-gray-700'
      : 'p-1 bg-gray-100 dark:bg-gray-800 rounded-lg';
  const widthClass = fullWidth ? 'w-full' : '';

  const listClasses = [baseClasses, variantClasses, widthClass, className]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={listClasses} role="tablist" {...props}>
      {children}
    </div>
  );
};

/**
 * Tab button component
 */
export const Tab: React.FC<
  Omit<TabPanelProps, 'children'> & { children: React.ReactNode }
> = ({ value, disabled = false, icon, className = '', children, ...props }) => {
  const { activeKey, setActiveKey, variant } = useTabsContext();
  const isActive = activeKey === value;

  const handleClick = () => {
    if (!disabled) {
      setActiveKey(value);
    }
  };

  const baseClasses =
    'flex items-center justify-center px-4 py-2 font-medium text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2';

  const variantClasses =
    variant === 'line'
      ? isActive
        ? 'border-b-2 border-blue-600 text-blue-600 dark:text-blue-400'
        : 'border-b-2 border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
      : isActive
      ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md shadow-sm'
      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200';

  const disabledClasses = disabled
    ? 'opacity-50 cursor-not-allowed'
    : 'cursor-pointer';

  const tabClasses = [baseClasses, variantClasses, disabledClasses, className]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      role="tab"
      aria-selected={isActive}
      aria-controls={`tabpanel-${value}`}
      id={`tab-${value}`}
      className={tabClasses}
      onClick={handleClick}
      disabled={disabled}
      tabIndex={isActive ? 0 : -1}
      {...props}
    >
      {icon && <span className="mr-2">{icon}</span>}
      {children}
    </button>
  );
};

/**
 * Tab panel component
 */
export const TabPanel: React.FC<TabPanelProps> = ({
  value,
  className = '',
  children,
  ...props
}) => {
  const { activeKey } = useTabsContext();
  const isActive = activeKey === value;

  if (!isActive) return null;

  return (
    <div
      role="tabpanel"
      id={`tabpanel-${value}`}
      aria-labelledby={`tab-${value}`}
      className={className}
      {...props}
    >
      {children}
    </div>
  );
};

Tabs.displayName = 'Tabs';
TabList.displayName = 'TabList';
Tab.displayName = 'Tab';
TabPanel.displayName = 'TabPanel';
