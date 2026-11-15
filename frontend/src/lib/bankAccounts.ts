// Shared types and helpers for GoCardless bank balances.

export interface Balance {
  balanceAmount: {
    amount: string
    currency: string
  }
  balanceType: string
  referenceDate?: string
}

export interface BankAccount {
  account_id: string
  requisition_id?: string | null
  institution_name: string
  label?: string | null
  balances: Balance[]
}

export interface PendingRequisition {
  requisition_id: string
  institution_id: string
  institution_name: string
  status: string
  status_label?: string
  link?: string
  message: string
}

export interface BalancesData {
  // Grouped by bank. Older backends only send this.
  balances: { [institutionName: string]: Balance[] }
  // One entry per account. Sent by newer backends.
  accounts?: BankAccount[]
  pending_requisitions: PendingRequisition[]
}

/** One entry per account, falling back to per-bank groups on older backends. */
export function getAccounts(data: BalancesData): BankAccount[] {
  if (data.accounts) return data.accounts
  return Object.entries(data.balances).map(([institution, balances]) => ({
    account_id: institution,
    institution_name: institution,
    balances: Array.isArray(balances) ? balances : [],
  }))
}

/** Title for an account card, e.g. "Chase •••• 1234" or "Chase account 2". */
export function accountTitle(account: BankAccount, all: BankAccount[]): string {
  if (account.label) return `${account.institution_name} ${account.label}`
  const sameBank = all.filter((a) => a.institution_name === account.institution_name)
  if (sameBank.length < 2) return account.institution_name
  return `${account.institution_name} account ${sameBank.indexOf(account) + 1}`
}

const BALANCE_TYPE_NAMES: Record<string, string> = {
  interimAvailable: 'Available',
  expected: 'Expected',
  closingBooked: 'Booked',
  interimBooked: 'Booked (today)',
  closingAvailable: 'Available (end of day)',
  openingBooked: 'Opening balance',
  forwardAvailable: 'Available (forward)',
}

export function balanceTypeName(type: string): string {
  return BALANCE_TYPE_NAMES[type] ?? type
}

// Banks report the same money several ways; this is the order we trust them.
const PRIMARY_BALANCE_ORDER = [
  'interimAvailable',
  'expected',
  'closingAvailable',
  'interimBooked',
  'closingBooked',
]

/** The single balance that represents what's in the account right now. */
export function primaryBalance(account: BankAccount): Balance | undefined {
  for (const type of PRIMARY_BALANCE_ORDER) {
    const match = account.balances.find((b) => b.balanceType === type)
    if (match) return match
  }
  return account.balances[0]
}

/** Total across accounts, counting one balance per account. */
export function totalBankBalance(data: BalancesData | null): number {
  if (!data) return 0
  return getAccounts(data).reduce((sum, account) => {
    const amount = parseFloat(primaryBalance(account)?.balanceAmount.amount ?? '')
    return isNaN(amount) ? sum : sum + amount
  }, 0)
}
