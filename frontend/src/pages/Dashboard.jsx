import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'

const currencyOptions = [
  { value: 'usd', label: 'USD' },
  { value: 'mxn', label: 'MXN' },
]

const transactionTypes = [
  { value: 'single_broker_sale', label: 'Single broker sale' },
  { value: 'double_broker_commission_split', label: 'Double broker commission split' },
  { value: 'due_diligence', label: 'Due diligence' },
  { value: 'hidden_defects', label: 'Hidden defects' },
]

const propertyTypeOptions = [
  { value: 'house', label: 'House' },
  { value: 'apartment', label: 'Apartment' },
  { value: 'condo', label: 'Condominium' },
  { value: 'land', label: 'Land' },
  { value: 'commercial', label: 'Commercial' },
  { value: 'industrial', label: 'Industrial' },
  { value: 'other', label: 'Other' },
]

const emptyForm = {
  name: '',
  currency: 'usd',
  transaction_type: 'single_broker_sale',
  property_type: '',
  purchase_price: '',
  earnest_deposit: '',
  due_diligence_end_date: '',
  estimated_closing_date: '',
  buyer_email: '',
  seller_email: '',
  initiating_party_email: '',
  initiating_party_role: 'buyer',
  secondary_broker_email: '',
  participant_emails: '',
}

export default function Dashboard() {
  const [message, setMessage] = useState('Fetching profile...')
  const [profile, setProfile] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [invitations, setInvitations] = useState([])
  const [activeTab, setActiveTab] = useState('transactions')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [formSuccess, setFormSuccess] = useState('')
  const [counterpartyEmails, setCounterpartyEmails] = useState({})

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await api.get('/api/auth/profile/')
        setProfile(response.data)
        setMessage('Welcome back!')
      } catch (error) {
        setMessage('Unable to load profile. Please re-login if needed.')
      }
    }

    const loadTransactions = async () => {
      try {
        const response = await api.get('/api/transactions/')
        setTransactions(response.data)
      } catch (error) {
        console.error('Failed to load transactions', error)
      }
    }

    const loadInvitations = async () => {
      try {
        const response = await api.get('/api/invitations/')
        setInvitations(response.data)
      } catch (error) {
        console.error('Failed to load invitations', error)
      }
    }

    loadProfile()
    loadTransactions()
    loadInvitations()
  }, [])

  const resetForm = () => {
    setFormData(emptyForm)
    setFormError('')
    setFormSuccess('')
  }

  const handleFormChange = (event) => {
    const { name, value } = event.target
    setFormData((prev) => {
      const next = { ...prev, [name]: value }

      if (name === 'transaction_type') {
        next.buyer_email = ''
        next.seller_email = ''
        next.initiating_party_email = ''
        next.initiating_party_role = 'buyer'
        next.secondary_broker_email = ''
      }

      return next
    })
  }

  const handleCreateTransaction = async (event) => {
    event.preventDefault()
    setFormError('')
    setFormSuccess('')

    try {
      if (
        formData.transaction_type === 'single_broker_sale' &&
        (!formData.buyer_email || !formData.seller_email)
      ) {
        setFormError('Buyer and seller emails are required for a single broker sale.')
        return
      }

      if (
        formData.transaction_type === 'double_broker_commission_split' &&
        (!formData.initiating_party_email ||
          !formData.initiating_party_role ||
          !formData.secondary_broker_email)
      ) {
        setFormError('Provide the known party email, their role, and the secondary broker email for a double broker transaction.')
        return
      }

      const payload = {
        name: formData.name,
        currency: formData.currency,
        transaction_type: formData.transaction_type,
        property_type: formData.property_type,
        purchase_price: formData.purchase_price || '0',
        earnest_deposit: formData.earnest_deposit || '0',
        due_diligence_end_date: formData.due_diligence_end_date,
        estimated_closing_date: formData.estimated_closing_date,
      }

      if (formData.transaction_type === 'single_broker_sale') {
        payload.buyer_email = formData.buyer_email
        payload.seller_email = formData.seller_email
      }

      if (formData.transaction_type === 'double_broker_commission_split') {
        payload.initiating_party_email = formData.initiating_party_email
        payload.initiating_party_role = formData.initiating_party_role
        payload.secondary_broker_email = formData.secondary_broker_email
      }

      if (formData.participant_emails) {
        payload.participant_emails = formData.participant_emails
          .split(',')
          .map((email) => email.trim())
          .filter(Boolean)
      }

      const response = await api.post('/api/transactions/', payload)
      setTransactions((prev) => [response.data, ...prev])
      setFormSuccess('Transaction created and invitations sent.')
      resetForm()
      setShowCreateForm(false)
    } catch (error) {
      const detail = error.response?.data?.detail || error.response?.data || 'Unable to create transaction.'
      setFormError(typeof detail === 'string' ? detail : 'Unable to create transaction.')
    }
  }

  const handleCounterpartyInvite = async (transactionId) => {
    const email = counterpartyEmails[transactionId]
    if (!email) return
    try {
      const response = await api.post(`/api/transactions/${transactionId}/invite-counterparty/`, { email })
      setTransactions((prev) => prev.map((tx) => (tx.id === transactionId ? response.data : tx)))
      setInvitations((prev) => prev)
      setCounterpartyEmails((prev) => ({ ...prev, [transactionId]: '' }))
    } catch (error) {
      const detail = error.response?.data?.detail || 'Unable to send counterparty invite.'
      alert(detail)
    }
  }

  const activeInvitations = useMemo(() => invitations, [invitations])

  const renderTransactionInvites = (tx) => (
    <ul className="inline-list">
      {tx.invitations.map((invite) => (
        <li key={`${invite.email}-${invite.role}`}>
          <span className="badge">{invite.role_label}: {invite.email}</span>
        </li>
      ))}
    </ul>
  )

  return (
    <div className="page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <div className="badge-group">
          <Link className="button" to="/broker-application">Become a broker</Link>
          {profile?.is_broker && (
            <button type="button" onClick={() => setShowCreateForm((prev) => !prev)}>
              {showCreateForm ? 'Close form' : 'Create transaction'}
            </button>
          )}
        </div>
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

      {profile?.is_broker && showCreateForm && (
        <div className="card">
          <h2>Start a transaction</h2>
          {formError && <div className="error">{formError}</div>}
          {formSuccess && <div className="success">{formSuccess}</div>}
          <form onSubmit={handleCreateTransaction} className="form-grid">
            <label>
              Transaction name
              <input name="name" value={formData.name} onChange={handleFormChange} required />
            </label>
            <label>
              Property type
              <select name="property_type" value={formData.property_type} onChange={handleFormChange} required>
                <option value="" disabled>
                  Select a property type
                </option>
                {propertyTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Currency
              <select name="currency" value={formData.currency} onChange={handleFormChange}>
                {currencyOptions.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <label>
              Transaction type
              <select name="transaction_type" value={formData.transaction_type} onChange={handleFormChange}>
                {transactionTypes.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <label>
              Purchase price
              <input name="purchase_price" type="number" value={formData.purchase_price} onChange={handleFormChange} required />
            </label>
            <label>
              Earnest deposit
              <input name="earnest_deposit" type="number" value={formData.earnest_deposit} onChange={handleFormChange} required />
            </label>
            <label>
              Due diligence end date
              <input name="due_diligence_end_date" type="date" value={formData.due_diligence_end_date} onChange={handleFormChange} required />
            </label>
            <label>
              Estimated closing date
              <input name="estimated_closing_date" type="date" value={formData.estimated_closing_date} onChange={handleFormChange} required />
            </label>

            {formData.transaction_type === 'single_broker_sale' && (
              <>
                <label>
                  Buyer email
                  <input name="buyer_email" type="email" value={formData.buyer_email} onChange={handleFormChange} required />
                </label>
                <label>
                  Seller email
                  <input name="seller_email" type="email" value={formData.seller_email} onChange={handleFormChange} required />
                </label>
              </>
            )}

            {formData.transaction_type === 'double_broker_commission_split' && (
              <>
                <label>
                  Known party email
                  <input name="initiating_party_email" type="email" value={formData.initiating_party_email} onChange={handleFormChange} required />
                </label>
                <label>
                  Known party role
                  <select name="initiating_party_role" value={formData.initiating_party_role} onChange={handleFormChange}>
                    <option value="buyer">Buyer</option>
                    <option value="seller">Seller</option>
                  </select>
                </label>
                <label>
                  Secondary broker email
                  <input name="secondary_broker_email" type="email" value={formData.secondary_broker_email} onChange={handleFormChange} required />
                </label>
              </>
            )}

            <label>
              Additional participant emails (comma separated)
              <input name="participant_emails" value={formData.participant_emails} onChange={handleFormChange} placeholder="colleague@example.com, investor@example.com" />
            </label>

            <div className="form-actions">
              <button type="submit">Save transaction</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="tabs">
          <button className={activeTab === 'transactions' ? 'tab active' : 'tab'} onClick={() => setActiveTab('transactions')}>Transactions</button>
          <button className={activeTab === 'invitations' ? 'tab active' : 'tab'} onClick={() => setActiveTab('invitations')}>Invitations</button>
        </div>

        {activeTab === 'transactions' && (
          <div className="stack">
            {transactions.length === 0 && <p className="muted">You have no active transactions.</p>}
            {transactions.map((tx) => (
              <div key={tx.id} className="transaction-card">
                <div className="transaction-header">
                  <div>
                    <p className="eyebrow">{tx.transaction_type.replaceAll('_', ' ')}</p>
                    <h3>{tx.name}</h3>
                  </div>
                  <div className="badge-group">
                    <span className="badge">{tx.currency.toUpperCase()}</span>
                    <span className="badge">{tx.property_type}</span>
                  </div>
                </div>
                <p className="muted">Purchase price: {tx.purchase_price} | Earnest deposit: {tx.earnest_deposit}</p>
                <p className="muted">Due diligence ends: {tx.due_diligence_end_date} | Closing: {tx.estimated_closing_date}</p>
                {renderTransactionInvites(tx)}

                {tx.can_invite_counterparty && tx.pending_counterparty_role && (
                  <div className="inline-form">
                    <label>
                      Invite {tx.pending_counterparty_role}
                      <input
                        type="email"
                        value={counterpartyEmails[tx.id] || ''}
                        onChange={(event) =>
                          setCounterpartyEmails((prev) => ({ ...prev, [tx.id]: event.target.value }))
                        }
                        placeholder={`Enter ${tx.pending_counterparty_role} email`}
                      />
                    </label>
                    <button type="button" onClick={() => handleCounterpartyInvite(tx.id)}>
                      Send counterparty invite
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'invitations' && (
          <div className="stack">
            {activeInvitations.length === 0 && <p className="muted">You have no invitations.</p>}
            {activeInvitations.map((invite) => (
              <div key={invite.id} className="transaction-card">
                <div className="transaction-header">
                  <div>
                    <p className="eyebrow">{invite.transaction.transaction_type.replaceAll('_', ' ')}</p>
                    <h3>{invite.transaction.name}</h3>
                  </div>
                  <span className="badge">Invited as {invite.role_label}</span>
                </div>
                <p className="muted">Currency: {invite.transaction.currency.toUpperCase()} | Property: {invite.transaction.property_type}</p>
                <p className="muted">Purchase price: {invite.transaction.purchase_price} | Earnest deposit: {invite.transaction.earnest_deposit}</p>
                <p className="muted">Due diligence ends: {invite.transaction.due_diligence_end_date} | Closing: {invite.transaction.estimated_closing_date}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
