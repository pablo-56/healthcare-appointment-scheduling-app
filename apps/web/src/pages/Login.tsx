import React, { useState } from 'react'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function Login() {
    const [email, setEmail] = useState('')
    const [code, setCode] = useState('')
    const [token, setToken] = useState<string | undefined>()
    const [msg, setMsg] = useState<string | undefined>()

    const json = (r: Response) => r.json().catch(() => ({}))

    const sendOtp = async () => {
        setMsg(undefined)
        const r = await fetch(`${API}/v1/auth/otp:send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Purpose-Of-Use': 'OPERATIONS',
            },
            body: JSON.stringify({ email }),
        })
        const data = await json(r)
        if (!r.ok) {
            setMsg(`OTP error: ${r.status} ${data?.error || ''}`)
            return
        }
        alert('OTP sent (check API logs or Redis in dev)')
    }

    const login = async () => {
        setMsg(undefined)
        const r = await fetch(`${API}/v1/sessions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Purpose-Of-Use': 'OPERATIONS',
            },
            body: JSON.stringify({ email, code }),
        })
        const data = await json(r)
        if (!r.ok) {
            setMsg(`Login failed: ${r.status} ${data?.detail || data?.error || ''}`)
            return
        }
        setToken(data.token)
    }

    return (
        <div style={{ maxWidth: 420, margin: '40px auto', padding: 20, border: '1px solid #ddd' }}>
            <h2>Login via OTP</h2>

            <label>Email</label>
            <input
                placeholder="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ width: '100%' }}
            />
            <button onClick={sendOtp} disabled={!email}>Send OTP</button>

            <hr />

            <label>Code</label>
            <input
                placeholder="6-digit code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                style={{ width: '100%' }}
            />
            <button onClick={login} disabled={!email || !code}>Create Session</button>

            {msg && <p style={{ color: 'crimson' }}>{msg}</p>}
            {token && (
                <>
                    <h3>JWT</h3>
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{token}</pre>
                </>
            )}
        </div>
    )
}
