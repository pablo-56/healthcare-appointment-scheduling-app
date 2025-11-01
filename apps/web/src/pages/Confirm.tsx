import React from 'react'
import { useLocation, Link } from 'react-router-dom'

export default function Confirm() {
    const loc = useLocation() as any
    const conf = loc.state?.confirmation
    const picked = loc.state?.picked
    const reason = loc.state?.reason

    if (!conf) return <div style={{ padding: 20 }}><p>No confirmation found. Go to <Link to="/book">/book</Link>.</p></div>

    return (
        <div style={{ padding: 20 }}>
            <h2>Booked!</h2>
            <p><b>FHIR Appointment ID:</b> {conf.fhir_appointment_id}</p>
            <p><b>Status:</b> {conf.status}</p>
            <p><b>When:</b> {picked?.start} → {picked?.end}</p>
            <p><b>Reason:</b> {reason}</p>
            <p><b>Intake link:</b> <a href={conf.intake_link} target="_blank">{conf.intake_link}</a></p>
            <p><Link to="/book">Book another</Link></p>
        </div>
    )
}
