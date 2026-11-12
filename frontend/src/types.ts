export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'PARENT' | 'CHILD' | 'ADMIN';
  parent_id?: number | null;
  child_id?: number | null;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  role: 'PARENT' | 'CHILD';
}

export interface SpendingRule {
  id: number;
  child_id: number;
  daily_limit: number;
  weekly_limit: number;
  approval_threshold: number;
  allowed_categories: string;
  blocked_merchants: string;
  is_active: boolean;
  updated_at: string;
}

export interface ChildSummary {
  id: number;
  name: string;
  age: number;
  avatar: string;
  balance: number;
  balance_usd?: number;
  balance_inr?: number;
  total_spent: number;
  spent_today: number;
  spent_today_inr?: number;
  daily_limit: number;
  daily_limit_inr?: number;
  weekly_limit: number;
  weekly_limit_inr?: number;
  approval_threshold: number;
  approval_threshold_inr?: number;
}

export interface ParentOverviewData {
  parent_name: string;
  currency: string;
  child_currency?: string;
  fx_rate?: number;
  total_family_spending: number;
  total_family_spending_usd?: number;
  total_transactions: number;
  pending_approvals_count: number;
  unread_alerts_count: number;
  children: ChildSummary[];
  category_spending: { category: string; amount: number; amount_usd?: number }[];
  daily_trends: { date: string; amount: number; amount_usd?: number }[];
}

export interface AIReportData {
  id?: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  category: string;
  requires_review: boolean;
  explanation: string;
  spending_summary: string;
  recommendation: string;
  confidence_score: number;
}

export interface TransactionItem {
  id: number;
  transaction_code: string;
  child_id: number;
  child_name?: string;
  amount: number;
  currency: string;
  amount_inr?: number;
  amount_usd?: number;
  fx_rate?: number;
  merchant: string;
  category: string;
  description?: string;
  status: 'COMPLETED' | 'PENDING_APPROVAL' | 'DECLINED' | 'FAILED' | 'REFUNDED';
  payment_method: string;
  paypal_order_id?: string | null;
  paypal_capture_id?: string | null;
  requires_approval: boolean;
  remaining_daily_allowance_after: number;
  created_at: string;
  ai_report?: AIReportData | null;
  approval_status?: string | null;
}

export interface ApprovalRequestItem {
  id: number;
  transaction_id: number;
  transaction_code: string;
  child_id: number;
  child_name: string;
  merchant: string;
  amount: number;
  currency: string;
  amount_inr?: number;
  amount_usd?: number;
  fx_rate?: number;
  category: string;
  status: 'PENDING' | 'APPROVED' | 'DECLINED';
  parent_notes?: string | null;
  requested_at: string;
  decided_at?: string | null;
  ai_report?: AIReportData | null;
}

export interface NotificationItem {
  id: number;
  parent_id: number;
  child_id: number;
  child_name: string;
  type: string;
  title: string;
  message: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  transaction_id?: number | null;
  is_read: boolean;
  created_at: string;
}

export interface SavingsGoalItem {
  id: number;
  title: string;
  target_amount: number;
  current_amount: number;
  icon: string;
  percentage: number;
  is_completed: boolean;
}

export interface ChildWalletData {
  id: number;
  child_id: number;
  currency: string;
  balance: number;
  balance_inr?: number;
  fx_rate?: number;
  total_spent: number;
  total_deposited: number;
  daily_limit: number;
  daily_spent_today: number;
  daily_remaining: number;
  weekly_limit: number;
  weekly_spent: number;
  weekly_remaining: number;
  approval_threshold: number;
}

export interface TransactionReceiptData {
  report_title: string;
  notice: string;
  child_name: string;
  transaction_id: string;
  merchant: string;
  transaction_amount: number;
  currency: string;
  amount_inr?: number;
  fx_rate?: number;
  transaction_date: string;
  payment_status: string;
  payment_method: string;
  category: string;
  risk_assessment: string;
  daily_spending_before: number;
  daily_spending_after: number;
  remaining_spending_allowance: number;
  daily_limit: number;
  ai_explanation: string;
  ai_spending_summary: string;
  ai_recommendation: string;
  requires_review: boolean;
}

export interface SendMoneyResponse {
  status: string;
  message: string;
  amount_inr: number;
  amount_usd: number;
  fx_rate: number;
  child_name: string;
  new_wallet_balance_usd: number;
  new_wallet_balance_inr: number;
  transaction_code: string;
}
