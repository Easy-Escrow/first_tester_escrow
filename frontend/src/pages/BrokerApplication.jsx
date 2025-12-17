import { useEffect, useMemo, useState } from 'react'
import { fetchBrokerApplication, submitBrokerApplication } from '../api/broker'

const requirementFields = [
  { name: 'date_of_birth', label: 'Date of birth', type: 'date', placeholder: 'YYYY-MM-DD' },
  { name: 'curp', label: 'Mexican CURP', type: 'text', placeholder: '18-character CURP' },
  { name: 'rfc', label: 'Mexican RFC', type: 'text', placeholder: '13-character RFC' },
  { name: 'nationality', label: 'Nationality', type: 'text', placeholder: 'e.g. Mexican' },
  { name: 'address', label: 'Current address', type: 'text', placeholder: 'Street, city, state, ZIP' },
  { name: 'mobile_phone', label: 'Mobile phone number', type: 'tel', placeholder: '+52...' },
  { name: 'occupation', label: 'Occupation', type: 'text', placeholder: 'What do you do?' },
]

export default function BrokerApplication() {
  const defaultFormValues = useMemo(
    () => ({
      additional_details: '',
      ...requirementFields.reduce((acc, field) => ({ ...acc, [field.name]: '' }), {}),
    }),
    []
  )

  const [formValues, setFormValues] = useState(defaultFormValues)
  const [fileValues, setFileValues] = useState({
    id_document_primary: null,
    id_document_secondary: null,
    selfie_with_id: null,
  })
  const [statusMessage, setStatusMessage] = useState('')
  const [error, setError] = useState('')
  const [isBroker, setIsBroker] = useState(false)
  const [existingApplication, setExistingApplication] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const loadApplication = async () => {
      try {
        const data = await fetchBrokerApplication()
        setIsBroker(Boolean(data.is_broker))
        if (data.application) {
          setExistingApplication(data.application)
          const hydrated = { ...defaultFormValues }
          requirementFields.forEach(({ name }) => {
            hydrated[name] = data.application[name] || ''
          })
          setFormValues(hydrated)
        }
      } catch (err) {
        setError('Unable to load your broker application details right now.')
      } finally {
        setLoading(false)
      }
    }

    loadApplication()
  }, [defaultFormValues])

  const handleInputChange = (event) => {
    const { name, value } = event.target
    setFormValues((prev) => ({ ...prev, [name]: value }))
  }

  const handleFileChange = (event) => {
    const { name, files } = event.target
    setFileValues((prev) => ({ ...prev, [name]: files?.[0] || null }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    setStatusMessage('')

    try {
      const payload = {
        ...formValues,
        additional_details: formValues.additional_details
          ? { notes: formValues.additional_details }
          : undefined,
      }
      const response = await submitBrokerApplication(payload, fileValues)
      setExistingApplication(response.application)
      setIsBroker(Boolean(response.is_broker))
      setStatusMessage('Your broker details have been submitted.')
    } catch (err) {
      const apiError = err.response?.data
      const detail = typeof apiError === 'string' ? apiError : apiError?.detail
      setError(detail || 'Unable to submit broker details. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="page">
        <h1>Broker onboarding</h1>
        <div className="card">Loading your information...</div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Upgrade your account</p>
          <h1>Broker onboarding</h1>
        </div>
        <div className="badge-group">
          <span className={`badge ${isBroker ? 'badge-success' : 'badge-muted'}`}>
            {isBroker ? 'Broker' : 'Standard user'}
          </span>
          {existingApplication && (
            <span className="badge badge-info">Application status: {existingApplication.status}</span>
          )}
        </div>
      </div>

      <div className="card">
        <p>
          Provide the information below so we can categorize your account as a broker.
          The fields are driven by a requirements list so we can adjust them later without
          rebuilding the page.
        </p>

        {error && <div className="error">{error}</div>}
        {statusMessage && <div className="success">{statusMessage}</div>}

        <form className="form-grid" onSubmit={handleSubmit}>
          <section>
            <h2>Identity documents</h2>
            <label>
              Primary ID (passport/INE)
              <input
                type="file"
                name="id_document_primary"
                accept="image/*,.pdf"
                onChange={handleFileChange}
                required={!existingApplication}
              />
              {existingApplication?.id_document_primary && (
                <small>Uploaded: {existingApplication.id_document_primary.split('/').slice(-1)}</small>
              )}
            </label>

            <label>
              Secondary ID
              <input
                type="file"
                name="id_document_secondary"
                accept="image/*,.pdf"
                onChange={handleFileChange}
                required={!existingApplication}
              />
              {existingApplication?.id_document_secondary && (
                <small>Uploaded: {existingApplication.id_document_secondary.split('/').slice(-1)}</small>
              )}
            </label>

            <label>
              Selfie holding your ID
              <input
                type="file"
                name="selfie_with_id"
                accept="image/*"
                onChange={handleFileChange}
                required={!existingApplication}
              />
              {existingApplication?.selfie_with_id && (
                <small>Uploaded: {existingApplication.selfie_with_id.split('/').slice(-1)}</small>
              )}
            </label>
          </section>

          <section>
            <h2>Personal details</h2>
            {requirementFields.map((field) => (
              <label key={field.name}>
                {field.label}
                <input
                  type={field.type}
                  name={field.name}
                  placeholder={field.placeholder}
                  value={formValues[field.name]}
                  onChange={handleInputChange}
                  required={!existingApplication}
                />
              </label>
            ))}

            <label>
              Additional notes (optional)
              <textarea
                name="additional_details"
                placeholder="Anything else we should know?"
                value={formValues.additional_details}
                onChange={handleInputChange}
                rows={3}
              />
            </label>
          </section>

          <div className="form-actions">
            <button type="submit" disabled={submitting}>
              {submitting ? 'Submitting...' : existingApplication ? 'Update details' : 'Submit application'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
