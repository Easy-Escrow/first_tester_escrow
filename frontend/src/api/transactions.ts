import api from './client'
import type { TransactionCreateRequest, TransactionListItem } from '../types/transactions'

export function listTransactions() {
  return api.get<TransactionListItem[]>('/api/transactions/')
}

export function createTransaction(data: TransactionCreateRequest) {
  return api.post('/api/transactions/', data)
}
