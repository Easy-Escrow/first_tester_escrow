import api from './client'
import type { TransactionCreateRequest, TransactionDetail, TransactionListItem } from '../types/transactions'

export function listTransactions() {
  return api.get<TransactionListItem[]>('/api/transactions/')
}

export function createTransaction(data: TransactionCreateRequest) {
  return api.post('/api/transactions/', data)
}

export function getTransaction(id: string) {
  return api.get<TransactionDetail>(`/api/transactions/${id}/`)
}
