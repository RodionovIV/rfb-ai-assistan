import { Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Project from "./pages/Project";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/projects/:projectId" element={<Project />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
