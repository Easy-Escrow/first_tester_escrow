import api from './client'

export function listTransactions() {
  return api.get('/api/transactions/')
}

export function createTransaction(data) {
  return api.post('/api/transactions/', data)
}
