import { useEffect, useState } from 'react'
import api from '../api/client'

export default function useApiHealth(intervalMs = 5000) {
  const [status, setStatus] = useState('unknown')

  useEffect(() => {
    let isMounted = true
    const checkHealth = async () => {
      try {
        const response = await api.get('/api/health/')
        if (!isMounted) return
        setStatus(response.data?.status === 'ok' ? 'online' : 'degraded')
      } catch (error) {
        if (!isMounted) return
        setStatus('offline')
      }
    }

    checkHealth()
    const timer = setInterval(checkHealth, intervalMs)
    return () => {
      isMounted = false
      clearInterval(timer)
    }
  }, [intervalMs])

  return status
}
