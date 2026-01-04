const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

/**
 * Trading212 API service for managing T212 accounts and data
 */
export class T212Service {
  /**
   * Add or update Trading212 API keys for the authenticated user
   * @param userKey - Trading212 API key ID
   * @param userSecret - Trading212 API secret key
   * @param token - JWT authentication token
   */
  async addUserKeys(userKey: string, userSecret: string, token: string): Promise<void> {
    const response = await fetch(
      `${BACKEND_URL}/T212_add_user_keys?user_key=${encodeURIComponent(userKey)}&user_secret=${encodeURIComponent(userSecret)}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to add Trading212 keys: ${error}`);
    }
  }

  /**
   * Remove Trading212 API keys for the authenticated user
   * @param token - JWT authentication token
   */
  async removeUserKeys(token: string): Promise<void> {
    const response = await fetch(`${BACKEND_URL}/T212_remove_user_keys`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to remove Trading212 keys: ${error}`);
    }
  }

  /**
   * Get Trading212 account summary
   * @param token - JWT authentication token
   * @returns Account summary with cash and investment metrics
   * @throws Error with status code 404 if API keys are not found
   */
  async getSummary(token: string): Promise<T212Summary> {
    const response = await fetch(`${BACKEND_URL}/T212_summary`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new T212Error('Trading212 API keys not found', 404);
      }
      const error = await response.text();
      throw new Error(`Failed to fetch Trading212 summary: ${error}`);
    }

    const data = await response.json();
    return data;
  }

  /**
   * Get all open positions in Trading212 account
   * @param token - JWT authentication token
   * @returns List of open positions
   * @throws Error with status code 404 if API keys are not found
   */
  async getPositions(token: string): Promise<T212Position[]> {
    const response = await fetch(`${BACKEND_URL}/T212_positions`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new T212Error('Trading212 API keys not found', 404);
      }
      const error = await response.text();
      throw new Error(`Failed to fetch Trading212 positions: ${error}`);
    }

    const data = await response.json();
    return data;
  }
}

/**
 * Custom error class for T212 service errors
 */
export class T212Error extends Error {
  constructor(message: string, public statusCode: number) {
    super(message);
    this.name = 'T212Error';
  }
}

/**
 * Trading212 account summary response
 */
export interface T212Summary {
  totalWorth: number;
  totalCash: number;
  totalPpl: number;
  totalResult: number;
  investedValue: number;
  pieCash: number;
  blockedForStocks: number;
  result: number;
  dividend: number;
  interest: number;
  fee: number;
  free: number;
}

/**
 * Trading212 position response
 */
export interface T212Position {
  ticker: string;
  quantity: number;
  averagePrice: number;
  currentPrice: number;
  ppl: number;
  frontend: number;
  initialFillDate: string;
  maxBuy: number;
  maxSell: number;
  pieQuantity: number;
}
