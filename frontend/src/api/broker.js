import api from './client'

export async function fetchBrokerApplication() {
  const response = await api.get('/api/broker/application/')
  return response.data
}

export async function submitBrokerApplication(formValues, fileValues) {
  const formData = new FormData()

  const detailKeys = [
    'date_of_birth',
    'curp',
    'rfc',
    'nationality',
    'address',
    'mobile_phone',
    'occupation',
  ]

  detailKeys.forEach((key) => {
    if (formValues[key] !== undefined && formValues[key] !== null) {
      formData.append(key, formValues[key])
    }
  })

  if (formValues.additional_details) {
    formData.append('additional_details', JSON.stringify(formValues.additional_details))
  }

  if (fileValues.id_document_primary) formData.append('id_document_primary', fileValues.id_document_primary)
  if (fileValues.id_document_secondary) formData.append('id_document_secondary', fileValues.id_document_secondary)
  if (fileValues.selfie_with_id) formData.append('selfie_with_id', fileValues.selfie_with_id)

  const response = await api.post('/api/broker/application/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}
