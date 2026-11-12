import React, { useState } from 'react';
import {
  X, Send, ArrowRight, ShieldCheck, CheckCircle2,
  RefreshCw, DollarSign, Wallet, Globe, Sparkles
} from 'lucide-react';
import { api } from '../api';
import { SendMoneyResponse } from '../types';

interface SendMoneyModalProps {
  isOpen: boolean;
  onClose: () => void;
  childId?: number;
  childName?: string;
  onSuccess: (res: SendMoneyResponse) => void;
}

const FX_RATE = 85.0; // 1 USD = 85.00 INR

export const SendMoneyModal: React.FC<SendMoneyModalProps> = ({
  isOpen,
  onClose,
  childId = 1,
  childName = 'Arjun',
  onSuccess,
}) => {
  const [amountInr, setAmountInr] = useState<number | ''>(8500);
  const [notes, setNotes] = useState('Monthly university living & textbook allowance');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const currentUsd = typeof amountInr === 'number' && amountInr > 0
    ? (amountInr / FX_RATE).toFixed(2)
    : '0.00';

  const quickPresets = [
    { inr: 2550, usd: 30, label: '₹2,550 ($30)' },
    { inr: 5100, usd: 60, label: '₹5,100 ($60)' },
    { inr: 8500, usd: 100, label: '₹8,500 ($100)' },
    { inr: 17000, usd: 200, label: '₹17,000 ($200)' },
  ];

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amountInr || Number(amountInr) <= 0) {
      setError('Please enter a valid remittance amount in Rupees');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await api.sendMoneyToChild({
        child_id: childId,
        amount_inr: Number(amountInr),
        notes,
        payment_method: 'PAYPAL_SANDBOX_BALANCE'
      });
      onSuccess(res);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Remittance transfer failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="relative bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header - PayPal Theme */}
        <div className="bg-[#003087] text-white px-6 py-5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center text-white border border-white/20">
              <span className="font-extrabold text-base tracking-tighter text-[#0070E0]">
                P<span className="text-[#00cfe8]">P</span>
              </span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold tracking-tight">PayPal International Remittance</h3>
                <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-[#0070E0] text-white">
                  Sandbox
                </span>
              </div>
              <p className="text-xs text-blue-200">India (INR ₹) ➔ Study Abroad (USD $)</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-white/10 text-white/80 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Currency Conversion Ticker Banner */}
        <div className="bg-[#F5F7FA] border-b border-slate-200/80 px-6 py-2.5 flex items-center justify-between text-xs text-slate-600">
          <div className="flex items-center space-x-2">
            <Globe className="w-4 h-4 text-[#0070E0]" />
            <span className="font-semibold text-slate-800">Pegged FX Index:</span>
            <span className="font-mono font-bold text-[#003087]">1 USD = 85.00 INR</span>
          </div>
          <span className="text-[11px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
            Zero Transfer Fee
          </span>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSend} className="p-6 space-y-5">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs font-medium">
              {error}
            </div>
          )}

          {/* Recipient Details */}
          <div className="bg-blue-50/60 p-3.5 rounded-2xl border border-blue-100 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-[#003087] text-white flex items-center justify-center font-bold text-sm">
                {childName.charAt(0)}
              </div>
              <div>
                <p className="text-xs font-bold text-slate-900">{childName} (Overseas Student)</p>
                <p className="text-[11px] text-slate-500 font-mono">sb-arjun-us@student.demo</p>
              </div>
            </div>
            <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-blue-100 text-[#003087]">
              US College Wallet
            </span>
          </div>

          {/* Amount Inputs */}
          <div>
            <label className="text-xs font-bold text-slate-800 block mb-1.5">
              You Send (Indian Rupees - ₹ INR)
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-2.5 text-sm font-bold text-slate-400">₹</span>
              <input
                type="number"
                required
                min="100"
                step="any"
                value={amountInr}
                onChange={(e) => setAmountInr(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 8500"
                className="w-full pl-8 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-base font-extrabold text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-[#0070E0] focus:bg-white transition"
              />
            </div>
          </div>

          {/* Real-time USD Conversion Card */}
          <div className="bg-[#001C64] text-white p-4 rounded-2xl flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-bold text-blue-300 tracking-wider block">
                Arjun Receives in US Wallet:
              </span>
              <p className="text-2xl font-black text-[#FFC439] mt-0.5 tracking-tight">
                ${currentUsd} <span className="text-xs font-bold text-white">USD</span>
              </p>
            </div>
            <div className="p-2.5 bg-white/10 rounded-xl">
              <DollarSign className="w-6 h-6 text-[#00cfe8]" />
            </div>
          </div>

          {/* Quick Presets */}
          <div>
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-2">
              Quick Allowance Presets:
            </span>
            <div className="grid grid-cols-4 gap-2">
              {quickPresets.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setAmountInr(p.inr)}
                  className={`py-2 px-1 text-center text-xs font-bold rounded-xl border transition ${
                    amountInr === p.inr
                      ? 'bg-[#003087] text-white border-[#003087]'
                      : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="text-xs font-bold text-slate-800 block mb-1.5">Transfer Note / Purpose</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Monthly study allowance & meal plan"
              className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-[#0070E0]"
            />
          </div>

          {/* Funding Source Notice */}
          <div className="flex items-center space-x-2 text-[11px] text-slate-500 pt-1">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Debited from PayPal Sandbox Parent Account (Verified Indian NetBanking)</span>
          </div>

          {/* Action Buttons */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-xs font-bold text-slate-600 hover:text-slate-900 transition"
            >
              Cancel
            </button>

            {/* Iconic PayPal Yellow Button */}
            <button
              type="submit"
              disabled={loading || !amountInr || Number(amountInr) <= 0}
              className="flex-1 py-3 px-5 bg-[#FFC439] hover:bg-[#F6C944] disabled:opacity-50 text-[#001C64] font-black text-xs rounded-full shadow-md hover:shadow-lg transition flex items-center justify-center space-x-2 border border-amber-300"
            >
              {loading ? (
                <RefreshCw className="w-4 h-4 animate-spin text-[#001C64]" />
              ) : (
                <Send className="w-4 h-4 text-[#001C64]" />
              )}
              <span>Send with PayPal Sandbox (${currentUsd} USD)</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
