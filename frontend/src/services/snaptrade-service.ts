const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export interface Brokerage {
  id: string;
  slug: string;
  name: string;
  display_name: string;
  logo_url: string;
  square_logo_url: string | null;
  enabled: boolean;
  allows_trading: boolean;
}

export interface BrokerageHoldingsResponse {
  holdings: BrokerageAccountHoldings[];
  user_id: string;
}

export interface BrokerageAccountHoldings {
  account?: {
    id: string;
    name: string;
    number: string;
  };
  balances?: Array<{
    currency?: { id: string; code: string; name: string };
    cash?: number;
  }>;
  positions?: Array<{
    symbol?: { id: string; symbol: string; description: string };
    units?: number;
    price?: number;
    average_purchase_price?: number;
    currency?: { id: string; code: string };
  }>;
  total_value?: {
    value?: number;
    currency?: string;
  };
}

/**
 * Service for SnapTrade brokerage integration
 */
export class SnapTradeService {
  /**
   * List all available brokerages (no auth required)
   */
  async listBrokerages(): Promise<Brokerage[]> {
    const response = await fetch(`${BACKEND_URL}/brokerages/list`);

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to list brokerages: ${error}`);
    }

    const data = await response.json();
    return data.brokerages || [];
  }

  /**
   * Get a connection portal URL for a specific brokerage
   */
  async getLoginUrl(
    token: string,
    broker?: string,
    darkMode?: boolean,
  ): Promise<{ redirect_url: string }> {
    const body: Record<string, unknown> = {};
    if (broker) body.broker = broker;
    if (darkMode !== undefined) body.dark_mode = darkMode;

    const response = await fetch(`${BACKEND_URL}/brokerages/login_url`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new SnapTradeError(`Failed to get login URL: ${error}`, response.status);
    }

    return response.json();
  }

  /**
   * Get all holdings for the authenticated user
   */
  async getHoldings(token: string): Promise<BrokerageHoldingsResponse> {
    const response = await fetch(`${BACKEND_URL}/brokerages/holdings`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new SnapTradeError('Brokerage account not connected', 404);
      }
      const error = await response.text();
      throw new SnapTradeError(`Failed to fetch holdings: ${error}`, response.status);
    }

    return response.json();
  }
}

/**
 * Custom error class for SnapTrade service errors
 */
export class SnapTradeError extends Error {
  constructor(message: string, public statusCode: number) {
    super(message);
    this.name = 'SnapTradeError';
  }
}
