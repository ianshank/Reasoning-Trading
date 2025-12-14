import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Theme = 'light' | 'dark'

export interface UserPreferences {
  defaultSymbol: string
  refreshInterval: number
  chartType: 'candlestick' | 'line' | 'bar'
  showNotifications: boolean
  soundEnabled: boolean
}

export interface AppState {
  // Theme
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void

  // Sidebar
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void

  // Current symbol
  currentSymbol: string
  setCurrentSymbol: (symbol: string) => void

  // User preferences
  preferences: UserPreferences
  updatePreferences: (preferences: Partial<UserPreferences>) => void

  // Notifications
  notifications: Notification[]
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void

  // Connection status
  isConnected: boolean
  setIsConnected: (connected: boolean) => void

  // Loading states
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
}

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  timestamp: Date
  read: boolean
}

const defaultPreferences: UserPreferences = {
  defaultSymbol: 'AAPL',
  refreshInterval: 5000,
  chartType: 'candlestick',
  showNotifications: true,
  soundEnabled: false,
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Theme
      theme: 'light',
      setTheme: (theme) => {
        set({ theme })
        // Apply theme to document
        if (theme === 'dark') {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
      },
      toggleTheme: () =>
        set((state) => {
          const newTheme = state.theme === 'light' ? 'dark' : 'light'
          // Apply theme to document
          if (newTheme === 'dark') {
            document.documentElement.classList.add('dark')
          } else {
            document.documentElement.classList.remove('dark')
          }
          return { theme: newTheme }
        }),

      // Sidebar
      sidebarCollapsed: false,
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      // Current symbol
      currentSymbol: 'AAPL',
      setCurrentSymbol: (symbol) => set({ currentSymbol: symbol }),

      // User preferences
      preferences: defaultPreferences,
      updatePreferences: (preferences) =>
        set((state) => ({
          preferences: { ...state.preferences, ...preferences },
        })),

      // Notifications
      notifications: [],
      addNotification: (notification) =>
        set((state) => ({
          notifications: [
            {
              ...notification,
              id: `notif-${Date.now()}-${Math.random()}`,
              timestamp: new Date(),
              read: false,
            },
            ...state.notifications,
          ],
        })),
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),
      clearNotifications: () => set({ notifications: [] }),

      // Connection status
      isConnected: false,
      setIsConnected: (connected) => set({ isConnected: connected }),

      // Loading states
      isLoading: false,
      setIsLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: 'reasoning-trading-storage',
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        currentSymbol: state.currentSymbol,
        preferences: state.preferences,
      }),
    }
  )
)

// Initialize theme on load
const storedTheme = useAppStore.getState().theme
if (storedTheme === 'dark') {
  document.documentElement.classList.add('dark')
}
