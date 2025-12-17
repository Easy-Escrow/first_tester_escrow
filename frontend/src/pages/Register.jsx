import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'

export default function Register() {
  const [form, setForm] = useState({ email: '', password: '', first_name: '', last_name: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const navigate = useNavigate()

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/api/auth/register/', form)
      setSuccess('Registration successful. Please log in.')
      setTimeout(() => navigate('/login'), 800)
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed')
    }
  }

  return (
    <div className="auth-container">
      <h1>Register</h1>
      <form className="card" onSubmit={handleSubmit}>
        <label>
          Email
          <input type="email" name="email" value={form.email} onChange={handleChange} required />
        </label>
        <label>
          Password
          <input type="password" name="password" value={form.password} onChange={handleChange} required />
        </label>
        <label>
          First name
          <input type="text" name="first_name" value={form.first_name} onChange={handleChange} />
        </label>
        <label>
          Last name
          <input type="text" name="last_name" value={form.last_name} onChange={handleChange} />
        </label>
        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}
        <button type="submit">Create Account</button>
      </form>
      <p>Already registered? <Link to="/login">Log in</Link></p>
    </div>
  )
}
