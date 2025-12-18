export type TransactionType =
  | 'single_broker_sale'
  | 'double_broker_split'
  | 'due_diligence'
  | 'hidden_defects'

type IsoDateString = string

export interface TransactionCoreFields {
  title: string
  property_description: string
  purchase_price: string
  earnest_deposit: string
  due_diligence_end_date: IsoDateString
  estimated_closing_date: IsoDateString
  depositor_name?: string
  property_address?: string
}

export interface TransactionCreateRequest extends TransactionCoreFields {
  type: TransactionType
  payload: Record<string, unknown>
}

export interface TransactionListItem extends TransactionCoreFields {
  id: string
  type: TransactionType
  status: string
  property_address?: string
  updated_at: string
  my_role?: string | null
  pending_invites_count?: number
  required_next_action?: string | null
}
