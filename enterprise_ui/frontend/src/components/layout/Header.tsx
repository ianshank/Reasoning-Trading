import { useState } from 'react'
import { useAppStore } from '@/stores/appStore'
import {
  Search,
  Bell,
  Sun,
  Moon,
  Settings,
  User,
  LogOut,
  ChevronDown,
} from 'lucide-react'
import clsx from 'clsx'

export default function Header() {
  const { theme, toggleTheme, notifications, currentSymbol, setCurrentSymbol } =
    useAppStore()
  const [searchOpen, setSearchOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)

  const unreadCount = notifications.filter((n) => !n.read).length

  const handleSymbolSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const symbol = formData.get('symbol') as string
    if (symbol) {
      setCurrentSymbol(symbol.toUpperCase())
      setSearchOpen(false)
    }
  }

  return (
    <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6">
      {/* Search */}
      <div className="flex-1 max-w-md">
        <form onSubmit={handleSymbolSearch} className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            name="symbol"
            placeholder="Search symbol..."
            defaultValue={currentSymbol}
            className="w-full pl-10 pr-4 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            onFocus={() => setSearchOpen(true)}
            onBlur={() => setTimeout(() => setSearchOpen(false), 200)}
          />
        </form>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Current Symbol Badge */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-primary/10 text-primary rounded-lg">
          <span className="text-sm font-medium">{currentSymbol}</span>
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg hover:bg-accent transition-colors"
          aria-label="Toggle theme"
        >
          {theme === 'light' ? (
            <Moon className="w-5 h-5" />
          ) : (
            <Sun className="w-5 h-5" />
          )}
        </button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            className="p-2 rounded-lg hover:bg-accent transition-colors relative"
            aria-label="Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-destructive rounded-full" />
            )}
          </button>

          {/* Notifications Dropdown */}
          {notificationsOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setNotificationsOpen(false)}
              />
              <div className="absolute right-0 mt-2 w-80 bg-popover border border-border rounded-lg shadow-lg z-20">
                <div className="p-4 border-b border-border">
                  <h3 className="font-semibold text-sm">Notifications</h3>
                  {unreadCount > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {unreadCount} unread
                    </p>
                  )}
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground text-sm">
                      No notifications
                    </div>
                  ) : (
                    notifications.slice(0, 5).map((notif) => (
                      <div
                        key={notif.id}
                        className={clsx(
                          'p-4 border-b border-border hover:bg-accent cursor-pointer',
                          !notif.read && 'bg-accent/50'
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <div
                            className={clsx(
                              'w-2 h-2 rounded-full mt-1',
                              notif.type === 'error' && 'bg-destructive',
                              notif.type === 'success' && 'bg-profit',
                              notif.type === 'warning' && 'bg-yellow-500',
                              notif.type === 'info' && 'bg-primary'
                            )}
                          />
                          <div className="flex-1">
                            <p className="text-sm font-medium">{notif.title}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {notif.message}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {new Date(notif.timestamp).toLocaleTimeString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* User Menu */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-2 p-2 rounded-lg hover:bg-accent transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
              <User className="w-4 h-4" />
            </div>
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          </button>

          {/* User Menu Dropdown */}
          {userMenuOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setUserMenuOpen(false)}
              />
              <div className="absolute right-0 mt-2 w-48 bg-popover border border-border rounded-lg shadow-lg z-20">
                <div className="p-2">
                  <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors">
                    <User className="w-4 h-4" />
                    Profile
                  </button>
                  <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors">
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>
                  <div className="border-t border-border my-1" />
                  <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent text-destructive transition-colors">
                    <LogOut className="w-4 h-4" />
                    Logout
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
