const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

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

}