import React, { useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Shield, User, Lock, Eye, EyeOff } from "lucide-react";
import axios from "axios";

const AdminSetup = ({ setAdminExists }) => {
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    confirmPassword: "",
  });
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { login, API } = useContext(AuthContext);
  const navigate = useNavigate();

  const validateForm = () => {
    const errors = [];
    
    if (!formData.username.trim()) {
      errors.push("Username is required");
    } else if (formData.username.length < 3) {
      errors.push("Username must be at least 3 characters");
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      errors.push("Username can only contain letters, numbers, and underscores");
    }
    
    if (!formData.password) {
      errors.push("Password is required");
    } else if (formData.password.length < 6) {
      errors.push("Password must be at least 6 characters");
    } else if (formData.password.length > 128) {
      errors.push("Password must be less than 128 characters");
    }
    
    if (formData.password !== formData.confirmPassword) {
      errors.push("Passwords do not match");
    }
    
    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const validationErrors = validateForm();
    if (validationErrors.length > 0) {
      validationErrors.forEach(error => toast.error(error));
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/setup-admin`, {
        username: formData.username,
        password: formData.password,
        role: "admin",
      });

      login(response.data.access_token, response.data.user);
      setAdminExists(true);
      navigate("/");
      toast.success("Admin account created successfully! Database initialized.");
    } catch (error) {
      console.error("Admin setup error:", error);
      
      if (error.response?.status === 503) {
        toast.error("Database connection failed", {
          description: "Please ensure MongoDB is running and properly configured"
        });
      } else if (error.response?.data?.detail?.includes("Database")) {
        toast.error("Database setup error", {
          description: error.response.data.detail
        });
      } else {
        toast.error(error.response?.data?.detail || "Failed to create admin account");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mb-4">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <CardTitle className="text-2xl text-white">
              Setup Administrator Account
            </CardTitle>
            <p className="text-gray-400 mt-2">
              Create the first admin account for your Minecraft AFK Console Client
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username" className="text-gray-300">
                  Administrator Username
                </Label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="username"
                    name="username"
                    type="text"
                    required
                    value={formData.username}
                    onChange={handleInputChange}
                    className="pl-10 bg-gray-700 border-gray-600 text-white"
                    placeholder="Enter admin username"
                    data-testid="admin-username-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-gray-300">
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    required
                    value={formData.password}
                    onChange={handleInputChange}
                    className="pl-10 pr-10 bg-gray-700 border-gray-600 text-white"
                    placeholder="Enter password"
                    data-testid="admin-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-gray-400 hover:text-gray-200"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-gray-300">
                  Confirm Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type={showPassword ? "text" : "password"}
                    required
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    className="pl-10 bg-gray-700 border-gray-600 text-white"
                    placeholder="Confirm password"
                    data-testid="admin-confirm-password-input"
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full btn-minecraft mt-6"
                disabled={loading}
                data-testid="create-admin-button"
              >
                {loading ? "Creating Account..." : "Create Administrator Account"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AdminSetup;