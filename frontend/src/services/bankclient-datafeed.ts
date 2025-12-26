const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

/**
 * Connects Frontend to Gocardless banking backend data
 */
export class BankClientDatafeed {
  /**
   * Fetches the list of institutions from the backend
   */
  async getInstitutions() {
    const response = await fetch(`${BACKEND_URL}/banking/institutions`);
    const data = await response.json();
    // Backend may return either an array or an object containing `institutions`.
    if (Array.isArray(data)) return data
    if (data && Array.isArray(data.institutions)) return data.institutions
    return []
  }

  /**
   * Creates a requisition and returns the GoCardless authentication link
   */
  async createRequisition(institutionId: string, redirectUri: string, token: string) {
    const response = await fetch(
      `${BACKEND_URL}/banking/requisition?redirect_uri=${encodeURIComponent(redirectUri)}&institution_id=${encodeURIComponent(institutionId)}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to create requisition: ${error}`);
    }

    const data = await response.json();
    return data; // { link: string, requisition_id: string }
  }

  /**
   * Fetches all account balances for the authenticated user
   */
  async getAllBalances(token: string) {
    const response = await fetch(`${BACKEND_URL}/banking/all_balances`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to fetch balances: ${error}`);
    }

    const data = await response.json();
    return data; // { balances: { [requisition_id]: balances[] } }
  }

}