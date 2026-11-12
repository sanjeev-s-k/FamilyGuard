import React, { useState } from 'react';
import {
  Bell, Bot, RefreshCw, CheckCircle2,
  AlertTriangle, Globe, Send, ChevronDown
} from 'lucide-react';
import { NotificationItem } from '../types';

interface HeaderProps {
  currentRole: 'PARENT' | 'CHILD';
  onSwitchRole: (role: 'PARENT' | 'CHILD') => void;
  notifications: NotificationItem[];
  onMarkNotificationRead: (id: number) => void;
  onMarkAllNotificationsRead: () => void;
  onOpenAIAssistant: () => void;
  onOpenSendMoney?: () => void;
  onResetDemo: () => void;
  isResetting: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentRole,
  onSwitchRole,
  notifications,
  onMarkNotificationRead,
  onMarkAllNotificationsRead,
  onOpenAIAssistant,
  onOpenSendMoney,
  onResetDemo,
  isResetting,
}) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <header className="sticky top-0 z-40 bg-[#003087] text-white shadow-md">
      {/* Top PayPal Sandbox Developer Strip */}
      <div className="bg-[#001C64] text-xs py-1.5 px-4 sm:px-6 lg:px-8 flex items-center justify-between border-b border-blue-900/40">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="font-extrabold uppercase text-[10px] tracking-wider text-amber-300">
            PayPal Developer Sandbox
          </span>
          <span className="text-blue-300 hidden sm:inline">• Cross-Border Family Portal</span>
        </div>

        {/* Live FX Ticker */}
        <div className="flex items-center space-x-3 text-[11px]">
          <div className="flex items-center space-x-1.5 text-blue-200 bg-white/10 px-2 py-0.5 rounded-full">
            <Globe className="w-3 h-3 text-[#00cfe8]" />
            <span className="font-semibold">FX Rate:</span>
            <span className="font-mono font-bold text-white">1 USD = ₹85.00 INR</span>
          </div>
          <span className="text-blue-300 text-[10px] hidden md:inline">
            {currentRole === 'PARENT' ? 'Active: Mumbai, India' : 'Active: Boston, MA, USA'}
          </span>
        </div>
      </div>

      {/* Main PayPal Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-18">
          {/* Brand Identity */}
          <div className="flex items-center space-x-3.5">
            {/* PayPal Double-P Insignia */}
            <div className="w-10 h-10 rounded-2xl bg-white flex items-center justify-center shadow-xs">
              <span className="font-black text-xl tracking-tighter text-[#003087]">
                P<span className="text-[#0070E0]">P</span>
              </span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-black tracking-tight text-white">PayPal</span>
                <span className="text-xs font-bold text-blue-200">FamilyGuard</span>
              </div>
              <p className="hidden sm:block text-[11px] font-medium text-blue-200/90">
                Cross-Border Study Abroad Parental Payment Monitoring & Remittance
              </p>
            </div>
          </div>

          {/* Quick Sandbox Account Switcher + Actions */}
          <div className="flex items-center space-x-3">
            {/* PayPal Sandbox Account Switcher */}
            <div className="bg-[#001C64] p-1 rounded-full flex items-center border border-blue-900/60 shadow-inner">
              <button
                onClick={() => onSwitchRole('PARENT')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all ${
                  currentRole === 'PARENT'
                    ? 'bg-[#FFC439] text-[#001C64] shadow-sm'
                    : 'text-blue-200 hover:text-white'
                }`}
              >
                <span>Parent (India • ₹ INR)</span>
              </button>
              <button
                onClick={() => onSwitchRole('CHILD')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all ${
                  currentRole === 'CHILD'
                    ? 'bg-[#0070E0] text-white shadow-sm'
                    : 'text-blue-200 hover:text-white'
                }`}
              >
                <span>Arjun (US • $ USD)</span>
              </button>
            </div>

            {/* Send Money CTA (Parent Mode) */}
            {currentRole === 'PARENT' && onOpenSendMoney && (
              <button
                onClick={onOpenSendMoney}
                className="hidden sm:flex items-center space-x-1.5 px-3.5 py-2 bg-[#FFC439] hover:bg-[#F6C944] text-[#001C64] font-black rounded-full text-xs shadow-md transition border border-amber-300"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Send Money</span>
              </button>
            )}

            {/* AI Assistant Button (Parent Mode) */}
            {currentRole === 'PARENT' && (
              <button
                onClick={onOpenAIAssistant}
                className="flex items-center space-x-1.5 px-3 py-2 bg-[#0070E0] hover:bg-[#005ea6] text-white rounded-full text-xs font-bold shadow-sm transition"
              >
                <Bot className="w-4 h-4 text-[#00cfe8]" />
                <span className="hidden md:inline">AI Assistant</span>
              </button>
            )}

            {/* Notification Bell Dropdown */}
            {currentRole === 'PARENT' && (
              <div className="relative">
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className="relative p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition"
                  title="PayPal Sandbox Notifications"
                >
                  <Bell className="w-4 h-4" />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center animate-pulse">
                      {unreadCount}
                    </span>
                  )}
                </button>

                {showNotifications && (
                  <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white text-slate-900 rounded-3xl shadow-2xl border border-slate-200 py-3 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                    <div className="px-4 pb-2 border-b border-slate-100 flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-bold text-slate-900">PayPal Activity Alerts</span>
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-semibold">
                          {unreadCount} new
                        </span>
                      </div>
                      {unreadCount > 0 && (
                        <button
                          onClick={onMarkAllNotificationsRead}
                          className="text-xs text-blue-600 hover:underline font-medium"
                        >
                          Mark all read
                        </button>
                      )}
                    </div>

                    <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                      {notifications.length === 0 ? (
                        <div className="py-6 text-center text-xs text-slate-400">
                          No notifications yet.
                        </div>
                      ) : (
                        notifications.slice(0, 10).map((n) => (
                          <div
                            key={n.id}
                            className={`p-3.5 hover:bg-slate-50 transition cursor-pointer flex items-start space-x-3 ${
                              !n.is_read ? 'bg-blue-50/50' : ''
                            }`}
                            onClick={() => onMarkNotificationRead(n.id)}
                          >
                            <div className="mt-0.5">
                              {n.risk_level === 'HIGH' ? (
                                <AlertTriangle className="w-4 h-4 text-rose-500" />
                              ) : n.risk_level === 'MEDIUM' ? (
                                <AlertTriangle className="w-4 h-4 text-amber-500" />
                              ) : (
                                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                              )}
                            </div>
                            <div className="flex-1">
                              <p className="text-xs font-semibold text-slate-800">{n.title}</p>
                              <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">{n.message}</p>
                              <span className="text-[10px] text-slate-400 mt-1 block">
                                {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                            {!n.is_read && (
                              <span className="w-2 h-2 rounded-full bg-[#0070E0] mt-1.5"></span>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Reset Demo State Button */}
            <button
              onClick={onResetDemo}
              disabled={isResetting}
              className="p-2 rounded-full bg-white/10 hover:bg-white/20 text-blue-200 hover:text-white transition text-xs font-medium flex items-center space-x-1"
              title="Reset Demo State"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin text-amber-300' : ''}`} />
              <span className="hidden xl:inline">Reset Sandbox</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
