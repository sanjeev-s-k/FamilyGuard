import {
  ParentOverviewData,
  ChildWalletData,
  TransactionItem,
  ApprovalRequestItem,
  NotificationItem,
  SavingsGoalItem,
  TransactionReceiptData,
  SendMoneyResponse
} from './types';

const API_BASE = '/api';

export function getToken(): string | null {
  return localStorage.getItem('familyguard_token');
}

export function setToken(token: string) {
  localStorage.setItem('familyguard_token', token);
}

export function clearToken() {
  localStorage.removeItem('familyguard_token');
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorMsg = 'An error occurred';
    try {
      const err = await res.json();
      errorMsg = err.detail || err.message || errorMsg;
    } catch {
      errorMsg = `HTTP ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

export const api = {
  // Auth
  demoLoginParent: () => request<any>('/auth/demo/parent', { method: 'POST' }),
  demoLoginChild: () => request<any>('/auth/demo/child', { method: 'POST' }),
  getCurrentUser: () => request<any>('/auth/me'),

  // Parent Dashboard
  getParentOverview: () => request<ParentOverviewData>('/parent/overview'),
  getChildren: () => request<any[]>('/parent/children'),
  updateSpendingLimits: (childId: number, limits: any) =>
    request<any>(`/parent/children/${childId}/limits`, {
      method: 'PUT',
      body: JSON.stringify(limits),
    }),
  sendMoneyToChild: (payload: {
    child_id: number;
    amount_inr: number;
    notes?: string;
    payment_method?: string;
  }) =>
    request<SendMoneyResponse>('/parent/send-money', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getParentTransactions: (params?: { child_id?: number; category?: string; status_filter?: string }) => {
    const q = new URLSearchParams();
    if (params?.child_id) q.append('child_id', params.child_id.toString());
    if (params?.category) q.append('category', params.category);
    if (params?.status_filter) q.append('status_filter', params.status_filter);
    return request<TransactionItem[]>(`/parent/transactions?${q.toString()}`);
  },
  getApprovalRequests: () => request<ApprovalRequestItem[]>('/parent/approvals'),
  actOnApproval: (requestId: number, action: 'APPROVE' | 'DECLINE', notes?: string) =>
    request<any>(`/parent/approvals/${requestId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action, notes }),
    }),
  getNotifications: () => request<NotificationItem[]>('/parent/notifications'),
  markNotificationRead: (id: number) =>
    request<any>(`/parent/notifications/${id}/read`, { method: 'POST' }),
  markAllNotificationsRead: () =>
    request<any>('/parent/notifications/read-all', { method: 'POST' }),
  askAIAssistant: (prompt: string, child_id?: number) =>
    request<{ reply: string; suggested_questions: string[] }>('/parent/ai-assistant', {
      method: 'POST',
      body: JSON.stringify({ prompt, child_id }),
    }),

  // Child Wallet
  getChildWallet: () => request<ChildWalletData>('/child/wallet'),
  getChildTransactions: () => request<TransactionItem[]>('/child/transactions'),
  initiatePayment: (payload: {
    merchant: string;
    amount: number;
    currency: string;
    category: string;
    description: string;
    payment_method: string;
    paypal_order_id?: string;
  }) =>
    request<any>('/child/pay', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getSavingsGoals: () => request<SavingsGoalItem[]>('/child/goals'),
  addFundsToGoal: (goalId: number, amount: number) =>
    request<any>(`/child/goals/${goalId}/add-funds`, {
      method: 'POST',
      body: JSON.stringify({ amount }),
    }),

  // Reports
  getTransactionReceipt: (code: string) =>
    request<TransactionReceiptData>(`/reports/transaction/${code}`),
  getPdfDownloadUrl: (code: string) => `${API_BASE}/reports/transaction/${code}/pdf`,

  // PayPal
  createPayPalOrder: (payload: {
    child_id: number;
    amount: number;
    currency: string;
    merchant: string;
    category: string;
    description?: string;
  }) =>
    request<any>('/payments/paypal/create-order', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  capturePayPalOrder: (payload: {
    order_id: string;
    child_id: number;
    merchant: string;
    category: string;
    description?: string;
    amount: number;
    currency: string;
  }) =>
    request<any>('/payments/paypal/capture-order', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // System
  resetDemoDatabase: () => request<any>('/system/reset-demo', { method: 'POST' }),
};
