import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Welcome</h1>
      <p className="mb-4">Start by <Link to="/book" className="underline">booking</Link> an appointment, or <Link to="/login" className="underline">log in</Link>.</p>
      <div className="space-x-4">
        <Link to="/book">Book</Link>
        <Link to="/login">Login</Link>
      </div>
    </div>
  );
}
