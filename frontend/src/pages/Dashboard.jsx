import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'

export default function Dashboard() {
  const [message, setMessage] = useState('Fetching profile...')
  const [profile, setProfile] = useState(null)

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
    loadProfile()
  }, [])

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
    </div>
  )
}
