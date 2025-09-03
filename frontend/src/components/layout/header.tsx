'use client'

import { useAuthStore } from '@/store/auth'
import { Settings, LogOut, BarChart3 } from 'lucide-react'

export function Header() {
  const { logout } = useAuthStore()

  const handleLogout = async () => {
    await logout()
  }

  return (
    <div className="h-12 bg-gray-900 border-b border-gray-700 px-6 flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <BarChart3 size={18} className="text-white" />
        </div>
        <span className="text-white font-semibold text-lg">FIX Trader</span>
      </div>

      <div className="flex items-center space-x-2">
        <button 
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          title="Settings"
        >
          <Settings size={18} />
        </button>
        
        <button 
          onClick={handleLogout}
          className="p-2 text-gray-400 hover:text-red-400 hover:bg-gray-800 rounded-lg transition-colors"
          title="Logout"
        >
          <LogOut size={18} />
        </button>
      </div>
    </div>
  )
}

