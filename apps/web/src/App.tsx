import { BrowserRouter, Routes, Route } from "react-router-dom";
import AdminTasks from "./pages/AdminTasks";
import AdminEligibility from "./pages/AdminEligibility";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Book from "./pages/Book";
import Confirm from "./pages/Confirm";
import Intake from "./pages/Intake";
import Consent from "./pages/Consent";
import Docs from "./pages/Docs";
import PrechartPage from "./pages/Prechart";
import ScribePage from "./pages/Scribe";
import PortalSummary from "./pages/PortalSummary";
import FollowUp from "./pages/FollowUp";
import BillingCases from "./pages/BillingCases";
import BillingClaim from "./pages/BillingClaim";
import PatientTasks from "./pages/PatientTasks";
import OpsEscalations from "./pages/OpsEscalations";
import AdminComplianceAudit from "./pages/AdminComplianceAudit";
import AdminCompliancePIA from "./pages/AdminCompliancePIA";
import AdminComplianceRetention from "./pages/AdminComplianceRetention"; 
import Analytics from "./pages/Analytics";
import Experiments from "./pages/Experiments"; 


export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/book" element={<Book />} />
        <Route path="/confirm" element={<Confirm />} />
        <Route path="/intake/:appointmentId" element={<Intake />} />
        <Route path="/consent/:requestId" element={<Consent />} />
        <Route path="/docs" element={<Docs />} />
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
      </Routes>
    </BrowserRouter>
  );
}
