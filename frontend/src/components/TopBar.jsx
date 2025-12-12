import { Link, useNavigate, useLocation } from 'react-router-dom'
import useApiHealth from '../hooks/useApiHealth'
import { clearSession, getToken } from '../api/session'

const statusColors = {
  online: '#32cd32',
  offline: '#ff4d4f',
  degraded: '#f0ad4e',
  unknown: '#d9d9d9'
}

export default function TopBar() {
  const status = useApiHealth()
  const navigate = useNavigate()
  const token = getToken()
  const location = useLocation()

  const handleLogout = () => {
    clearSession()
    navigate('/login')
  }

  const indicatorColor = statusColors[status] || statusColors.unknown

  return (
    <header className="top-bar">
      <div className="brand">Escrow Starter</div>
      <div className="nav-links">
        {token ? (
          <button className="link-button" onClick={handleLogout}>Logout</button>
        ) : (
          <>
            {location.pathname !== '/login' && <Link to="/login">Login</Link>}
            {location.pathname !== '/register' && <Link to="/register">Register</Link>}
          </>
        )}
      </div>
      <div className="status" title={`API status: ${status}`}>
        <span className="status-dot" style={{ backgroundColor: indicatorColor }} />
        <span className="status-text">{status}</span>
      </div>
    </header>
  )
}
