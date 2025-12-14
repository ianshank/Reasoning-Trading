import { NavLink } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'
import {
  LayoutDashboard,
  Briefcase,
  LineChart,
  GitBranch,
  ShoppingCart,
  TrendingUp,
  Layers,
  Settings,
  ChevronLeft,
  ChevronRight,
  User,
} from 'lucide-react'
import clsx from 'clsx'

interface NavItem {
  name: string
  path: string
  icon: React.ComponentType<{ className?: string }>
}

const navItems: NavItem[] = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Portfolio', path: '/portfolio', icon: Briefcase },
  { name: 'Analysis', path: '/analysis', icon: LineChart },
  { name: 'MCTS', path: '/mcts', icon: GitBranch },
  { name: 'Orders', path: '/orders', icon: ShoppingCart },
  { name: 'Regime', path: '/regime', icon: TrendingUp },
  { name: 'Lambda', path: '/lambda', icon: Layers },
  { name: 'Settings', path: '/settings', icon: Settings },
]

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useAppStore()

  return (
    <div
      className={clsx(
        'h-screen bg-card border-r border-border flex flex-col transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-border">
        {!sidebarCollapsed && (
          <h1 className="text-lg font-bold text-foreground">
            Reasoning Trading
          </h1>
        )}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-accent transition-colors"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors group',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <item.icon
                      className={clsx(
                        'w-5 h-5 flex-shrink-0',
                        isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-accent-foreground'
                      )}
                    />
                    {!sidebarCollapsed && (
                      <span className="font-medium">{item.name}</span>
                    )}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* User Profile */}
      <div className="border-t border-border p-4">
        <div
          className={clsx(
            'flex items-center gap-3 p-2 rounded-lg hover:bg-accent transition-colors cursor-pointer',
            sidebarCollapsed && 'justify-center'
          )}
        >
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground flex-shrink-0">
            <User className="w-4 h-4" />
          </div>
          {!sidebarCollapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                Trader
              </p>
              <p className="text-xs text-muted-foreground truncate">
                trader@example.com
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
