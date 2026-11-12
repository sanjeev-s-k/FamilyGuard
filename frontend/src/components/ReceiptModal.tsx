import React, { useState, useEffect } from 'react';
import {
  X, Download, ShieldCheck, AlertCircle, AlertTriangle,
  Receipt, Calendar, ArrowRight, User, Tag, Globe
} from 'lucide-react';
import { TransactionReceiptData } from '../types';
import { api } from '../api';

const FX_RATE = 85.0;

interface ReceiptModalProps {
  transactionCode: string | null;
  onClose: () => void;
}

export const ReceiptModal: React.FC<ReceiptModalProps> = ({ transactionCode, onClose }) => {
  const [data, setData] = useState<TransactionReceiptData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!transactionCode) return;
    setLoading(true);
    setError(null);
    api.getTransactionReceipt(transactionCode)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load transaction receipt');
        setLoading(false);
      });
  }, [transactionCode]);

  if (!transactionCode) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="relative bg-white rounded-3xl max-w-2xl w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header with PayPal Sandbox Branding */}
        <div className="bg-gradient-to-r from-[#001C64] via-[#003087] to-[#0070E0] text-white px-6 py-5 flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center shadow-xs">
              <span className="font-black text-lg tracking-tighter text-[#003087]">
                P<span className="text-[#0070E0]">P</span>
              </span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold tracking-tight">PayPal Sandbox Transaction Receipt</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-[#FFC439] text-[#001C64]">
                  Verified
                </span>
              </div>
              <p className="text-xs text-blue-200">Audit Code: {transactionCode} • Cross-Border Remittance & Spend</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-white/10 text-white/80 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Audit Disclaimer Notice */}
        <div className="bg-amber-50 border-b border-amber-200/80 px-6 py-2.5 flex items-center space-x-2 text-amber-900 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
          <span>
            <b>PayPal Sandbox Telemetry:</b> Monitored overseas transaction receipt and AI explainability report with dual-currency breakdown.
          </span>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {loading ? (
            <div className="py-16 text-center text-slate-500 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-3 border-[#003087] border-t-transparent rounded-full animate-spin"></div>
              <p className="text-sm font-medium">Retrieving transaction audit & AI report...</p>
            </div>
          ) : error ? (
            <div className="py-12 text-center text-rose-500 text-sm font-medium">
              {error}
            </div>
          ) : data ? (
            <>
              {/* Primary Summary Card */}
              <div className="bg-slate-50 rounded-2xl p-5 border border-slate-200/80 grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Merchant</span>
                  <span className="text-sm font-bold text-slate-900 truncate block mt-0.5">{data.merchant}</span>
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">USD Amount</span>
                  <span className="text-base font-extrabold text-[#003087] block mt-0.5">
                    ${data.transaction_amount.toFixed(2)} USD
                  </span>
                  <span className="text-[11px] text-[#0070E0] font-bold block">
                    ≈ ₹{(data.transaction_amount * FX_RATE).toFixed(2)} INR
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Child</span>
                  <span className="text-sm font-bold text-slate-800 block mt-0.5">{data.child_name} (Boston, USA)</span>
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Status</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 mt-0.5">
                    {data.payment_status}
                  </span>
                </div>
              </div>

              {/* Allowance Impact Breakdown */}
              <div className="bg-blue-50/60 rounded-2xl p-5 border border-blue-100">
                <h4 className="text-xs font-bold text-[#003087] uppercase tracking-wider mb-3 flex items-center space-x-1.5">
                  <ShieldCheck className="w-4 h-4 text-[#0070E0]" />
                  <span>Spending Limit Impact ($ USD)</span>
                </h4>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="bg-white p-3 rounded-xl border border-blue-100/80">
                    <span className="text-[10px] text-slate-500 font-medium">Daily Limit</span>
                    <p className="text-sm font-bold text-slate-800 mt-0.5">
                      ${data.daily_limit.toFixed(2)} USD
                    </p>
                    <span className="text-[10px] text-slate-400">≈ ₹{(data.daily_limit * FX_RATE).toFixed(0)} INR</span>
                  </div>
                  <div className="bg-white p-3 rounded-xl border border-blue-100/80">
                    <span className="text-[10px] text-slate-500 font-medium">Spent After Tx</span>
                    <p className="text-sm font-bold text-[#003087] mt-0.5">
                      ${data.daily_spending_after.toFixed(2)} USD
                    </p>
                    <span className="text-[10px] text-[#0070E0]">≈ ₹{(data.daily_spending_after * FX_RATE).toFixed(0)} INR</span>
                  </div>
                  <div className="bg-white p-3 rounded-xl border border-blue-100/80">
                    <span className="text-[10px] text-slate-500 font-medium">Remaining Allowance</span>
                    <p className="text-sm font-bold text-emerald-600 mt-0.5">
                      ${data.remaining_spending_allowance.toFixed(2)} USD
                    </p>
                    <span className="text-[10px] text-emerald-700">≈ ₹{(data.remaining_spending_allowance * FX_RATE).toFixed(0)} INR</span>
                  </div>
                </div>
              </div>

              {/* AI Assessment & Safety Section */}
              <div className="bg-slate-50 rounded-2xl p-5 border border-slate-200/80 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">AI Safety Risk Assessment</span>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                    data.risk_assessment === 'HIGH'
                      ? 'bg-rose-100 text-rose-700 border border-rose-200'
                      : data.risk_assessment === 'MEDIUM'
                      ? 'bg-amber-100 text-amber-800 border border-amber-200'
                      : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                  }`}>
                    {data.risk_assessment} Risk
                  </span>
                </div>

                <div className="text-xs text-slate-700 leading-relaxed bg-white p-3.5 rounded-xl border border-slate-200/60">
                  <span className="font-semibold text-slate-900 block mb-1">Parent Explanation:</span>
                  {data.ai_explanation}
                </div>

                <div className="text-xs text-slate-700 leading-relaxed bg-white p-3.5 rounded-xl border border-slate-200/60">
                  <span className="font-semibold text-slate-900 block mb-1">Allowance Summary:</span>
                  {data.ai_spending_summary}
                </div>

                <div className="text-xs text-[#003087] leading-relaxed bg-blue-50/70 p-3.5 rounded-xl border border-blue-200/60">
                  <span className="font-bold text-[#001C64] block mb-1">Recommendation:</span>
                  {data.ai_recommendation}
                </div>
              </div>

              {/* Timestamp & Method */}
              <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100">
                <span className="flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{data.transaction_date}</span>
                </span>
                <span className="flex items-center space-x-1.5">
                  <Tag className="w-3.5 h-3.5" />
                  <span>Category: {data.category} • FX: 1 USD = ₹85.00 INR</span>
                </span>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer Actions */}
        <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 transition"
          >
            Close
          </button>

          {data && (
            <a
              href={api.getPdfDownloadUrl(data.transaction_id)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-2 px-5 py-2.5 bg-[#003087] hover:bg-[#001C64] text-white text-xs font-bold rounded-xl shadow-sm transition"
            >
              <Download className="w-4 h-4" />
              <span>Download Official PDF Receipt</span>
            </a>
          )}
        </div>
      </div>
    </div>
  );
};
