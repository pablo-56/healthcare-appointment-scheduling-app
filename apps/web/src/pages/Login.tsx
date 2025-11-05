import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { sendOtp, verifyOtp } from "../lib/api";

export default function Login() {
  const [search] = useSearchParams();
  const next = search.get("next") || "/book";
  const [identity, setIdentity] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [msg, setMsg] = useState("");
  const nav = useNavigate();

  async function onSend() {
    setMsg("");
    try {
      await sendOtp(identity);
      setSent(true);
      setMsg("Code sent. Check your phone/email.");
    } catch (e: any) {
      setMsg(e.message || "Failed to send code");
    }
  }

  async function onVerify() {
    setMsg("");
    try {
      await verifyOtp(identity, code);
      nav(next);
    } catch (e: any) {
      setMsg(e.message || "Invalid code");
    }
  }

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-2">Login (OTP)</h2>
      <div className="space-y-2 max-w-md">
        <input
          className="border p-2 w-full"
          placeholder="Phone or email"
          value={identity}
          onChange={(e) => setIdentity(e.target.value)}
        />
        {!sent ? (
          <button onClick={onSend} className="border px-3 py-1">Send code</button>
        ) : (
          <>
            <input
              className="border p-2 w-full"
              placeholder="Enter code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
            <div className="space-x-2">
              <button onClick={onVerify} className="border px-3 py-1">Verify</button>
              <button onClick={onSend} className="border px-3 py-1">Resend</button>
            </div>
          </>
        )}
        {msg && <p className="text-sm text-gray-400">{msg}</p>}
        <p className="text-sm">Back to <Link className="underline" to="/">Home</Link></p>
      </div>
    </div>
  );
}
