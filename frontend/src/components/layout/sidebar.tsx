'use client'

import { cn } from '@/lib/utils'
import { 
  BarChart3, 
  TrendingUp, 
  Wallet, 
  Settings, 
  PieChart,
  Activity,
  Clock,
  LogOut
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'

const navigationItems = [
  { icon: BarChart3, label: 'Trading', active: true },
  { icon: TrendingUp, label: 'Markets', active: false },
  { icon: PieChart, label: 'Portfolio', active: false },
  { icon: Wallet, label: 'Wallet', active: false },
  { icon: Activity, label: 'History', active: false },
  { icon: Clock, label: 'Orders', active: false },
  { icon: Settings, label: 'Settings', active: false },
]

export function Sidebar() {
  const { logout, sessionStatus } = useAuthStore()

  const handleLogout = async () => {
    await logout()
  }

  return (
    <div className="w-16 bg-gray-900 border-r border-gray-700 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <BarChart3 size={18} className="text-white" />
        </div>
      </div>

      <nav className="flex-1 py-4">
        <ul className="space-y-2">
          {navigationItems.map((item, index) => (
            <li key={index}>
              <button
                className={cn(
                  "w-full p-3 flex items-center justify-center transition-colors relative group",
                  item.active 
                    ? "text-blue-400 bg-blue-900/20" 
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                )}
              >
                <item.icon size={20} />
                {item.active && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-r" />
                )}
                
                <div className="absolute left-full ml-2 px-2 py-1 bg-gray-800 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                  {item.label}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="p-4 border-t border-gray-700">
        <div className="space-y-2">
          <div className="text-center">
            <div className={cn(
              "w-2 h-2 rounded-full mx-auto mb-1",
              sessionStatus?.session.overall_active ? "bg-green-500" : "bg-red-500"
            )} />
            <div className="text-xs text-gray-400">
              {sessionStatus?.session.overall_active ? 'Connected' : 'Disconnected'}
            </div>
          </div>
          
          <button
            onClick={handleLogout}
            className="w-full p-2 text-gray-400 hover:text-red-400 hover:bg-gray-800 rounded transition-colors group"
          >
            <LogOut size={16} className="mx-auto" />
            <div className="absolute left-full ml-2 px-2 py-1 bg-gray-800 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
              Logout
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}

