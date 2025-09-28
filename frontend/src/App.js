import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";

// Import pages
import AdminSetup from "./pages/AdminSetup";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import AccountsPage from "./pages/AccountsPage";
import ChatsPage from "./pages/ChatsPage";
import ConnectPage from "./pages/ConnectPage";

// Import components
import Layout from "./components/Layout";

// Import styles
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
export const AuthContext = React.createContext();

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [adminExists, setAdminExists] = useState(false);

  // Check if admin exists on app load
  useEffect(() => {
    checkAdminExists();
    checkAuthToken();
  }, []);

  const checkAdminExists = async () => {
    try {
      const response = await axios.get(`${API}/auth/check-admin`);
      setAdminExists(response.data.admin_exists);
    } catch (error) {
      console.error('Error checking admin status:', error);
      toast.error('Failed to check admin status');
    }
  };

  const checkAuthToken = () => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      try {
        const user = JSON.parse(userData);
        setUser(user);
        // Set axios default header
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      } catch (error) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  };

  const login = (token, userData) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    toast.success(`Welcome back, ${userData.username}!`);
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
    toast.success('Logged out successfully');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-green-400 text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, API }}>
      <div className="App">
        <BrowserRouter>
          <Routes>
            {/* Admin Setup Route */}
            {!adminExists && (
              <Route path="/setup" element={<AdminSetup setAdminExists={setAdminExists} />} />
            )}
            
            {/* Login Route */}
            <Route path="/login" element={<Login />} />
            
            {/* Protected Routes */}
            {user ? (
              <Route path="/" element={<Layout />}>
                <Route index element={<Dashboard />} />
                <Route path="accounts" element={<AccountsPage />} />
                <Route path="chats" element={<ChatsPage />} />
                <Route path="connect" element={<ConnectPage />} />
              </Route>
            ) : (
              <Route path="*" element={<Navigate to={!adminExists ? "/setup" : "/login"} />} />
            )}
            
            {/* Catch all redirect */}
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </div>
    </AuthContext.Provider>
  );
}

export default App;