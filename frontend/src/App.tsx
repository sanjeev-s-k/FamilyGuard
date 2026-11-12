import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ParentDashboard } from './components/ParentDashboard';
import { ChildDashboard } from './components/ChildDashboard';
import { ReceiptModal } from './components/ReceiptModal';
import { SendMoneyModal } from './components/SendMoneyModal';
import { AIAssistantDrawer } from './components/AIAssistantDrawer';
import { NotificationItem } from './types';
import { api, setToken } from './api';

export const App: React.FC = () => {
  const [currentRole, setCurrentRole] = useState<'PARENT' | 'CHILD'>('PARENT');
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [selectedReceiptCode, setSelectedReceiptCode] = useState<string | null>(null);
  const [isAIAssistantOpen, setIsAIAssistantOpen] = useState(false);
  const [isSendMoneyOpen, setIsSendMoneyOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [isResetting, setIsResetting] = useState(false);

  // Authenticate demo user on load
  useEffect(() => {
    const initAuth = async () => {
      try {
        if (currentRole === 'PARENT') {
          const res = await api.demoLoginParent();
          setToken(res.access_token);
        } else {
          const res = await api.demoLoginChild();
          setToken(res.access_token);
        }
        await loadNotifications();
      } catch (err) {
        console.error('Failed to initialize demo auth:', err);
      }
    };
    initAuth();
  }, [currentRole]);

  // Load notifications for Parent
  const loadNotifications = async () => {
    try {
      if (currentRole === 'PARENT') {
        const notifs = await api.getNotifications();
        setNotifications(notifs);
      }
    } catch (err) {
      // Ignore if not authorized
    }
  };

  // Switch role handler - await login token BEFORE changing role to avoid race conditions
  const handleSwitchRole = async (role: 'PARENT' | 'CHILD') => {
    try {
      if (role === 'PARENT') {
        const res = await api.demoLoginParent();
        setToken(res.access_token);
      } else {
        const res = await api.demoLoginChild();
        setToken(res.access_token);
      }
    } catch (err) {
      console.error('Error switching demo auth:', err);
    }
    setCurrentRole(role);
    setRefreshTrigger((prev) => prev + 1);
    if (role === 'PARENT') {
      loadNotifications();
    }
  };


  const handleMarkNotificationRead = async (id: number) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkAllNotificationsRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetDemo = async () => {
    if (!window.confirm('Reset FamilyGuard demonstration to pristine initial cross-border state?')) return;
    try {
      setIsResetting(true);
      await api.resetDemoDatabase();
      // Re-login as parent
      const res = await api.demoLoginParent();
      setToken(res.access_token);
      setCurrentRole('PARENT');
      setRefreshTrigger((prev) => prev + 1);
      await loadNotifications();
      alert('Demo data successfully reset! Initial overseas balance restored to $250.00 USD (~₹21,250 INR).');
    } catch (err: any) {
      alert(`Error resetting demo: ${err.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Header
        currentRole={currentRole}
        onSwitchRole={handleSwitchRole}
        notifications={notifications}
        onMarkNotificationRead={handleMarkNotificationRead}
        onMarkAllNotificationsRead={handleMarkAllNotificationsRead}
        onOpenAIAssistant={() => setIsAIAssistantOpen(true)}
        onOpenSendMoney={() => setIsSendMoneyOpen(true)}
        onResetDemo={handleResetDemo}
        isResetting={isResetting}
      />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {currentRole === 'PARENT' ? (
          <ParentDashboard
            onOpenReceipt={(code) => setSelectedReceiptCode(code)}
            onOpenAIAssistant={() => setIsAIAssistantOpen(true)}
            onOpenSendMoney={() => setIsSendMoneyOpen(true)}
            refreshTrigger={refreshTrigger}
          />
        ) : (
          <ChildDashboard
            onOpenReceipt={(code) => setSelectedReceiptCode(code)}
            refreshTrigger={refreshTrigger}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200/80 py-4 text-center text-xs text-slate-400">
        <p>FamilyGuard © 2026 • AI-Powered Cross-Border Study Abroad Parental Payment Monitoring • PayPal Developer Sandbox</p>
      </footer>

      {/* Modals & Drawers */}
      <ReceiptModal
        transactionCode={selectedReceiptCode}
        onClose={() => setSelectedReceiptCode(null)}
      />

      <SendMoneyModal
        isOpen={isSendMoneyOpen}
        onClose={() => setIsSendMoneyOpen(false)}
        childId={1}
        childName="Arjun"
        onSuccess={() => {
          setRefreshTrigger((prev) => prev + 1);
          loadNotifications();
        }}
      />

      <AIAssistantDrawer
        isOpen={isAIAssistantOpen}
        onClose={() => setIsAIAssistantOpen(false)}
        childName="Arjun"
      />
    </div>
  );
};
