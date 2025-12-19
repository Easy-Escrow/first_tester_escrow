export type TransactionType =
  | 'single_broker_sale'
  | 'double_broker_split'
  | 'due_diligence'
  | 'hidden_defects'

type IsoDateString = string
export type TransactionStage = 'pending_invitations' | 'pending_user_information' | string

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

export interface TransactionEvent {
  type: 'stage_changed' | 'invitation_sent' | 'invitation_accepted' | 'counterparty_invited' | string
  actor: string | number | null
  actor_email?: string | null
  data: Record<string, unknown>
  created_at: IsoDateString
}

export interface TransactionListItem extends TransactionCoreFields {
  id: string
  type: TransactionType
  status: string
  stage: TransactionStage
  stage_updated_at: IsoDateString
  property_address?: string
  updated_at: string
  my_role?: string | null
  pending_invites_count?: number
  required_next_action?: string | null
}

export interface TransactionDetail extends TransactionListItem {
  created_at: IsoDateString
  participants: Array<{
    role: string
    invited_email: string
    user: string | null
    joined_at: IsoDateString | null
  }>
  invitations: Array<{
    participant_role: string
    status: string
    expires_at: IsoDateString
  }>
  details: Record<string, unknown>
  commission_split?: {
    primary_broker_pct: number
    secondary_broker_pct: number
  } | null
  events: TransactionEvent[]
}
