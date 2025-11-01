import React, { useState } from 'react'
import { triageAndSlots, bookAppointment } from '../api'
import { useNavigate } from 'react-router-dom'

export default function Book() {
    const [email, setEmail] = useState('')
    const [reason, setReason] = useState('annual physical')
    const [slots, setSlots] = useState<any[]>([])
    const [picked, setPicked] = useState<any | null>(null)
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const find = async () => {
        setLoading(true)
        try {
            const d = await triageAndSlots(reason)
            setSlots(d.slots || [])
        } finally { setLoading(false) }
    }

    const book = async () => {
        if (!picked) return
        const res = await bookAppointment({
            patient_email: email || undefined,
            reason,
            start: picked.start,
            end: picked.end,
            slot_id: picked.slot_id,
        })
        navigate('/confirm', { state: { confirmation: res, reason, picked } })
    }

    return (
        <div style={{ padding: 20 }}>
            <h2>Book an appointment</h2>
            <label>Email (optional for confirmation)</label><br />
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" style={{ width: 320 }} /><br /><br />
            <label>Reason for visit</label><br />
            <input value={reason} onChange={e => setReason(e.target.value)} style={{ width: 320 }} />
            <button onClick={find} disabled={loading}>Find availability</button>

            <h3>Available slots</h3>
            {slots.length === 0 && <p>No slots yet — click "Find availability".</p>}
            {slots.map((s, i) => (
                <div key={i} style={{ border: '1px solid #ddd', padding: 8, marginBottom: 6, background: picked?.slot_id === s.slot_id ? '#eef' : '#fff' }}>
                    <div><b>{s.start}</b> → {s.end}</div>
                    <button onClick={() => setPicked(s)}>Pick this</button>
                </div>
            ))}
            <hr />
            <button disabled={!picked} onClick={book}>Book selected slot</button>
        </div>
    )
}
