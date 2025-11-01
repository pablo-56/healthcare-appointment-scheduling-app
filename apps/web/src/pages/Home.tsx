import React from 'react'

export default function Home() {
    return (
        <div style={{ padding: 20 }}>
            <h1>Healthcare App — Dev Home</h1>
            <ul>
                <li><a href="/login">Login (OTP)</a></li>
                <li><a href="http://localhost:8000/docs" target="_blank">API Docs</a></li>
                <li><a href="http://localhost:8000/metrics" target="_blank">/metrics</a></li>
                <li><a href="http://localhost:3000" target="_blank">Grafana</a></li>
            </ul>
        </div>
    )
}
