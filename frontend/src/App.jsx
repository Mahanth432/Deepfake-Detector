import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import History from "./pages/History";
import Home from "./pages/Home";
import Analyze from "./pages/Analyze";
import Login from "./pages/Login";
import Register from "./pages/Register";

function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="app-main container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/analyze" element={<Analyze />} />
          <Route path="/history" element={<History />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
