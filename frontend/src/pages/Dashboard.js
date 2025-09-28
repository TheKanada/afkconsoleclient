import React, { useContext, useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { 
  Plus, 
  Users, 
  Shield, 
  UserCheck, 
  Activity,
  MessageSquare,
  Wifi,
  WifiOff,
  RefreshCw,
  Settings
} from "lucide-react";
import axios from "axios";

const Dashboard = () => {
  const { user, API } = useContext(AuthContext);
  const [users, setUsers] = useState([]);
  const [newUser, setNewUser] = useState({
    username: "",
    password: "",
    role: "user"
  });
  const [loading, setLoading] = useState(false);
  const [showCreateUser, setShowCreateUser] = useState(false);

  useEffect(() => {
    if (user?.role === "admin" || user?.role === "moderator") {
      fetchUsers();
    }
  }, [user]);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`);
      setUsers(response.data);
    } catch (error) {
      console.error("Error fetching users:", error);
      toast.error("Failed to fetch users");
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await axios.post(`${API}/users`, newUser);
      toast.success("User created successfully");
      setNewUser({ username: "", password: "", role: "user" });
      setShowCreateUser(false);
      fetchUsers();
    } catch (error) {
      console.error("Error creating user:", error);
      toast.error(error.response?.data?.detail || "Failed to create user");
    } finally {
      setLoading(false);
    }
  };

  const getRoleIcon = (role) => {
    switch (role) {
      case "admin":
        return <Shield className="w-4 h-4" />;
      case "moderator":
        return <UserCheck className="w-4 h-4" />;
      default:
        return <Users className="w-4 h-4" />;
    }
  };

  const getRoleBadgeVariant = (role) => {
    switch (role) {
      case "admin":
        return "destructive";
      case "moderator":
        return "default";
      default:
        return "secondary";
    }
  };

  return (
    <div className="space-y-6 fade-in">
      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">
            Welcome back, {user?.username}!
          </h1>
          <p className="text-gray-400 mt-1">
            Manage your Minecraft AFK Console Client
          </p>
        </div>
        <Badge variant={getRoleBadgeVariant(user?.role)} className="text-sm">
          {getRoleIcon(user?.role)}
          <span className="ml-1 capitalize">{user?.role}</span>
        </Badge>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Active Accounts</p>
                <p className="text-2xl font-bold text-green-400">0</p>
              </div>
              <Users className="w-8 h-8 text-green-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Server Status</p>
                <p className="text-2xl font-bold text-red-400">Offline</p>
              </div>
              <div className="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center">
                <div className="w-3 h-3 rounded-full bg-white"></div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Messages Today</p>
                <p className="text-2xl font-bold text-yellow-400">0</p>
              </div>
              <div className="w-8 h-8 rounded-full bg-yellow-500 flex items-center justify-center text-black text-sm font-bold">
                M
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* User Management (Admin/Moderator only) */}
      {(user?.role === "admin" || user?.role === "moderator") && (
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white">User Management</CardTitle>
              {user?.role === "admin" && (
                <Button
                  onClick={() => setShowCreateUser(!showCreateUser)}
                  className="btn-minecraft"
                  data-testid="create-user-toggle-button"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create User
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {showCreateUser && user?.role === "admin" && (
              <div className="mb-6 p-4 bg-gray-700 rounded-lg">
                <h3 className="text-lg font-semibold text-white mb-4">Create New User</h3>
                <form onSubmit={handleCreateUser} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="username" className="text-gray-300">Username</Label>
                    <Input
                      id="username"
                      value={newUser.username}
                      onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                      className="bg-gray-600 border-gray-500 text-white"
                      placeholder="Enter username"
                      required
                      data-testid="new-user-username-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="password" className="text-gray-300">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      value={newUser.password}
                      onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                      className="bg-gray-600 border-gray-500 text-white"
                      placeholder="Enter password"
                      required
                      data-testid="new-user-password-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="role" className="text-gray-300">Role</Label>
                    <Select value={newUser.role} onValueChange={(value) => setNewUser({ ...newUser, role: value })}>
                      <SelectTrigger className="bg-gray-600 border-gray-500 text-white" data-testid="new-user-role-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="user">User</SelectItem>
                        <SelectItem value="moderator">Moderator</SelectItem>
                        <SelectItem value="admin">Administrator</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="md:col-span-3 flex gap-2">
                    <Button type="submit" disabled={loading} className="btn-minecraft" data-testid="create-user-submit-button">
                      {loading ? "Creating..." : "Create User"}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowCreateUser(false)}
                      className="border-gray-500 text-gray-300"
                    >
                      Cancel
                    </Button>
                  </div>
                </form>
              </div>
            )}

            <Separator className="my-4 bg-gray-600" />

            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-400">Current Users</h4>
              {users.length > 0 ? (
                <div className="grid gap-2">
                  {users.map((u) => (
                    <div key={u.id} className="flex items-center justify-between p-3 bg-gray-700 rounded-lg" data-testid={`user-item-${u.username}`}>
                      <div className="flex items-center gap-3">
                        {getRoleIcon(u.role)}
                        <span className="text-white font-medium">{u.username}</span>
                        <Badge variant={getRoleBadgeVariant(u.role)} className="text-xs">
                          {u.role}
                        </Badge>
                      </div>
                      <span className="text-gray-400 text-sm">
                        {new Date(u.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400 text-sm">No users found</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button variant="outline" className="h-20 flex flex-col items-center gap-2 border-gray-600 text-gray-300 hover:bg-gray-700">
              <Users className="w-6 h-6" />
              <span className="text-sm">View Accounts</span>
            </Button>
            <Button variant="outline" className="h-20 flex flex-col items-center gap-2 border-gray-600 text-gray-300 hover:bg-gray-700">
              <div className="w-6 h-6 rounded bg-green-500"></div>
              <span className="text-sm">Connect Server</span>
            </Button>
            <Button variant="outline" className="h-20 flex flex-col items-center gap-2 border-gray-600 text-gray-300 hover:bg-gray-700">
              <div className="w-6 h-6 rounded bg-yellow-500"></div>
              <span className="text-sm">View Chats</span>
            </Button>
            <Button variant="outline" className="h-20 flex flex-col items-center gap-2 border-gray-600 text-gray-300 hover:bg-gray-700">
              <div className="w-6 h-6 rounded bg-blue-500"></div>
              <span className="text-sm">Settings</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;