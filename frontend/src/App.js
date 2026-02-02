import "@/App.css";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { Shield, History, FileText } from "lucide-react";
import Dashboard from "@/pages/Dashboard";
import RunHistory from "@/pages/RunHistory";
import RunDetails from "@/pages/RunDetails";

const Header = () => {
  return (
    <header className="header-sticky" data-testid="main-header">
      <div className="container-main py-4 flex items-center justify-between">
        <NavLink to="/" className="flex items-center gap-3" data-testid="logo-link">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" strokeWidth={1.5} />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tight text-slate-900">DQ Sentinel</h1>
            <p className="text-xs text-slate-500">Data Quality Monitor</p>
          </div>
        </NavLink>
        
        <nav className="flex items-center gap-6" data-testid="main-nav">
          <NavLink 
            to="/" 
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            data-testid="nav-dashboard"
            end
          >
            Dashboard
          </NavLink>
          <NavLink 
            to="/history" 
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            data-testid="nav-history"
          >
            <span className="flex items-center gap-1.5">
              <History className="w-4 h-4" strokeWidth={1.5} />
              Run History
            </span>
          </NavLink>
        </nav>
      </div>
    </header>
  );
};

const Footer = () => {
  return (
    <footer className="border-t border-slate-200 mt-auto" data-testid="main-footer">
      <div className="container-main py-6 flex items-center justify-between text-sm text-slate-500">
        <p>© 2024 DQ Sentinel. Data Quality Made Simple.</p>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <FileText className="w-4 h-4" strokeWidth={1.5} />
            10 DQ Rules
          </span>
        </div>
      </div>
    </footer>
  );
};

function App() {
  return (
    <div className="App flex flex-col min-h-screen">
      <BrowserRouter>
        <Header />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/history" element={<RunHistory />} />
            <Route path="/runs/:runId" element={<RunDetails />} />
          </Routes>
        </main>
        <Footer />
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </div>
  );
}

export default App;
