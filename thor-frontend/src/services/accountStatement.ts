import api from './api';

export type AccountType = 'paper' | 'real';

export interface AccountSummary {
  netLiquidatingValue?: string;
  stockBuyingPower?: string;
  optionBuyingPower?: string;
  dayTradingBuyingPower?: string;
  availableFundsForTrading?: string;
  longStockValue?: string;
  equityPercentage?: string; // include % sign
  resetCount?: number;
  lastReset?: string | null;
}

export async function fetchAccountSummary(accountType: AccountType): Promise<AccountSummary> {
  try {
    const { data } = await api.get('/account-statement/summary', {
      params: { account_type: accountType },
    });
    return data as AccountSummary;
  } catch (e) {
    // Backend only policy: surface empty values on error
    return {} as AccountSummary;
  }
}

export async function resetPaperAccount(): Promise<AccountSummary | null> {
  try {
    const { data } = await api.post('/account-statement/reset-paper');
    return data as AccountSummary;
  } catch (e) {
    return null;
  }
}
