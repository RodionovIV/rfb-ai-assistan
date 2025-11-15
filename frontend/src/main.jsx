import axios from "axios";
import { getApiBaseUrl } from "./config/api";

const resolveBaseUrl = () => {
  const resolved = getApiBaseUrl();
  if (resolved) {
    return resolved;
  }
  if (typeof window !== "undefined" && window.location) {
    return `${window.location.protocol}//${window.location.host}`;
  }
  return "";
};

axios.defaults.baseURL = resolveBaseUrl();

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
