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
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [dashboardStats, setDashboardStats] = useState({
    active_accounts: 0,
    total_accounts: 0,
    server_status: "offline",
    messages_today: 0,
    online_accounts: [],
    recent_activity: []
  });
  const [newUser, setNewUser] = useState({
    username: "",
    password: "",
    role: "user"
  });
  const [loading, setLoading] = useState(false);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Real-time updates
  const fetchDashboardStats = useCallback(async () => {
    if (user?.role === "admin" || user?.role === "moderator") {
      try {
        const response = await axios.get(`${API}/dashboard/stats`);
        setDashboardStats(response.data);
        setLastUpdated(new Date());
      } catch (error) {
        console.error("Error fetching dashboard stats:", error);
      }
    }
  }, [API, user?.role]);

  useEffect(() => {
    if (user?.role === "admin" || user?.role === "moderator") {
      fetchDashboardStats();
      if (user.role === "admin") {
        fetchUsers();
      }
      
      // Set up real-time updates every 5 seconds
      const interval = setInterval(() => {
        fetchDashboardStats();
      }, 5000);
      
      return () => clearInterval(interval);
    }
  }, [user, fetchDashboardStats]);

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

      {/* User Dashboard for regular users */}
      {user?.role === "user" && (
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-8 text-center">
            <Users className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h3 className="text-xl font-semibold text-white mb-2">Welcome to AFK Console</h3>
            <p className="text-gray-400 mb-6">
              Use the navigation menu to access your Minecraft accounts, manage connections, 
              and monitor chat messages.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Button 
                variant="outline" 
                onClick={() => navigate("/accounts")}
                className="border-gray-600 text-gray-300 hover:bg-gray-700"
              >
                <Users className="w-4 h-4 mr-2" />
                My Accounts
              </Button>
              <Button 
                variant="outline" 
                onClick={() => navigate("/chats")}
                className="border-gray-600 text-gray-300 hover:bg-gray-700"
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                Chat Monitor
              </Button>
              <Button 
                variant="outline" 
                onClick={() => navigate("/connect")}
                className="border-gray-600 text-gray-300 hover:bg-gray-700"
              >
                <Wifi className="w-4 h-4 mr-2" />
                Connect Server
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Real-time Stats Cards */}
      {(user?.role === "admin" || user?.role === "moderator") && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Active Accounts</p>
                  <p className="text-2xl font-bold text-green-400">{dashboardStats.active_accounts}</p>
                  <p className="text-xs text-gray-500">of {dashboardStats.total_accounts} total</p>
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
                  <p className={`text-2xl font-bold ${
                    dashboardStats.server_status === "online" ? "text-green-400" : "text-red-400"
                  }`}>
                    {dashboardStats.server_status === "online" ? "Online" : "Offline"}
                  </p>
                </div>
                {dashboardStats.server_status === "online" ? (
                  <Wifi className="w-8 h-8 text-green-400" />
                ) : (
                  <WifiOff className="w-8 h-8 text-red-400" />
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Messages Today</p>
                  <p className="text-2xl font-bold text-yellow-400">{dashboardStats.messages_today}</p>
                </div>
                <MessageSquare className="w-8 h-8 text-yellow-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Last Updated</p>
                  <p className="text-sm font-bold text-blue-400">
                    {lastUpdated.toLocaleTimeString()}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={fetchDashboardStats}
                    className="mt-1 p-0 h-auto text-xs text-gray-400 hover:text-white"
                  >
                    <RefreshCw className="w-3 h-3 mr-1" />
                    Refresh
                  </Button>
                </div>
                <Activity className="w-8 h-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Online Accounts & Recent Activity */}
      {(user?.role === "admin" || user?.role === "moderator") && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Online Accounts */}
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Online Accounts ({dashboardStats.online_accounts.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dashboardStats.online_accounts.length > 0 ? (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {dashboardStats.online_accounts.map((account) => (
                    <div key={account.id} className="flex items-center justify-between p-2 bg-gray-700 rounded">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                        <span className="text-white text-sm">
                          {account.account_type === "microsoft" ? account.email : account.nickname}
                        </span>
                        <Badge variant="secondary" className="text-xs">
                          {account.account_type}
                        </Badge>
                      </div>
                      <span className="text-gray-400 text-xs">
                        {account.last_seen ? new Date(account.last_seen).toLocaleTimeString() : "Active"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-gray-400">
                  <WifiOff className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No accounts currently online</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <MessageSquare className="w-5 h-5" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dashboardStats.recent_activity.length > 0 ? (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {dashboardStats.recent_activity.map((activity, index) => (
                    <div key={index} className="flex items-start gap-3 p-2 bg-gray-700 rounded">
                      <div className="w-2 h-2 bg-blue-400 rounded-full mt-2"></div>
                      <div className="flex-1">
                        <p className="text-white text-sm truncate">{activity.message}</p>
                        <p className="text-gray-400 text-xs">
                          {activity.timestamp ? new Date(activity.timestamp).toLocaleString() : "Recent"}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-gray-400">
                  <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No recent activity</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* User Management (Admin only) */}
      {user?.role === "admin" && (
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white">User Management</CardTitle>
              <Button
                onClick={() => setShowCreateUser(!showCreateUser)}
                className="btn-minecraft"
                data-testid="create-user-toggle-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create User
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {showCreateUser && (
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
            <Button 
              variant="outline" 
              onClick={() => navigate("/accounts")}
              className="h-20 flex flex-col items-center gap-2 border-gray-600 text-gray-300 hover:bg-gray-700 hover:border-green-500"
              data-testid="quick-action-accounts"
            >
              <Users className="w-6 h-6" />
              <span className="text-sm">Manage Accounts</span>
            </Button>
            
            <Button 
              variant="outline" 
              onClick={() => navigate("/connect")}
              className="h-20 flex flex-col items-center gap-2 border-gray-600 text-gray-300 hover:bg-gray-700 hover:border-green-500"
              data-testid="quick-action-connect"
            >
              <Wifi className="w-6 h-6" />
              <span className="text-sm">Connect Server</span>
            </Button>
            
            <Button 
              variant="outline" 
              onClick={() => navigate("/chats")}
              className="h-20 flex flex-col items-center gap-2 border-gray-600 text-gray-300 hover:bg-gray-700 hover:border-yellow-500"
              data-testid="quick-action-chats"
            >
              <MessageSquare className="w-6 h-6" />
              <span className="text-sm">View Chats</span>
            </Button>
            
            <Button 
              variant="outline" 
              onClick={() => navigate("/connect")}
              className="h-20 flex flex-col items-center gap-2 border-gray-600 text-gray-300 hover:bg-gray-700 hover:border-blue-500"
              data-testid="quick-action-settings"
            >
              <Settings className="w-6 h-6" />
              <span className="text-sm">Bot Settings</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;