import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { createTransaction, listTransactions } from '../api/transactions'
import type {
  TransactionCoreFields,
  TransactionCreateRequest,
  TransactionListItem,
  TransactionType,
} from '../types/transactions'

interface Profile {
  email: string
  first_name?: string
  last_name?: string
  is_broker: boolean
}

interface TypePayloadState {
  buyer_email: string
  seller_email: string
  known_party_role: 'buyer' | 'seller'
  known_party_email: string
  secondary_broker_email: string
  notes: string
}

const initialCoreFields: TransactionCoreFields = {
  title: '',
  property_description: '',
  purchase_price: '',
  earnest_deposit: '',
  due_diligence_end_date: '',
  estimated_closing_date: '',
  depositor_name: '',
  property_address: '',
}

const initialPayloadState: TypePayloadState = {
  buyer_email: '',
  seller_email: '',
  known_party_role: 'buyer',
  known_party_email: '',
  secondary_broker_email: '',
  notes: '',
}

function formatCurrency(value?: string) {
  if (!value) return '-'
  const numericValue = Number(value)
  if (Number.isNaN(numericValue)) return value
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numericValue)
}

function formatDate(value?: string) {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString()
}

export default function Dashboard() {
  const [message, setMessage] = useState('Fetching profile...')
  const [profile, setProfile] = useState<Profile | null>(null)
  const [transactions, setTransactions] = useState<TransactionListItem[]>([])
  const [transactionsError, setTransactionsError] = useState('')
  const [transactionsLoading, setTransactionsLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [createType, setCreateType] = useState<TransactionType>('single_broker_sale')
  const [coreFields, setCoreFields] = useState<TransactionCoreFields>(initialCoreFields)
  const [payloadState, setPayloadState] = useState<TypePayloadState>(initialPayloadState)
  const [coreError, setCoreError] = useState('')
  const [createError, setCreateError] = useState('')
  const [createSuccess, setCreateSuccess] = useState('')
  const [creating, setCreating] = useState(false)
  const [currentStep, setCurrentStep] = useState<1 | 2>(1)

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await api.get<Profile>('/api/auth/profile/')
        setProfile(response.data)
        setMessage('Welcome back!')
        await loadTransactions()
      } catch (error) {
        console.error(error)
        setMessage('Unable to load profile. Please re-login if needed.')
      }
    }
    loadProfile()
  }, [])

  const loadTransactions = async () => {
    setTransactionsLoading(true)
    setTransactionsError('')
    try {
      const response = await listTransactions()
      setTransactions(response.data)
    } catch (error) {
      console.error(error)
      setTransactionsError('Unable to load transactions right now.')
    } finally {
      setTransactionsLoading(false)
    }
  }

  const validateCoreFields = () => {
    setCoreError('')
    if (
      !coreFields.title.trim() ||
      !coreFields.property_description.trim() ||
      !coreFields.purchase_price ||
      !coreFields.earnest_deposit ||
      !coreFields.due_diligence_end_date ||
      !coreFields.estimated_closing_date
    ) {
      setCoreError('Please complete all required transaction details in Step 1.')
      return false
    }

    const purchase = Number(coreFields.purchase_price)
    const earnest = Number(coreFields.earnest_deposit)
    if (!Number.isNaN(purchase) && !Number.isNaN(earnest) && earnest > purchase) {
      setCoreError('Earnest deposit cannot exceed purchase price.')
      return false
    }

    const dueDate = new Date(coreFields.due_diligence_end_date)
    const closingDate = new Date(coreFields.estimated_closing_date)
    if (!Number.isNaN(dueDate.getTime()) && !Number.isNaN(closingDate.getTime())) {
      if (closingDate <= dueDate) {
        setCoreError('Estimated closing date must be after due diligence end date.')
        return false
      }
    }

    return true
  }

  const handleNextStep = () => {
    if (validateCoreFields()) {
      setCurrentStep(2)
    }
  }

  const handleCreateTransaction = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setCreateError('')
    setCreateSuccess('')

    if (!validateCoreFields()) {
      setCurrentStep(1)
      return
    }

    setCreating(true)

    const payload: Record<string, unknown> = {}

    if (createType === 'single_broker_sale') {
      payload.buyer_email = payloadState.buyer_email
      payload.seller_email = payloadState.seller_email
    } else if (createType === 'double_broker_split') {
      payload.known_party_role = payloadState.known_party_role
      payload.known_party_email = payloadState.known_party_email
      payload.secondary_broker_email = payloadState.secondary_broker_email
    } else {
      payload.notes = payloadState.notes
    }

    const requestBody: TransactionCreateRequest = {
      ...coreFields,
      type: createType,
      payload,
    }

    try {
      await createTransaction(requestBody)
      setCreateSuccess('Transaction created. Invitations have been sent to participants.')
      setShowCreate(false)
      setCurrentStep(1)
      setCoreFields(initialCoreFields)
      setPayloadState(initialPayloadState)
      await loadTransactions()
    } catch (error) {
      console.error(error)
      setCreateError('Unable to create transaction. Please check the form and try again.')
    } finally {
      setCreating(false)
    }
  }

  const invitations = useMemo(
    () => transactions.filter((tx) => tx.status === 'inviting' && !tx.my_role),
    [transactions]
  )

  const activeTransactions = useMemo(
    () =>
      transactions.filter(
        (tx) => tx.status !== 'completed' && !(tx.status === 'inviting' && !tx.my_role)
      ),
    [transactions]
  )

  const renderCoreFieldInputs = () => (
    <div className="transaction-form-grid">
      <label>
        Title
        <input
          type="text"
          required
          value={coreFields.title}
          onChange={(e) => setCoreFields({ ...coreFields, title: e.target.value })}
        />
      </label>
      <label className="span-2">
        Property description
        <textarea
          rows={3}
          required
          value={coreFields.property_description}
          onChange={(e) => setCoreFields({ ...coreFields, property_description: e.target.value })}
        />
      </label>
      <label>
        Purchase price
        <input
          type="number"
          required
          value={coreFields.purchase_price}
          onChange={(e) => setCoreFields({ ...coreFields, purchase_price: e.target.value })}
        />
      </label>
      <label>
        Earnest deposit
        <input
          type="number"
          required
          value={coreFields.earnest_deposit}
          onChange={(e) => setCoreFields({ ...coreFields, earnest_deposit: e.target.value })}
        />
      </label>
      <label>
        Due diligence end date
        <input
          type="date"
          required
          value={coreFields.due_diligence_end_date}
          onChange={(e) => setCoreFields({ ...coreFields, due_diligence_end_date: e.target.value })}
        />
      </label>
      <label>
        Estimated closing date
        <input
          type="date"
          required
          value={coreFields.estimated_closing_date}
          onChange={(e) => setCoreFields({ ...coreFields, estimated_closing_date: e.target.value })}
        />
      </label>
      <label>
        Depositor name (optional)
        <input
          type="text"
          value={coreFields.depositor_name ?? ''}
          onChange={(e) => setCoreFields({ ...coreFields, depositor_name: e.target.value })}
          placeholder="Only if depositor differs from purchaser"
        />
      </label>
    </div>
  )

  const renderTypeSpecificFields = () => {
    if (createType === 'single_broker_sale') {
      return (
        <div className="transaction-form-grid">
          <label>
            Buyer email
            <input
              type="email"
              required
              value={payloadState.buyer_email}
              onChange={(e) => setPayloadState({ ...payloadState, buyer_email: e.target.value })}
            />
          </label>
          <label>
            Seller email
            <input
              type="email"
              required
              value={payloadState.seller_email}
              onChange={(e) => setPayloadState({ ...payloadState, seller_email: e.target.value })}
            />
          </label>
        </div>
      )
    }

    if (createType === 'double_broker_split') {
      return (
        <div className="transaction-form-grid">
          <label>
            Known party role
            <select
              value={payloadState.known_party_role}
              onChange={(e) =>
                setPayloadState({ ...payloadState, known_party_role: e.target.value as 'buyer' | 'seller' })
              }
            >
              <option value="buyer">Buyer</option>
              <option value="seller">Seller</option>
            </select>
          </label>
          <label>
            Known party email
            <input
              type="email"
              required
              value={payloadState.known_party_email}
              onChange={(e) => setPayloadState({ ...payloadState, known_party_email: e.target.value })}
            />
          </label>
          <label>
            Secondary broker email
            <input
              type="email"
              required
              value={payloadState.secondary_broker_email}
              onChange={(e) => setPayloadState({ ...payloadState, secondary_broker_email: e.target.value })}
            />
          </label>
        </div>
      )
    }

    return (
      <label>
        Notes
        <textarea
          rows={3}
          value={payloadState.notes}
          onChange={(e) => setPayloadState({ ...payloadState, notes: e.target.value })}
          placeholder="Provide brief details for the transaction"
        />
      </label>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <Link className="button" to="/broker-application">Become a broker</Link>
      </div>
      <div className="card">
        <p>{message}</p>
        {profile && (
          <ul>
            <li><strong>Email:</strong> {profile.email}</li>
            {profile.first_name && <li><strong>First name:</strong> {profile.first_name}</li>}
            {profile.last_name && <li><strong>Last name:</strong> {profile.last_name}</li>}
            <li><strong>Role:</strong> {profile.is_broker ? 'Broker' : 'Standard user'}</li>
          </ul>
        )}
      </div>

      <div className="card" style={{ marginTop: '18px' }}>
        <div className="card-header">
          <h2>Transactions</h2>
          {profile?.is_broker && (
            <button className="button" onClick={() => setShowCreate(!showCreate)}>
              {showCreate ? 'Close form' : 'Create transaction'}
            </button>
          )}
        </div>

        {transactionsError && <p className="error">{transactionsError}</p>}

        {showCreate && (
          <form onSubmit={handleCreateTransaction} className="transaction-form">
            <div className="form-steps">
              <div className={`step ${currentStep === 1 ? 'active' : ''}`}>Step 1: Core info</div>
              <div className={`step ${currentStep === 2 ? 'active' : ''}`}>Step 2: Transaction type</div>
            </div>

            <h4>Step 1 — Core transaction info</h4>
            {renderCoreFieldInputs()}
            {coreError && <p className="error">{coreError}</p>}

            {currentStep === 1 && (
              <div className="form-actions">
                <button type="button" onClick={handleNextStep}>
                  Continue to step 2
                </button>
              </div>
            )}

            {currentStep === 2 && (
              <>
                <h4>Step 2 — Transaction type specific fields</h4>
                <label>
                  Type
                  <select
                    value={createType}
                    onChange={(e) => setCreateType(e.target.value as TransactionType)}
                  >
                    <option value="single_broker_sale">Single broker sale</option>
                    <option value="double_broker_split">Double broker split</option>
                    <option value="due_diligence">Due diligence</option>
                    <option value="hidden_defects">Hidden defects</option>
                  </select>
                </label>

                {renderTypeSpecificFields()}

                {createError && <p className="error">{createError}</p>}
                {createSuccess && <p className="success">{createSuccess}</p>}

                <div className="form-actions">
                  <button type="button" onClick={() => setCurrentStep(1)}>
                    Back to step 1
                  </button>
                  <button type="submit" disabled={creating}>
                    {creating ? 'Submitting...' : 'Create transaction'}
                  </button>
                </div>
              </>
            )}
          </form>
        )}

        <div className="transaction-section">
          <h3>Invitations</h3>
          {!transactionsLoading && invitations.length === 0 && <p>No pending invitations.</p>}
          {invitations.map((tx) => (
            <div key={tx.id} className="transaction-row">
              <div>
                <div className="eyebrow">{tx.type.replaceAll('_', ' ')}</div>
                <strong>{tx.title || 'Untitled transaction'}</strong>
                <div className="transaction-meta">
                  <span>Purchase price: {formatCurrency(tx.purchase_price)}</span>
                  <span>Earnest deposit: {formatCurrency(tx.earnest_deposit)}</span>
                  <span>Due diligence end: {formatDate(tx.due_diligence_end_date)}</span>
                  <span>Estimated closing: {formatDate(tx.estimated_closing_date)}</span>
                </div>
                <div className="badge-group">
                  <span className="badge badge-info">Inviting</span>
                  {tx.pending_invites_count !== undefined && tx.pending_invites_count > 0 && (
                    <span className="badge badge-muted">{tx.pending_invites_count} pending</span>
                  )}
                </div>
              </div>
              {tx.required_next_action && <div className="badge badge-muted">{tx.required_next_action}</div>}
            </div>
          ))}
        </div>

        <div className="transaction-section">
          <h3>Active transactions</h3>
          {!transactionsLoading && activeTransactions.length === 0 && <p>No transactions yet.</p>}
          {activeTransactions.map((tx) => (
            <div key={tx.id} className="transaction-row">
              <div>
                <div className="eyebrow">{tx.type.replaceAll('_', ' ')}</div>
                <strong>{tx.title || 'Untitled transaction'}</strong>
                <div className="transaction-meta">
                  <span>Purchase price: {formatCurrency(tx.purchase_price)}</span>
                  <span>Earnest deposit: {formatCurrency(tx.earnest_deposit)}</span>
                  <span>Due diligence end: {formatDate(tx.due_diligence_end_date)}</span>
                  <span>Estimated closing: {formatDate(tx.estimated_closing_date)}</span>
                </div>
                <div className="badge-group">
                  <span className="badge badge-info">{tx.status}</span>
                  {tx.my_role && <span className="badge badge-muted">My role: {tx.my_role}</span>}
                </div>
              </div>
              {tx.required_next_action && <div className="badge badge-muted">{tx.required_next_action}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
