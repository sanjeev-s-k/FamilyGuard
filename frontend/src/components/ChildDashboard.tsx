import React, { useState, useEffect } from 'react';
import {
  Wallet, Send, History, Target, PieChart as PieIcon,
  CheckCircle2, AlertTriangle, ArrowRight, Sparkles,
  ShieldAlert, PlusCircle, CreditCard, ShoppingBag,
  ExternalLink, Eye, RefreshCw, Globe, DollarSign
} from 'lucide-react';
import { ChildWalletData, TransactionItem, SavingsGoalItem } from '../types';
import { api } from '../api';

const FX_RATE = 85.0;

interface ChildDashboardProps {
  onOpenReceipt: (code: string) => void;
  refreshTrigger: number;
}

export const ChildDashboard: React.FC<ChildDashboardProps> = ({
  onOpenReceipt,
  refreshTrigger,
}) => {
  const [activeTab, setActiveTab] = useState<'wallet' | 'pay' | 'transactions' | 'goals' | 'summary'>('wallet');
  const [wallet, setWallet] = useState<ChildWalletData | null>(null);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [goals, setGoals] = useState<SavingsGoalItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Payment Form State (all in USD)
  const [merchant, setMerchant] = useState('');
  const [amount, setAmount] = useState<number | ''>('');
  const [category, setCategory] = useState('Education');
  const [description, setDescription] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<'SIMULATED_WALLET' | 'PAYPAL_SANDBOX'>('SIMULATED_WALLET');
  const [paying, setPaying] = useState(false);
  const [paymentResult, setPaymentResult] = useState<{
    status: string;
    message: string;
    requires_approval: boolean;
    tx_code?: string;
  } | null>(null);

  // Quick preset payment buttons for US college scenario
  const presets = [
    { merchant: 'Campus Dining & Groceries', amount: 18.50, category: 'Food & Snacks', desc: 'Lunch combo & dorm groceries' },
    { merchant: 'MIT Press Academic Bookstore', amount: 35.00, category: 'Education', desc: 'Required lab manual & stationery' },
    { merchant: 'Best Buy Tech & Dorm Gear', amount: 55.00, category: 'Shopping', desc: 'High-speed USB-C dorm hub' }, // Triggers approval threshold (> $40 USD)
  ];

  const loadData = async (isBackground = false) => {
    try {
      if (!wallet && !isBackground) {
        setLoading(true);
      }
      const [wData, txData, gData] = await Promise.all([
        api.getChildWallet(),
        api.getChildTransactions(),
        api.getSavingsGoals(),
      ]);
      setWallet(wData);
      setTransactions(txData);
      setGoals(gData);
    } catch (err) {
      console.error('Error loading child data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(!!wallet);
  }, [refreshTrigger, activeTab]);

  const handlePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!merchant || !amount || Number(amount) <= 0) return;

    setPaying(true);
    setPaymentResult(null);

    try {
      const numAmount = Number(amount);
      if (paymentMethod === 'PAYPAL_SANDBOX') {
        // Create PayPal sandbox order, then capture it
        const orderRes = await api.createPayPalOrder({
          child_id: wallet?.child_id || 1,
          amount: numAmount,
          currency: 'USD',
          merchant,
          category,
          description,
        });

        const capRes = await api.capturePayPalOrder({
          order_id: orderRes.order_id,
          child_id: wallet?.child_id || 1,
          amount: numAmount,
          currency: 'USD',
          merchant,
          category,
          description,
        });

        setPaymentResult({
          status: capRes.status,
          message: `PayPal Sandbox payment of $${numAmount.toFixed(2)} USD captured successfully! Converted parent debit: ≈ ₹${(numAmount * FX_RATE).toFixed(2)} INR.`,
          requires_approval: false,
          tx_code: capRes.transaction_code,
        });
      } else {
        // Standard Wallet Payment in USD
        const res = await api.initiatePayment({
          merchant,
          amount: numAmount,
          currency: 'USD',
          category,
          description,
          payment_method: 'SIMULATED_WALLET',
        });

        setPaymentResult({
          status: res.status,
          message: res.message,
          requires_approval: res.requires_approval,
          tx_code: res.transaction_code,
        });
      }

      setMerchant('');
      setAmount('');
      setDescription('');
      await loadData();
    } catch (err: any) {
      alert(`Payment failed: ${err.message}`);
    } finally {
      setPaying(false);
    }
  };

  const handleAddSavings = async (goalId: number) => {
    const amtStr = prompt('Enter amount to add to savings goal ($ USD):', '10');
    if (!amtStr) return;
    const addAmt = parseFloat(amtStr);
    if (isNaN(addAmt) || addAmt <= 0) return;

    try {
      await api.addFundsToGoal(goalId, addAmt);
      await loadData();
    } catch (err: any) {
      alert(`Could not add funds: ${err.message}`);
    }
  };

  const applyPreset = (p: typeof presets[0]) => {
    setMerchant(p.merchant);
    setAmount(p.amount);
    setCategory(p.category);
    setDescription(p.desc);
  };

  return (
    <div className="space-y-6">
      {/* Navigation Sub-Tabs */}
      <div className="bg-white rounded-2xl p-1.5 border border-slate-200/80 shadow-xs flex flex-wrap gap-1">
        {[
          { id: 'wallet', label: 'My Wallet', icon: Wallet },
          { id: 'pay', label: 'Make Payment', icon: Send },
          { id: 'transactions', label: 'Transactions', icon: History },
          { id: 'goals', label: 'Savings Goals', icon: Target },
          { id: 'summary', label: 'Spending Summary', icon: PieIcon },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-[#003087] text-white shadow-xs'
                  : 'text-slate-600 hover:text-[#003087] hover:bg-slate-100'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {loading && !wallet ? (
        <div className="py-20 text-center flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-3 border-[#003087] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs text-slate-500 font-medium">Loading Arjun's overseas wallet telemetry...</p>
        </div>
      ) : (
        <>
          {/* ========================================================== */}
          {/* 1. MY WALLET TAB */}
          {/* ========================================================== */}
          {activeTab === 'wallet' && wallet && (
            <div className="space-y-6">
              {/* Wallet Card Hero */}
              <div className="bg-gradient-to-tr from-[#001C64] via-[#003087] to-[#0070E0] text-white rounded-3xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs uppercase tracking-wider text-amber-300 font-extrabold block">
                        PayPal Sandbox Student Wallet • Boston, USA
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/10 text-white">
                        $ USD Account
                      </span>
                    </div>
                    <h2 className="text-3xl sm:text-4xl font-black tracking-tight mt-1">
                      ${wallet.balance.toFixed(2)} <span className="text-lg font-bold text-blue-200">USD</span>
                    </h2>
                    <p className="text-xs text-blue-100 mt-1 flex items-center space-x-1.5">
                      <span>Equivalent Indian Parent Funding:</span>
                      <span className="font-bold text-amber-300">₹{(wallet.balance * FX_RATE).toLocaleString(undefined, { minimumFractionDigits: 2 })} INR</span>
                      <span className="text-blue-300">(Rate: 1 USD = ₹85.00)</span>
                    </p>
                  </div>

                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => setActiveTab('pay')}
                      className="px-5 py-2.5 bg-[#FFC439] hover:bg-[#F6C944] text-[#001C64] font-black text-xs rounded-xl shadow-md transition flex items-center space-x-1.5 border border-amber-300"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>Make Payment</span>
                    </button>
                  </div>
                </div>

                {/* Progress Gauges */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8 pt-6 border-t border-white/10 relative z-10">
                  <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-xs">
                    <div className="flex justify-between text-xs font-semibold mb-1">
                      <span className="text-blue-200">Daily Allowance ($ USD)</span>
                      <span>
                        ${wallet.daily_spent_today.toFixed(2)} / ${wallet.daily_limit.toFixed(2)} USD
                      </span>
                    </div>
                    <div className="w-full bg-white/20 rounded-full h-2">
                      <div
                        className="bg-emerald-400 h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.min(100, (wallet.daily_spent_today / (wallet.daily_limit || 1)) * 100)}%`,
                        }}
                      ></div>
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-emerald-300 mt-1">
                      <span>${wallet.daily_remaining.toFixed(2)} USD remaining today</span>
                      <span className="text-blue-200">≈ ₹{(wallet.daily_remaining * FX_RATE).toFixed(0)} INR</span>
                    </div>
                  </div>

                  <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-xs">
                    <div className="flex justify-between text-xs font-semibold mb-1">
                      <span className="text-blue-200">Weekly Allowance ($ USD)</span>
                      <span>
                        ${wallet.weekly_spent.toFixed(2)} / ${wallet.weekly_limit.toFixed(2)} USD
                      </span>
                    </div>
                    <div className="w-full bg-white/20 rounded-full h-2">
                      <div
                        className="bg-[#00CFE8] h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.min(100, (wallet.weekly_spent / (wallet.weekly_limit || 1)) * 100)}%`,
                        }}
                      ></div>
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-[#00CFE8] mt-1">
                      <span>${wallet.weekly_remaining.toFixed(2)} USD remaining this week</span>
                      <span className="text-blue-200">≈ ₹{(wallet.weekly_remaining * FX_RATE).toFixed(0)} INR</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Threshold Safety Alert Notice */}
              <div className="p-4 bg-amber-50 rounded-2xl border border-amber-200/80 flex items-start space-x-3 text-xs text-amber-900">
                <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold block">Parental Approval Guardrail Active:</span>
                  Any single purchase of <b>${wallet.approval_threshold.toFixed(2)} USD or above</b> (≈ ₹{(wallet.approval_threshold * FX_RATE).toLocaleString()} INR) will be paused and routed to your parents in India for approval before completion.
                </div>
              </div>

              {/* Recent Activity List */}
              <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">Recent Overseas Transactions</h3>
                  <button
                    onClick={() => setActiveTab('transactions')}
                    className="text-xs font-semibold text-[#0070E0] hover:underline"
                  >
                    View All
                  </button>
                </div>

                <div className="divide-y divide-slate-100">
                  {transactions.slice(0, 4).map((t) => (
                    <div key={t.id} className="py-3 flex items-center justify-between text-xs">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center text-slate-600">
                          <ShoppingBag className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-bold text-slate-900">{t.merchant}</p>
                          <p className="text-[10px] text-slate-400">{t.category} • {new Date(t.created_at).toLocaleDateString()}</p>
                        </div>
                      </div>

                      <div className="flex items-center space-x-3">
                        <div className="text-right">
                          <span className="font-bold text-slate-900 block">
                            - ${t.amount.toFixed(2)} USD
                          </span>
                          <span className="text-[10px] text-slate-400 block">
                            ≈ ₹{(t.amount * FX_RATE).toFixed(2)} INR
                          </span>
                        </div>
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
                        <button
                          onClick={() => onOpenReceipt(t.transaction_code)}
                          className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700"
                          title="View Receipt"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* 2. MAKE PAYMENT TAB */}
          {/* ========================================================== */}
          {activeTab === 'pay' && wallet && (
            <div className="max-w-2xl mx-auto space-y-6">
              <div>
                <h3 className="text-base font-bold text-slate-900">Initiate Monitored Payment in US Dollars ($ USD)</h3>
                <p className="text-xs text-slate-500">
                  Transactions are checked in real-time against your parental limits (${wallet.approval_threshold.toFixed(2)} USD threshold) and monitored via PayPal Sandbox.
                </p>
              </div>

              {/* Hackathon Quick Demo Presets */}
              <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200/80">
                <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block mb-2">
                  Quick Study Abroad Demo Presets:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {presets.map((p, idx) => (
                    <button
                      key={idx}
                      onClick={() => applyPreset(p)}
                      className="p-3 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-300 rounded-xl text-left transition flex flex-col justify-between"
                    >
                      <span className="text-xs font-bold text-slate-900">{p.merchant}</span>
                      <div className="mt-1">
                        <span className="text-xs font-black text-[#003087]">${p.amount.toFixed(2)} USD</span>
                        <span className="text-[10px] text-slate-500 block">≈ ₹{(p.amount * FX_RATE).toFixed(0)} INR</span>
                      </div>
                      <span className="text-[10px] text-slate-400 mt-1">
                        {p.amount >= wallet.approval_threshold ? '⚠️ Requires Parent Approval' : '✅ Auto-Approved'}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Payment Result Alert */}
              {paymentResult && (
                <div
                  className={`p-4 rounded-2xl border flex items-start space-x-3 text-xs animate-in fade-in ${
                    paymentResult.requires_approval
                      ? 'bg-amber-50 border-amber-200 text-amber-900'
                      : 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  }`}
                >
                  {paymentResult.requires_approval ? (
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <span className="font-bold block text-sm">
                      {paymentResult.requires_approval ? 'Approval Required!' : 'Payment Verified & Completed!'}
                    </span>
                    <p className="mt-0.5 leading-relaxed">{paymentResult.message}</p>
                    {paymentResult.tx_code && (
                      <button
                        onClick={() => onOpenReceipt(paymentResult.tx_code!)}
                        className="mt-2 inline-flex items-center space-x-1 font-bold text-[#0070E0] hover:underline"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>View Official Receipt & AI Risk Assessment ({paymentResult.tx_code})</span>
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Payment Form */}
              <form onSubmit={handlePayment} className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs space-y-5">
                <div>
                  <label className="text-xs font-bold text-slate-800 block mb-1.5">US Merchant Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. MIT Dining, Harvard Coop Bookstore, Best Buy"
                    value={merchant}
                    onChange={(e) => setMerchant(e.target.value)}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-[#0070E0]"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-slate-800 block mb-1.5">Amount in US Dollars ($ USD)</label>
                    <input
                      type="number"
                      required
                      min="0.5"
                      step="any"
                      placeholder="e.g. 18.50"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value === '' ? '' : Number(e.target.value))}
                      className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-[#0070E0]"
                    />
                    {amount !== '' && Number(amount) > 0 && (
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        ≈ ₹{(Number(amount) * FX_RATE).toFixed(2)} INR parent home debit
                      </span>
                    )}
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-800 block mb-1.5">Category</label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-[#0070E0]"
                    >
                      <option value="Education">Education & Books</option>
                      <option value="Food & Snacks">Food & Dining</option>
                      <option value="Entertainment">Entertainment</option>
                      <option value="Gaming">Gaming & Software</option>
                      <option value="Shopping">Shopping & Tech</option>
                      <option value="Transport">Campus Transport</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-800 block mb-1.5">Description (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. Course study materials or dorm provisions"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-[#0070E0]"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-800 block mb-2">Checkout Method</label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setPaymentMethod('SIMULATED_WALLET')}
                      className={`p-3 rounded-2xl border text-left transition flex items-center space-x-2.5 ${
                        paymentMethod === 'SIMULATED_WALLET'
                          ? 'border-[#003087] bg-blue-50/50 text-[#003087]'
                          : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <Wallet className="w-4 h-4 text-[#003087]" />
                      <div>
                        <span className="text-xs font-bold block">Overseas Wallet</span>
                        <span className="text-[10px] text-slate-400">Available: ${wallet.balance.toFixed(2)} USD</span>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setPaymentMethod('PAYPAL_SANDBOX')}
                      className={`p-3 rounded-2xl border text-left transition flex items-center space-x-2.5 ${
                        paymentMethod === 'PAYPAL_SANDBOX'
                          ? 'border-[#0070E0] bg-blue-50/50 text-[#0070E0]'
                          : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <CreditCard className="w-4 h-4 text-[#0070E0]" />
                      <div>
                        <span className="text-xs font-bold block">PayPal Checkout</span>
                        <span className="text-[10px] text-slate-400">Sandbox API Order</span>
                      </div>
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={paying}
                  className="w-full py-3.5 bg-[#FFC439] hover:bg-[#F6C944] disabled:opacity-50 text-[#001C64] font-black text-xs rounded-xl shadow-md transition flex items-center justify-center space-x-2 border border-amber-300"
                >
                  {paying ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  <span>
                    {paymentMethod === 'PAYPAL_SANDBOX'
                      ? 'Pay with PayPal Sandbox ($ USD)'
                      : 'Confirm Student Payment ($ USD)'}
                  </span>
                </button>
              </form>
            </div>
          )}

          {/* ========================================================== */}
          {/* 3. TRANSACTIONS TAB */}
          {/* ========================================================== */}
          {activeTab === 'transactions' && (
            <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-5">
              <h3 className="text-base font-bold text-slate-900">Arjun's US Dollar Transaction History</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                      <th className="pb-3">Code</th>
                      <th className="pb-3">Merchant</th>
                      <th className="pb-3">Category</th>
                      <th className="pb-3">Amount ($ USD / ₹ INR)</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3">Allowance After</th>
                      <th className="pb-3 text-right">Receipt</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {transactions.map((t) => (
                      <tr key={t.id} className="hover:bg-slate-50 transition">
                        <td className="py-3 font-mono font-bold text-slate-800">{t.transaction_code}</td>
                        <td className="py-3 font-medium text-slate-900">{t.merchant}</td>
                        <td className="py-3 text-slate-600">{t.category}</td>
                        <td className="py-3 font-bold text-slate-900">
                          <div className="flex flex-col">
                            <span>${t.amount.toFixed(2)} USD</span>
                            <span className="text-[10px] text-slate-400">≈ ₹{(t.amount * FX_RATE).toFixed(2)} INR</span>
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
                        <td className="py-3 font-medium text-slate-600">
                          ${t.remaining_daily_allowance_after.toFixed(2)} USD
                        </td>
                        <td className="py-3 text-right">
                          <button
                            onClick={() => onOpenReceipt(t.transaction_code)}
                            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-[#003087] hover:bg-blue-100 font-semibold transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Receipt</span>
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
          {/* 4. SAVINGS GOALS TAB */}
          {/* ========================================================== */}
          {activeTab === 'goals' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-bold text-slate-900">Student Savings Goals ($ USD)</h3>
                <p className="text-xs text-slate-500">
                  Build healthy savings habits during your college years by setting aside funds in Dollars
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {goals.map((g) => (
                  <div key={g.id} className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="w-10 h-10 rounded-2xl bg-blue-50 text-[#003087] flex items-center justify-center">
                        <Target className="w-5 h-5" />
                      </div>
                      <span className="text-xs font-black text-[#0070E0]">{g.percentage}%</span>
                    </div>

                    <div>
                      <h4 className="text-sm font-bold text-slate-900">{g.title}</h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Saved: ${g.current_amount.toLocaleString()} / ${g.target_amount.toLocaleString()} USD
                      </p>
                      <p className="text-[10px] text-slate-400">
                        ≈ ₹{(g.current_amount * FX_RATE).toLocaleString()} / ₹{(g.target_amount * FX_RATE).toLocaleString()} INR
                      </p>
                    </div>

                    <div className="w-full bg-slate-100 rounded-full h-2">
                      <div
                        className="bg-[#003087] h-2 rounded-full transition-all duration-300"
                        style={{ width: `${g.percentage}%` }}
                      ></div>
                    </div>

                    <button
                      onClick={() => handleAddSavings(g.id)}
                      className="w-full py-2 bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-[#003087] text-xs font-bold rounded-xl transition flex items-center justify-center space-x-1.5"
                    >
                      <PlusCircle className="w-3.5 h-3.5" />
                      <span>Add Funds ($ USD)</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* 5. SPENDING SUMMARY TAB */}
          {/* ========================================================== */}
          {activeTab === 'summary' && wallet && (
            <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-5 max-w-2xl">
              <h3 className="text-base font-bold text-slate-900">Arjun's Spending Summary & Financial Literacy</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Smart financial habits start in college! You are doing great staying within your daily allowance of ${wallet.daily_limit.toFixed(2)} USD (≈ ₹{(wallet.daily_limit * FX_RATE).toLocaleString()} INR).
              </p>

              <div className="space-y-3 pt-2">
                <div className="p-4 bg-blue-50/60 rounded-2xl flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-900">Daily Limit Usage</span>
                  <span className="font-bold text-[#003087]">
                    {Math.round((wallet.daily_spent_today / (wallet.daily_limit || 1)) * 100)}%
                  </span>
                </div>
                <div className="p-4 bg-blue-50/60 rounded-2xl flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-900">Weekly Limit Usage</span>
                  <span className="font-bold text-[#0070E0]">
                    {Math.round((wallet.weekly_spent / (wallet.weekly_limit || 1)) * 100)}%
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
