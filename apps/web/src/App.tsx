import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Suspense, lazy } from "react";
import Home from "./pages/Home";

// Lazy-load everything else so missing files don't crash the initial render
const Login = lazy(() => import("./pages/Login"));
const Book = lazy(() => import("./pages/Book"));
const Confirm = lazy(() => import("./pages/Confirm"));
const Intake = lazy(() => import("./pages/Intake"));
const Consent = lazy(() => import("./pages/Consent"));
const Docs = lazy(() => import("./pages/Docs"));
const CheckIn = lazy(() => import("./pages/CheckIn"));
const Queue = lazy(() => import("./pages/Queue"));
const AdminEligibility = lazy(() => import("./pages/AdminEligibility"));
const AdminTasks = lazy(() => import("./pages/AdminTasks"));
const PrechartPage = lazy(() => import("./pages/Prechart"));
const ScribePage = lazy(() => import("./pages/Scribe"));
const PortalSummary = lazy(() => import("./pages/PortalSummary"));
const FollowUp = lazy(() => import("./pages/FollowUp"));
const BillingCases = lazy(() => import("./pages/BillingCases"));
const BillingClaim = lazy(() => import("./pages/BillingClaim"));
const PatientTasks = lazy(() => import("./pages/PatientTasks"));
const OpsEscalations = lazy(() => import("./pages/OpsEscalations"));
const AdminComplianceAudit = lazy(() => import("./pages/AdminComplianceAudit"));
const AdminCompliancePIA = lazy(() => import("./pages/AdminCompliancePIA"));
const AdminComplianceRetention = lazy(() => import("./pages/AdminComplianceRetention"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Experiments = lazy(() => import("./pages/Experiments"));
import { RoleGuard } from "./components/RoleGuard";

export default function App() {
  return (
    <BrowserRouter>
      
        <RoleGuard>
        <Suspense fallback={<div className="p-4 text-gray-300">Loading…</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/book" element={<Book />} />
            <Route path="/confirm" element={<Confirm />} />
            <Route path="/intake/:appointmentId" element={<Intake />} />
            <Route path="/consent/:requestId" element={<Consent />} />
            <Route path="/docs" element={<Docs />} />
            <Route path="/check-in" element={<CheckIn />} />
            <Route path="/ops/queue" element={<Queue />} />
            <Route path="/admin/billing/eligibility" element={<AdminEligibility />} />
            <Route path="/admin/tasks" element={<AdminTasks />} />
            <Route path="/provider/prechart/:appointmentId" element={<PrechartPage />} />
            <Route path="/provider/scribe/:appointmentId" element={<ScribePage />} />
            <Route path="/portal/summary/:encounterId" element={<PortalSummary />} />
            <Route path="/portal/follow-up" element={<FollowUp />} />
            <Route path="/billing/cases" element={<BillingCases />} />
            <Route path="/billing/claims/:id" element={<BillingClaim />} />
            <Route path="/portal/tasks" element={<PatientTasks />} />
            <Route path="/ops/escalations" element={<OpsEscalations />} />
            <Route path="/admin/compliance/audit" element={<AdminComplianceAudit />} />
            <Route path="/admin/compliance/pia" element={<AdminCompliancePIA />} />
            <Route path="/admin/compliance/retention" element={<AdminComplianceRetention />} />
            <Route path="/admin/analytics" element={<Analytics />} />
            <Route path="/admin/experiments" element={<Experiments />} />
            <Route path="*" element={<div className="p-6 text-gray-100">Not found</div>} />
          </Routes>
        </Suspense>
      </RoleGuard>
    </BrowserRouter>
  );
}
