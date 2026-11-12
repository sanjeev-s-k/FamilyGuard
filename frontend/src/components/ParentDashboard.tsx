import React, { useState, useEffect } from 'react';
import {
  TrendingUp, Users, CreditCard, AlertTriangle, ShieldCheck,
  FileText, Sliders, Settings, CheckCircle2, XCircle, Search,
  Download, ArrowUpRight, ChevronRight, Eye, Bot, RefreshCw,
  Clock, Filter, ShieldAlert, Sparkles, Check, X, PlusCircle,
  Send, Globe, ArrowRightLeft, DollarSign
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend, BarChart, Bar
} from 'recharts';
import {
  ParentOverviewData, TransactionItem, ApprovalRequestItem,
  SpendingRule
} from '../types';
import { api } from '../api';

const COLORS = ['#003087', '#0070E0', '#00CFE8', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899'];
const FX_RATE = 85.0;

interface ParentDashboardProps {
  onOpenReceipt: (code: string) => void;
  onOpenAIAssistant: () => void;
  refreshTrigger: number;
  onOpenSendMoney?: () => void;
}

export const ParentDashboard: React.FC<ParentDashboardProps> = ({
  onOpenReceipt,
  onOpenAIAssistant,
  refreshTrigger,
  onOpenSendMoney,
}) => {
  const [activeTab, setActiveTab] = useState<
    'overview' | 'children' | 'transactions' | 'approvals' | 'insights' | 'reports' | 'controls' | 'settings'
  >('overview');

  const [overview, setOverview] = useState<ParentOverviewData | null>(null);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequestItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Filter state for transactions tab
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Controls state for Arjun (stored in USD)
  const [dailyLimit, setDailyLimit] = useState(60);
  const [weeklyLimit, setWeeklyLimit] = useState(250);
  const [approvalThreshold, setApprovalThreshold] = useState(40);
  const [savingControls, setSavingControls] = useState(false);
  const [controlsSuccess, setControlsSuccess] = useState(false);

  // Approval action notes
  const [actionNotes, setActionNotes] = useState<{ [key: number]: string }>({});
  const [actionLoading, setActionLoading] = useState<{ [key: number]: boolean }>({});

  const loadData = async (isBackground = false) => {
    try {
      if (!overview && !isBackground) {
        setLoading(true);
      }
      const [ovData, txData, appData] = await Promise.all([
        api.getParentOverview(),
        api.getParentTransactions(),
        api.getApprovalRequests(),
      ]);
      setOverview(ovData);
      setTransactions(txData);
      setApprovals(appData);

      if (ovData.children.length > 0 && !overview) {
        setDailyLimit(ovData.children[0].daily_limit);
        setWeeklyLimit(ovData.children[0].weekly_limit);
        setApprovalThreshold(ovData.children[0].approval_threshold);
      }
    } catch (err) {
      console.error('Error loading parent dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(!!overview);
  }, [refreshTrigger, activeTab]);

  const handleApprovalAction = async (requestId: number, action: 'APPROVE' | 'DECLINE') => {
    try {
      setActionLoading((prev) => ({ ...prev, [requestId]: true }));
      await api.actOnApproval(requestId, action, actionNotes[requestId] || '');
      await loadData();
    } catch (err: any) {
      alert(`Error updating approval: ${err.message}`);
    } finally {
      setActionLoading((prev) => ({ ...prev, [requestId]: false }));
    }
  };

  const handleSaveControls = async () => {
    if (!overview || overview.children.length === 0) return;
    try {
      setSavingControls(true);
      setControlsSuccess(false);
      const childId = overview.children[0].id;
      await api.updateSpendingLimits(childId, {
        daily_limit: dailyLimit,
        weekly_limit: weeklyLimit,
        approval_threshold: approvalThreshold,
        is_active: true,
      });
      setControlsSuccess(true);
      await loadData();
      setTimeout(() => setControlsSuccess(false), 3000);
    } catch (err: any) {
      alert(`Failed to save spending limits: ${err.message}`);
    } finally {
      setSavingControls(false);
    }
  };

  const filteredTransactions = transactions.filter((t) => {
    const matchesSearch =
      t.merchant.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.transaction_code.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const pendingApprovalsList = approvals.filter((a) => a.status === 'PENDING');

  return (
    <div className="space-y-6">
      {/* Navigation Sub-Tabs */}
      <div className="bg-white rounded-2xl p-1.5 border border-slate-200/80 shadow-xs flex flex-wrap gap-1">
        {[
          { id: 'overview', label: 'Overview', icon: TrendingUp },
          { id: 'children', label: 'My Children', icon: Users },
          { id: 'transactions', label: 'Transactions', icon: CreditCard },
          {
            id: 'approvals',
            label: 'Approval Requests',
            icon: AlertTriangle,
            badge: pendingApprovalsList.length > 0 ? pendingApprovalsList.length : undefined
          },
          { id: 'insights', label: 'AI Insights', icon: Sparkles },
          { id: 'reports', label: 'Reports', icon: FileText },
          { id: 'controls', label: 'Spending Controls', icon: Sliders },
          { id: 'settings', label: 'Settings', icon: Settings },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-[#003087] text-white shadow-xs'
                  : 'text-slate-600 hover:text-[#003087] hover:bg-slate-100'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              {tab.badge && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500 text-white animate-pulse">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {loading && !overview ? (
        <div className="py-20 text-center flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-3 border-[#003087] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs text-slate-500 font-medium">Loading parental monitoring telemetry...</p>
        </div>
      ) : (
        <>
          {/* ========================================================== */}
          {/* 1. OVERVIEW TAB */}
          {/* ========================================================== */}
          {activeTab === 'overview' && overview && (
            <div className="space-y-6">
              {/* Cross-Border Study Abroad Banner */}
              <div className="bg-gradient-to-r from-[#001C64] via-[#003087] to-[#0070E0] rounded-3xl p-5 sm:p-6 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-md border border-blue-900/40">
                <div className="flex items-center space-x-3.5">
                  <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center shrink-0 border border-white/20">
                    <Globe className="w-6 h-6 text-[#00cfe8]" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-base font-extrabold tracking-tight">Cross-Border Study Abroad Monitored Account</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-[#FFC439] text-[#001C64]">
                        1 USD = ₹85.00 INR
                      </span>
                    </div>
                    <p className="text-xs text-blue-100 mt-1">
                      Son <b>Arjun</b> spends in <b>Dollars ($ USD)</b> at university in Boston, USA. You monitor expenditures and remit funds in <b>Rupees (₹ INR)</b> from India.
                    </p>
                  </div>
                </div>
                {onOpenSendMoney && (
                  <button
                    onClick={onOpenSendMoney}
                    className="px-5 py-3 bg-[#FFC439] hover:bg-[#F6C944] text-[#001C64] font-black rounded-2xl text-xs shadow-md transition flex items-center justify-center space-x-2 shrink-0 border border-amber-300"
                  >
                    <Send className="w-4 h-4" />
                    <span>Send Money to Arjun</span>
                  </button>
                )}
              </div>

              {/* KPI Stat Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs relative overflow-hidden">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Family Spend</span>
                    <div className="p-2 bg-blue-50 text-[#003087] rounded-xl">
                      <CreditCard className="w-4 h-4" />
                    </div>
                  </div>
                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹ {overview.total_family_spending.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1 flex items-center space-x-1">
                    <span className="text-[#0070E0] font-bold">
                      ≈ ${(overview.total_family_spending / (overview.fx_rate || FX_RATE)).toFixed(2)} USD
                    </span>
                    <span>overseas total</span>
                  </p>
                </div>

                <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Arjun's Spend (Today)</span>
                    <div className="p-2 bg-indigo-50 text-[#0070E0] rounded-xl">
                      <Users className="w-4 h-4" />
                    </div>
                  </div>
                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹ {overview.children[0]?.spent_today?.toLocaleString(undefined, { minimumFractionDigits: 2 }) || '0.00'}
                  </p>
                  <p className="text-[11px] text-[#0070E0] font-semibold mt-1">
                    ≈ ${( (overview.children[0]?.spent_today || 0) / (overview.fx_rate || FX_RATE) ).toFixed(2)} USD abroad
                  </p>
                  <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5">
                    <div
                      className="bg-[#0070E0] h-1.5 rounded-full"
                      style={{
                        width: `${Math.min(
                          100,
                          ((overview.children[0]?.spent_today || 0) / ((overview.children[0]?.daily_limit || 60) * (overview.fx_rate || FX_RATE))) * 100
                        )}%`,
                      }}
                    ></div>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1">
                    Cap: ${overview.children[0]?.daily_limit || 60} USD (≈ ₹{((overview.children[0]?.daily_limit || 60) * (overview.fx_rate || FX_RATE)).toLocaleString()} INR)
                  </p>
                </div>

                <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Pending Approvals</span>
                    <div className="p-2 bg-amber-50 text-amber-600 rounded-xl">
                      <AlertTriangle className="w-4 h-4" />
                    </div>
                  </div>
                  <p className="text-2xl font-black text-slate-900 mt-2">
                    {overview.pending_approvals_count}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    {overview.pending_approvals_count > 0 ? (
                      <span className="text-rose-600 font-bold">Action required</span>
                    ) : (
                      <span className="text-emerald-600 font-bold">All overseas requests reviewed</span>
                    )}
                  </p>
                </div>

                <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Transactions</span>
                    <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl">
                      <TrendingUp className="w-4 h-4" />
                    </div>
                  </div>
                  <p className="text-2xl font-black text-slate-900 mt-2">
                    {overview.total_transactions}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1 flex items-center space-x-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#003087]" />
                    <span>PayPal Sandbox Monitored</span>
                  </p>
                </div>
              </div>

              {/* Charts Section */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 7-Day Spending Area Chart */}
                <div className="lg:col-span-2 bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Daily Spending Telemetry (Last 7 Days)</h3>
                      <p className="text-xs text-slate-500">Continuous AI-verified expenditure timeline in Indian Rupees (₹)</p>
                    </div>
                  </div>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={overview.daily_trends}>
                        <defs>
                          <linearGradient id="colorSpend" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#003087" stopOpacity={0.25} />
                            <stop offset="95%" stopColor="#0070E0" stopOpacity={0.0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                        <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94A3B8" />
                        <YAxis tick={{ fontSize: 11 }} stroke="#94A3B8" />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#001C64', borderRadius: '12px', color: '#fff', fontSize: '12px', border: 'none' }}
                          formatter={(value: any) => [`₹ ${Number(value).toFixed(2)} (≈ $${(Number(value)/FX_RATE).toFixed(2)} USD)`, 'Spending']}
                        />
                        <Area isAnimationActive={false} type="monotone" dataKey="amount" stroke="#003087" strokeWidth={2.5} fillOpacity={1} fill="url(#colorSpend)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Category Breakdown Pie Chart */}
                <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs flex flex-col">
                  <h3 className="text-sm font-bold text-slate-900 mb-1">Category Distribution</h3>
                  <p className="text-xs text-slate-500 mb-4">Cumulative spend allocation (₹ INR)</p>
                  <div className="flex-1 h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          isAnimationActive={false}
                          data={overview.category_spending}
                          dataKey="amount"
                          nameKey="category"
                          cx="50%"
                          cy="50%"
                          innerRadius={45}
                          outerRadius={75}
                          paddingAngle={3}
                        >
                          {overview.category_spending.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{ backgroundColor: '#001C64', borderRadius: '12px', color: '#fff', fontSize: '12px', border: 'none' }}
                          formatter={(val: any) => [`₹ ${Number(val).toFixed(2)} (≈ $${(Number(val)/FX_RATE).toFixed(2)} USD)`, '']}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="space-y-1.5 pt-2 border-t border-slate-100">
                    {overview.category_spending.slice(0, 3).map((cat, i) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <div className="flex items-center space-x-2">
                          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }}></span>
                          <span className="text-slate-600 font-medium">{cat.category}</span>
                        </div>
                        <span className="font-bold text-slate-900">₹ {cat.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Recent Activity Table Preview */}
              <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Recent Transactions & AI Risk Reports</h3>
                    <p className="text-xs text-slate-500">Live overseas transaction stream with dual-currency breakdown</p>
                  </div>
                  <button
                    onClick={() => setActiveTab('transactions')}
                    className="text-xs text-[#0070E0] font-semibold hover:underline flex items-center space-x-1"
                  >
                    <span>View All</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                        <th className="pb-3">Code</th>
                        <th className="pb-3">Child</th>
                        <th className="pb-3">Merchant</th>
                        <th className="pb-3">Category</th>
                        <th className="pb-3">Amount (₹ INR / $ USD)</th>
                        <th className="pb-3">Status</th>
                        <th className="pb-3">AI Risk</th>
                        <th className="pb-3 text-right">Receipt & Report</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {transactions.slice(0, 5).map((t) => (
                        <tr key={t.id} className="hover:bg-slate-50/80 transition">
                          <td className="py-3 font-mono font-bold text-slate-700">{t.transaction_code}</td>
                          <td className="py-3 font-semibold text-slate-800">{t.child_name}</td>
                          <td className="py-3 font-medium text-slate-900">{t.merchant}</td>
                          <td className="py-3 text-slate-600">{t.category}</td>
                          <td className="py-3 font-bold text-slate-900">
                            <div className="flex flex-col">
                              <span>₹ {(t.amount_inr || (t.amount * FX_RATE)).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                              <span className="text-[10px] text-[#0070E0] font-medium font-mono">${t.amount.toFixed(2)} USD</span>
                            </div>
                          </td>
                          <td className="py-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                t.status === 'COMPLETED'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : t.status === 'PENDING_APPROVAL'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-rose-100 text-rose-800'
                              }`}
                            >
                              {t.status}
                            </span>
                          </td>
                          <td className="py-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                                t.ai_report?.risk_level === 'HIGH'
                                  ? 'bg-rose-100 text-rose-700'
                                  : t.ai_report?.risk_level === 'MEDIUM'
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-emerald-100 text-emerald-700'
                              }`}
                            >
                              {t.ai_report?.risk_level || 'LOW'}
                            </span>
                          </td>
                          <td className="py-3 text-right">
                            <button
                              onClick={() => onOpenReceipt(t.transaction_code)}
                              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-[#003087] hover:bg-blue-100 font-semibold transition"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>View</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* 2. MY CHILDREN TAB */}
          {/* ========================================================== */}
          {activeTab === 'children' && overview && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Child Overseas Profiles & Spending Limits</h3>
                  <p className="text-xs text-slate-500">Configure individualized spending limits and monitor foreign balances</p>
                </div>
                {onOpenSendMoney && (
                  <button
                    onClick={onOpenSendMoney}
                    className="px-4 py-2 bg-[#FFC439] hover:bg-[#F6C944] text-[#001C64] font-black rounded-xl text-xs shadow-xs transition flex items-center space-x-1.5 self-start sm:self-auto border border-amber-300"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Send Money / Remit to Arjun</span>
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {overview.children.map((child) => (
                  <div key={child.id} className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3.5">
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#001C64] via-[#003087] to-[#0070E0] text-white flex items-center justify-center font-bold text-lg shadow-md">
                          {child.name.charAt(0)}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h4 className="text-base font-bold text-slate-900">{child.name}</h4>
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-[#003087]">
                              Boston, USA
                            </span>
                          </div>
                          <span className="text-xs text-slate-500 font-medium">Age: {child.age} yrs • Overseas Student Account ($ USD)</span>
                        </div>
                      </div>
                      <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                        Active Monitored
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-3 bg-blue-50/40 p-4 rounded-2xl border border-blue-100/80">
                      <div>
                        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Wallet Balance (Abroad)</span>
                        <span className="text-xl font-black text-slate-900 block mt-0.5">
                          ${child.balance.toFixed(2)} <span className="text-xs font-bold text-slate-500">USD</span>
                        </span>
                        <span className="text-[11px] font-semibold text-[#0070E0] block mt-0.5">
                          ≈ ₹{(child.balance * FX_RATE).toLocaleString(undefined, { minimumFractionDigits: 2 })} INR
                        </span>
                      </div>
                      <div>
                        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Total Spent (Abroad)</span>
                        <span className="text-xl font-black text-[#003087] block mt-0.5">
                          ${child.total_spent.toFixed(2)} <span className="text-xs font-bold text-slate-500">USD</span>
                        </span>
                        <span className="text-[11px] font-semibold text-slate-500 block mt-0.5">
                          ≈ ₹{(child.total_spent * FX_RATE).toLocaleString(undefined, { minimumFractionDigits: 2 })} INR
                        </span>
                      </div>
                    </div>

                    <div className="space-y-3 pt-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-600 font-medium">Daily Limit</span>
                        <span className="font-bold text-slate-900">
                          ${child.daily_limit} USD <span className="text-slate-400 font-normal">(≈ ₹{(child.daily_limit * FX_RATE).toLocaleString()} INR)</span>
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-600 font-medium">Weekly Limit</span>
                        <span className="font-bold text-slate-900">
                          ${child.weekly_limit} USD <span className="text-slate-400 font-normal">(≈ ₹{(child.weekly_limit * FX_RATE).toLocaleString()} INR)</span>
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-600 font-medium">Approval Threshold</span>
                        <span className="font-bold text-amber-600">
                          ${child.approval_threshold} USD <span className="text-amber-800/60 font-normal">(≈ ₹{(child.approval_threshold * FX_RATE).toLocaleString()} INR)</span>
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 flex flex-col sm:flex-row items-center gap-2">
                      {onOpenSendMoney && (
                        <button
                          onClick={onOpenSendMoney}
                          className="w-full sm:flex-1 py-2.5 bg-[#FFC439] hover:bg-[#F6C944] text-[#001C64] font-black text-xs rounded-xl shadow-xs transition flex items-center justify-center space-x-1.5 border border-amber-300"
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>Send Money</span>
                        </button>
                      )}
                      <button
                        onClick={() => setActiveTab('controls')}
                        className="w-full sm:flex-1 py-2.5 bg-blue-50 hover:bg-blue-100 text-[#003087] font-bold text-xs rounded-xl transition text-center"
                      >
                        Adjust Limits
                      </button>
                      <button
                        onClick={() => {
                          setSearchQuery(child.name);
                          setActiveTab('transactions');
                        }}
                        className="w-full sm:flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition text-center"
                      >
                        History
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* 3. TRANSACTIONS TAB */}
          {/* ========================================================== */}
          {activeTab === 'transactions' && (
            <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-5">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Family Transactions Audit Log</h3>
                  <p className="text-xs text-slate-500">Searchable history with verified AI assessments and dual-currency figures</p>
                </div>

                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search merchant, category..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9 pr-3.5 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-[#0070E0] focus:outline-hidden w-60"
                    />
                  </div>

                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="py-2 px-3 rounded-xl border border-slate-200 text-xs font-medium focus:ring-2 focus:ring-[#0070E0] focus:outline-hidden bg-white text-slate-700"
                  >
                    <option value="ALL">All Statuses</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="PENDING_APPROVAL">Pending Approval</option>
                    <option value="DECLINED">Declined</option>
                  </select>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                      <th className="pb-3">Code</th>
                      <th className="pb-3">Date</th>
                      <th className="pb-3">Child</th>
                      <th className="pb-3">Merchant</th>
                      <th className="pb-3">Category</th>
                      <th className="pb-3">Amount (₹ INR / $ USD)</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3">AI Risk</th>
                      <th className="pb-3">AI Explanation</th>
                      <th className="pb-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredTransactions.map((t) => (
                      <tr key={t.id} className="hover:bg-slate-50/80 transition">
                        <td className="py-3.5 font-mono font-bold text-slate-800">{t.transaction_code}</td>
                        <td className="py-3.5 text-slate-500 whitespace-nowrap">
                          {new Date(t.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit' + (t.id ? '' : ''), minute: '2-digit' })}
                        </td>
                        <td className="py-3.5 font-bold text-slate-900">{t.child_name}</td>
                        <td className="py-3.5 font-medium text-slate-900">{t.merchant}</td>
                        <td className="py-3.5 text-slate-600">{t.category}</td>
                        <td className="py-3.5 font-black text-slate-900">
                          <div className="flex flex-col">
                            <span>₹ {(t.amount_inr || (t.amount * FX_RATE)).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                            <span className="text-[10px] text-[#0070E0] font-mono font-bold">${t.amount.toFixed(2)} USD</span>
                          </div>
                        </td>
                        <td className="py-3.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              t.status === 'COMPLETED'
                                ? 'bg-emerald-100 text-emerald-800'
                                : t.status === 'PENDING_APPROVAL'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-rose-100 text-rose-800'
                            }`}
                          >
                            {t.status}
                          </span>
                        </td>
                        <td className="py-3.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              t.ai_report?.risk_level === 'HIGH'
                                ? 'bg-rose-100 text-rose-700'
                                : t.ai_report?.risk_level === 'MEDIUM'
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-emerald-100 text-emerald-700'
                            }`}
                          >
                            {t.ai_report?.risk_level || 'LOW'}
                          </span>
                        </td>
                        <td className="py-3.5 max-w-xs truncate text-slate-600 text-[11px]" title={t.ai_report?.explanation}>
                          {t.ai_report?.explanation || 'Standard transaction.'}
                        </td>
                        <td className="py-3.5 text-right whitespace-nowrap">
                          <button
                            onClick={() => onOpenReceipt(t.transaction_code)}
                            className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-blue-50 text-[#003087] hover:bg-blue-100 font-semibold transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Receipt & AI Report</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* 4. APPROVAL REQUESTS TAB */}
          {/* ========================================================== */}
          {activeTab === 'approvals' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-bold text-slate-900">Parental Payment Approval Workflow</h3>
                <p className="text-xs text-slate-500">
                  Transactions exceeding configured threshold (${approvalThreshold} USD ≈ ₹{(approvalThreshold * FX_RATE).toLocaleString()} INR) require explicit parental authorization
                </p>
              </div>

              {pendingApprovalsList.length === 0 ? (
                <div className="bg-white rounded-3xl p-12 text-center border border-slate-200/80 shadow-xs flex flex-col items-center justify-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <h4 className="text-base font-bold text-slate-900">No Pending Approvals</h4>
                  <p className="text-xs text-slate-500 max-w-md">
                    All payment requests have been reviewed. When Arjun initiates an overseas purchase above ${approvalThreshold} USD in Boston, it will appear here instantly for your review.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {pendingApprovalsList.map((req) => (
                    <div
                      key={req.id}
                      className="bg-white rounded-3xl p-6 border-2 border-amber-200 shadow-sm space-y-5 animate-in fade-in"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
                        <div className="flex items-center space-x-3">
                          <div className="p-2.5 bg-amber-100 text-amber-700 rounded-2xl">
                            <AlertTriangle className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <h4 className="text-sm font-bold text-slate-900">{req.merchant}</h4>
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
                                Requires Parental Approval
                              </span>
                            </div>
                            <p className="text-xs text-slate-500">
                              Requested by <b>{req.child_name}</b> (Boston, USA) on{' '}
                              {new Date(req.requested_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                        </div>

                        <div className="text-right">
                          <span className="text-2xl font-black text-slate-900 block">
                            ${req.amount.toFixed(2)} <span className="text-sm font-bold text-slate-500">USD</span>
                          </span>
                          <span className="text-xs font-black text-[#0070E0] block">
                            ≈ ₹{(req.amount * FX_RATE).toLocaleString(undefined, { minimumFractionDigits: 2 })} INR parent debit
                          </span>
                          <span className="text-[10px] text-rose-500 font-bold block mt-0.5">
                            Exceeds threshold of ${approvalThreshold} USD (₹{(approvalThreshold * FX_RATE).toLocaleString()} INR)
                          </span>
                        </div>
                      </div>

                      {/* AI Risk Explanation */}
                      {req.ai_report && (
                        <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200/60 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
                              <Bot className="w-3.5 h-3.5 text-[#003087]" />
                              <span>AI Decision Support Telemetry</span>
                            </span>
                            <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
                              {req.ai_report.risk_level} Risk
                            </span>
                          </div>
                          <p className="text-xs text-slate-700 leading-relaxed">{req.ai_report.explanation}</p>
                          <p className="text-[11px] text-[#003087] font-medium">{req.ai_report.spending_summary}</p>
                        </div>
                      )}

                      {/* Notes & Actions */}
                      <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
                        <input
                          type="text"
                          placeholder="Optional parent feedback or note for Arjun..."
                          value={actionNotes[req.id] || ''}
                          onChange={(e) =>
                            setActionNotes((prev) => ({ ...prev, [req.id]: e.target.value }))
                          }
                          className="flex-1 w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-[#0070E0]"
                        />

                        <div className="flex items-center space-x-2 w-full sm:w-auto">
                          <button
                            onClick={() => handleApprovalAction(req.id, 'APPROVE')}
                            disabled={actionLoading[req.id]}
                            className="flex-1 sm:flex-initial inline-flex items-center justify-center space-x-1.5 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition"
                          >
                            <Check className="w-4 h-4" />
                            <span>Approve Purchase</span>
                          </button>
                          <button
                            onClick={() => handleApprovalAction(req.id, 'DECLINE')}
                            disabled={actionLoading[req.id]}
                            className="flex-1 sm:flex-initial inline-flex items-center justify-center space-x-1.5 px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-xs transition"
                          >
                            <X className="w-4 h-4" />
                            <span>Decline</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Historical Approval Log */}
              {approvals.filter((a) => a.status !== 'PENDING').length > 0 && (
                <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
                  <h4 className="text-sm font-bold text-slate-900">Historical Approval Decisions</h4>
                  <div className="divide-y divide-slate-100">
                    {approvals
                      .filter((a) => a.status !== 'PENDING')
                      .map((a) => (
                        <div key={a.id} className="py-3 flex items-center justify-between text-xs">
                          <div>
                            <span className="font-bold text-slate-800">{a.merchant}</span>
                            <span className="text-slate-500 ml-2">({a.child_name})</span>
                            <span className="text-[10px] text-slate-400 block mt-0.5">
                              Decision recorded on {new Date(a.decided_at || a.requested_at).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="text-right">
                            <span className="font-extrabold text-slate-900 block">
                              ${a.amount.toFixed(2)} USD <span className="text-slate-400 font-normal">(≈ ₹{(a.amount * FX_RATE).toLocaleString()} INR)</span>
                            </span>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-block mt-0.5 ${
                                a.status === 'APPROVED' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                              }`}
                            >
                              {a.status}
                            </span>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================== */}
          {/* 5. AI INSIGHTS TAB */}
          {/* ========================================================== */}
          {activeTab === 'insights' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900">FamilyGuard AI Telemetry & Insights</h3>
                  <p className="text-xs text-slate-500">Autonomous pattern recognition and predictive cross-border financial health</p>
                </div>
                <button
                  onClick={onOpenAIAssistant}
                  className="px-4 py-2 bg-gradient-to-r from-[#003087] to-[#0070E0] hover:from-[#001C64] hover:to-[#003087] text-white rounded-xl text-xs font-bold shadow-xs transition flex items-center space-x-1.5"
                >
                  <Bot className="w-4 h-4" />
                  <span>Launch AI Assistant</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-3">
                  <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl w-fit">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">Study Abroad Financial Health</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Over 80% of Arjun's overseas expenditures fall into academic textbooks and campus dining. Adherence to monthly allowance budget remains strong.
                  </p>
                </div>

                <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-3">
                  <div className="p-3 bg-blue-50 text-[#0070E0] rounded-2xl w-fit">
                    <Globe className="w-5 h-5" />
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">Dual-Currency Rate Stability</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Transactions are pegged at fixed FX conversion (1 USD = ₹85.00 INR), providing predictable remittance forecasting for Indian parents.
                  </p>
                </div>

                <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-3">
                  <div className="p-3 bg-indigo-50 text-[#003087] rounded-2xl w-fit">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">Approval Guardrails</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Single purchase threshold of ${approvalThreshold} USD (₹{(approvalThreshold * FX_RATE).toLocaleString()} INR) safely isolates high-value electronics and unexpected bills for your prior review.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* 6. REPORTS TAB */}
          {/* ========================================================== */}
          {activeTab === 'reports' && (
            <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Parental Audit Reports & Downloadable PDF Receipts</h3>
                  <p className="text-xs text-slate-500">Official PayPal Sandbox receipts with dual-currency breakdown & AI explainability</p>
                </div>
              </div>

              <div className="divide-y divide-slate-100">
                {transactions.map((t) => (
                  <div key={t.id} className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono font-bold text-slate-800 text-xs">{t.transaction_code}</span>
                        <span className="text-xs font-semibold text-slate-900">• {t.merchant}</span>
                        <span className="text-[10px] text-slate-500">({t.category})</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {new Date(t.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} • Child: {t.child_name} (Boston, USA)
                      </p>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div className="text-right">
                        <span className="text-sm font-extrabold text-slate-900 block">
                          ₹ {(t.amount_inr || (t.amount * FX_RATE)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </span>
                        <span className="text-[11px] text-[#0070E0] font-mono font-bold block">
                          ${t.amount.toFixed(2)} USD
                        </span>
                      </div>
                      <button
                        onClick={() => onOpenReceipt(t.transaction_code)}
                        className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
                        title="View Receipt"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <a
                        href={api.getPdfDownloadUrl(t.transaction_code)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-[#003087] hover:bg-[#001C64] text-white rounded-xl text-xs font-bold transition shadow-xs"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>PDF</span>
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* 7. SPENDING CONTROLS TAB */}
          {/* ========================================================== */}
          {activeTab === 'controls' && overview && (
            <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs space-y-6 max-w-3xl">
              <div>
                <h3 className="text-base font-bold text-slate-900">Configure Spending Controls for Arjun</h3>
                <p className="text-xs text-slate-500">
                  Enforce strict financial limits in <b>US Dollars ($ USD)</b> for Arjun's overseas wallet, with automatic conversion to <b>Indian Rupees (₹ INR)</b>.
                </p>
              </div>

              {controlsSuccess && (
                <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center space-x-2 text-emerald-800 text-xs font-semibold animate-in fade-in">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Spending controls updated and actively enforced by backend engine!</span>
                </div>
              )}

              <div className="space-y-6">
                {/* Daily Spending Limit */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-bold text-slate-800">Daily Spending Limit (USD)</label>
                    <div className="text-right">
                      <span className="text-sm font-black text-[#003087]">${dailyLimit} USD / day</span>
                      <span className="text-xs text-slate-500 block">≈ ₹{(dailyLimit * FX_RATE).toLocaleString()} INR</span>
                    </div>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="200"
                    step="5"
                    value={dailyLimit}
                    onChange={(e) => setDailyLimit(Number(e.target.value))}
                    className="w-full accent-[#003087] cursor-pointer"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Maximum expenditure permitted for Arjun in a 24-hour window abroad.
                  </p>
                </div>

                {/* Weekly Spending Limit */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-bold text-slate-800">Weekly Spending Limit (USD)</label>
                    <div className="text-right">
                      <span className="text-sm font-black text-[#003087]">${weeklyLimit} USD / week</span>
                      <span className="text-xs text-slate-500 block">≈ ₹{(weeklyLimit * FX_RATE).toLocaleString()} INR</span>
                    </div>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="1000"
                    step="25"
                    value={weeklyLimit}
                    onChange={(e) => setWeeklyLimit(Number(e.target.value))}
                    className="w-full accent-[#003087] cursor-pointer"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Cumulative cap reset at the beginning of each calendar week.
                  </p>
                </div>

                {/* Approval Threshold */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-bold text-slate-800">Single-Purchase Approval Threshold (USD)</label>
                    <div className="text-right">
                      <span className="text-sm font-black text-amber-600">${approvalThreshold} USD per purchase</span>
                      <span className="text-xs text-slate-500 block">≈ ₹{(approvalThreshold * FX_RATE).toLocaleString()} INR</span>
                    </div>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="150"
                    step="5"
                    value={approvalThreshold}
                    onChange={(e) => setApprovalThreshold(Number(e.target.value))}
                    className="w-full accent-amber-600 cursor-pointer"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Any overseas purchase exceeding this USD amount pauses and requires your explicit authorization.
                  </p>
                </div>

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button
                    onClick={handleSaveControls}
                    disabled={savingControls}
                    className="px-6 py-2.5 bg-[#003087] hover:bg-[#001C64] disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-xs transition flex items-center space-x-2"
                  >
                    {savingControls ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Check className="w-4 h-4" />
                    )}
                    <span>Save Overseas Controls</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* 8. SETTINGS TAB */}
          {/* ========================================================== */}
          {activeTab === 'settings' && overview && (
            <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-6 max-w-2xl">
              <div>
                <h3 className="text-base font-bold text-slate-900">FamilyGuard System Settings</h3>
                <p className="text-xs text-slate-500">Manage PayPal Sandbox integrations, cross-border remittance gateway, and AI modes</p>
              </div>

              <div className="space-y-4">
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-900 block">PayPal Sandbox REST API</span>
                    <span className="text-[11px] text-slate-500">Live sandbox orders, capture engine & checkout portal</span>
                  </div>
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800">
                    PayPal Sandbox Active
                  </span>
                </div>

                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-900 block">Cross-Border Remittance Engine</span>
                    <span className="text-[11px] text-slate-500">Fixed rate: $1.00 USD = ₹85.00 INR (Instant Wallet Credit)</span>
                  </div>
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-blue-100 text-[#003087]">
                    INR → USD Gateway
                  </span>
                </div>

                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-900 block">AI Monitoring Engine</span>
                    <span className="text-[11px] text-slate-500">Deterministic Safety Heuristics + OpenAI JSON format</span>
                  </div>
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-blue-100 text-blue-800">
                    Active & Audited
                  </span>
                </div>

                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-900 block">Database Storage</span>
                    <span className="text-[11px] text-slate-500">SQLAlchemy Relational Schema (PostgreSQL & SQLite)</span>
                  </div>
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800">
                    Connected
                  </span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
