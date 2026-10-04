import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CropCheck from './pages/CropCheck';
import Result from './pages/Result';
import Assistant from './pages/Assistant';
import Weather from './pages/Weather';
import './i18n/i18n';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="login" element={<Login />} />
          <Route path="register" element={<Login />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="crop" element={<CropCheck />} />
          <Route path="result" element={<Result />} />
          <Route path="assistant" element={<Assistant />} />
          <Route path="weather" element={<Weather />} />
          {/* Add more routes here */}
          <Route path="*" element={<Dashboard />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
