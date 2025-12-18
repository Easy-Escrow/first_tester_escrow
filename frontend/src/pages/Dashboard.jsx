import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { createTransaction, listTransactions } from '../api/transactions'

export default function Dashboard() {
  const [message, setMessage] = useState('Fetching profile...')
  const [profile, setProfile] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [transactionsError, setTransactionsError] = useState('')
  const [transactionsLoading, setTransactionsLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [createType, setCreateType] = useState('single_broker_sale')
  const [formState, setFormState] = useState({
    buyer_email: '',
    seller_email: '',
    known_party_role: 'buyer',
    known_party_email: '',
    secondary_broker_email: '',
    notes: '',
  })
  const [createError, setCreateError] = useState('')
  const [createSuccess, setCreateSuccess] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await api.get('/api/auth/profile/')
        setProfile(response.data)
        setMessage('Welcome back!')
        await loadTransactions()
      } catch (error) {
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
      setTransactionsError('Unable to load transactions right now.')
    } finally {
      setTransactionsLoading(false)
    }
  }

  const handleCreateTransaction = async (event) => {
    event.preventDefault()
    setCreateError('')
    setCreateSuccess('')
    setCreating(true)

    const payload = {}

    if (createType === 'single_broker_sale') {
      payload.buyer_email = formState.buyer_email
      payload.seller_email = formState.seller_email
    } else if (createType === 'double_broker_split') {
      payload.known_party_role = formState.known_party_role
      payload.known_party_email = formState.known_party_email
      payload.secondary_broker_email = formState.secondary_broker_email
    } else {
      payload.notes = formState.notes
    }

    try {
      await createTransaction({ type: createType, payload })
      setCreateSuccess('Transaction created. Invitations have been sent to participants.')
      setShowCreate(false)
      setFormState({
        buyer_email: '',
        seller_email: '',
        known_party_role: 'buyer',
        known_party_email: '',
        secondary_broker_email: '',
        notes: '',
      })
      await loadTransactions()
    } catch (error) {
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
            <button type="button" onClick={() => setShowCreate(!showCreate)}>
              {showCreate ? 'Close' : 'Start transaction'}
            </button>
          )}
        </div>

        {transactionsLoading && <p>Loading transactions...</p>}
        {transactionsError && <p className="error">{transactionsError}</p>}

        {showCreate && profile?.is_broker && (
          <form onSubmit={handleCreateTransaction} className="transaction-form">
            <label>
              Type
              <select
                value={createType}
                onChange={(e) => setCreateType(e.target.value)}
              >
                <option value="single_broker_sale">Single broker sale</option>
                <option value="double_broker_split">Double broker split</option>
                <option value="due_diligence">Due diligence</option>
                <option value="hidden_defects">Hidden defects</option>
              </select>
            </label>

            {createType === 'single_broker_sale' && (
              <div className="transaction-form-grid">
                <label>
                  Buyer email
                  <input
                    type="email"
                    required
                    value={formState.buyer_email}
                    onChange={(e) => setFormState({ ...formState, buyer_email: e.target.value })}
                  />
                </label>
                <label>
                  Seller email
                  <input
                    type="email"
                    required
                    value={formState.seller_email}
                    onChange={(e) => setFormState({ ...formState, seller_email: e.target.value })}
                  />
                </label>
              </div>
            )}

            {createType === 'double_broker_split' && (
              <div className="transaction-form-grid">
                <label>
                  Known party role
                  <select
                    value={formState.known_party_role}
                    onChange={(e) => setFormState({ ...formState, known_party_role: e.target.value })}
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
                    value={formState.known_party_email}
                    onChange={(e) => setFormState({ ...formState, known_party_email: e.target.value })}
                  />
                </label>
                <label>
                  Secondary broker email
                  <input
                    type="email"
                    required
                    value={formState.secondary_broker_email}
                    onChange={(e) => setFormState({ ...formState, secondary_broker_email: e.target.value })}
                  />
                </label>
              </div>
            )}

            {(createType === 'due_diligence' || createType === 'hidden_defects') && (
              <label>
                Notes
                <textarea
                  rows={3}
                  value={formState.notes}
                  onChange={(e) => setFormState({ ...formState, notes: e.target.value })}
                  placeholder="Provide brief details for the transaction"
                />
              </label>
            )}

            {createError && <p className="error">{createError}</p>}
            {createSuccess && <p className="success">{createSuccess}</p>}

            <div className="form-actions">
              <button type="submit" disabled={creating}>
                {creating ? 'Submitting...' : 'Create transaction'}
              </button>
            </div>
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
                <div className="badge-group">
                  <span className="badge badge-info">Inviting</span>
                  {tx.pending_invites_count > 0 && (
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
