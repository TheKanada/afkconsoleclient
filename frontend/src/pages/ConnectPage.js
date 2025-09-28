import React, { useState, useEffect, useContext } from "react";
import { AuthContext } from "../App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import { 
  Wifi, 
  WifiOff, 
  Settings, 
  Play, 
  Square, 
  Trash2, 
  RotateCcw,
  MessageCircle,
  Globe,
  Clock,
  Shield,
  Zap,
  Users
} from "lucide-react";
import axios from "axios";

const ConnectPage = () => {
  const { API } = useContext(AuthContext);
  const [accounts, setAccounts] = useState([]);
  const [serverSettings, setServerSettings] = useState({
    server_ip: "",
    login_delay: 5,
    offline_accounts_enabled: true,
    anti_afk_enabled: false,
    auto_connect_enabled: false,
    login_message_enabled: false,
    login_messages: [],
    world_change_messages_enabled: false,
    world_change_messages: []
  });
  const [selectedAccounts, setSelectedAccounts] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState("disconnected"); // connected, connecting, disconnected
  const [showLoginMessagesDialog, setShowLoginMessagesDialog] = useState(false);
  const [showWorldMessagesDialog, setShowWorldMessagesDialog] = useState(false);
  const [newLoginMessage, setNewLoginMessage] = useState({ message: "", delay: 2 });
  const [newWorldMessage, setNewWorldMessage] = useState({ message: "", delay: 2 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAccounts();
    fetchServerSettings();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await axios.get(`${API}/accounts`);
      setAccounts(response.data);
    } catch (error) {
      console.error("Error fetching accounts:", error);
      toast.error("Failed to fetch accounts");
    }
  };

  const fetchServerSettings = async () => {
    try {
      const response = await axios.get(`${API}/server-settings`);
      setServerSettings(response.data);
    } catch (error) {
      console.error("Error fetching server settings:", error);
      toast.error("Failed to fetch server settings");
    }
  };

  const updateServerSettings = async (updates) => {
    try {
      const response = await axios.put(`${API}/server-settings`, updates);
      setServerSettings(response.data);
      toast.success("Settings updated");
    } catch (error) {
      console.error("Error updating server settings:", error);
      toast.error("Failed to update settings");
    }
  };

  const handleConnect = async () => {
    if (!serverSettings.server_ip.trim()) {
      toast.error("Please enter a server IP address");
      return;
    }

    if (selectedAccounts.length === 0) {
      toast.error("Please select at least one account");
      return;
    }

    setLoading(true);
    setConnectionStatus("connecting");

    try {
      const response = await axios.post(`${API}/server/connect`);
      
      if (response.data.simulation) {
        setConnectionStatus("connected");
        toast.success(`Connection simulated for ${selectedAccounts.length} account(s)`, {
          description: `Server: ${response.data.server_ip || serverSettings.server_ip} (Simulation Mode)`
        });
      } else {
        setConnectionStatus("connected");
        toast.success(`Connected ${selectedAccounts.length} account(s) to ${serverSettings.server_ip}`);
      }
    } catch (error) {
      console.error("Error connecting to server:", error);
      setConnectionStatus("disconnected");
      
      if (error.response?.status === 400 && error.response?.data?.detail?.includes("Server IP")) {
        toast.error("Server IP not configured", {
          description: "Please enter a valid server IP address"
        });
      } else {
        toast.error("Failed to connect to server");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    setConnectionStatus("connecting");

    try {
      const response = await axios.post(`${API}/server/disconnect`);
      setConnectionStatus("disconnected");
      
      if (response.data.simulation) {
        toast.success("Disconnection simulated", {
          description: "Note: This was a simulation disconnection"
        });
      } else {
        toast.success("Disconnected from server");
      }
    } catch (error) {
      console.error("Error disconnecting from server:", error);
      toast.error("Failed to disconnect from server");
    } finally {
      setLoading(false);
    }
  };

  const handleAccountToggle = (accountId, checked) => {
    if (checked) {
      setSelectedAccounts([...selectedAccounts, accountId]);
    } else {
      setSelectedAccounts(selectedAccounts.filter(id => id !== accountId));
    }
  };

  const handleSelectAll = (checked) => {
    if (checked) {
      const availableAccounts = serverSettings.offline_accounts_enabled 
        ? accounts 
        : accounts.filter(acc => acc.account_type === "microsoft");
      setSelectedAccounts(availableAccounts.map(acc => acc.id));
    } else {
      setSelectedAccounts([]);
    }
  };

  const addLoginMessage = () => {
    if (!newLoginMessage.message.trim()) {
      toast.error("Please enter a message");
      return;
    }

    const updatedMessages = [...serverSettings.login_messages, newLoginMessage];
    updateServerSettings({ login_messages: updatedMessages });
    setNewLoginMessage({ message: "", delay: 2 });
  };

  const removeLoginMessage = (index) => {
    const updatedMessages = serverSettings.login_messages.filter((_, i) => i !== index);
    updateServerSettings({ login_messages: updatedMessages });
  };

  const addWorldMessage = () => {
    if (!newWorldMessage.message.trim()) {
      toast.error("Please enter a message");
      return;
    }

    const updatedMessages = [...serverSettings.world_change_messages, newWorldMessage];
    updateServerSettings({ world_change_messages: updatedMessages });
    setNewWorldMessage({ message: "", delay: 2 });
  };

  const removeWorldMessage = (index) => {
    const updatedMessages = serverSettings.world_change_messages.filter((_, i) => i !== index);
    updateServerSettings({ world_change_messages: updatedMessages });
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "text-green-400";
      case "connecting":
        return "text-yellow-400";
      default:
        return "text-red-400";
    }
  };

  const getConnectionStatusIcon = () => {
    switch (connectionStatus) {
      case "connected":
        return <Wifi className="w-4 h-4" />;
      case "connecting":
        return <RotateCcw className="w-4 h-4 animate-spin" />;
      default:
        return <WifiOff className="w-4 h-4" />;
    }
  };

  const getAccountDisplayName = (account) => {
    return account.account_type === "microsoft" ? account.email : account.nickname;
  };

  const availableAccounts = serverSettings.offline_accounts_enabled 
    ? accounts 
    : accounts.filter(acc => acc.account_type === "microsoft");

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Server Connection</h1>
          <p className="text-gray-400 mt-1">
            Configure and manage your Minecraft server connection
          </p>
        </div>
        
        <div className={`connection-indicator ${connectionStatus}`}>
          {getConnectionStatusIcon()}
          <span className="capitalize">{connectionStatus}</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Server Information */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Globe className="w-5 h-5" />
                Server Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="server_ip" className="text-gray-300">Server IP Address</Label>
                  <Input
                    id="server_ip"
                    value={serverSettings.server_ip}
                    onChange={(e) => setServerSettings({ ...serverSettings, server_ip: e.target.value })}
                    onBlur={(e) => updateServerSettings({ server_ip: e.target.value })}
                    className="bg-gray-700 border-gray-600 text-white"
                    placeholder="play.example.com:25565"
                    data-testid="server-ip-input"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="login_delay" className="text-gray-300">Login Delay (seconds)</Label>
                  <Input
                    id="login_delay"
                    type="number"
                    value={serverSettings.login_delay}
                    onChange={(e) => setServerSettings({ ...serverSettings, login_delay: parseInt(e.target.value) || 5 })}
                    onBlur={(e) => updateServerSettings({ login_delay: parseInt(e.target.value) || 5 })}
                    className="bg-gray-700 border-gray-600 text-white"
                    min="1"
                    data-testid="login-delay-input"
                  />
                </div>
              </div>

              <div className="flex gap-4">
                <Button
                  onClick={handleConnect}
                  disabled={loading || connectionStatus === "connected" || selectedAccounts.length === 0}
                  className="btn-minecraft"
                  data-testid="connect-button"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Connect ({selectedAccounts.length})
                </Button>
                
                <Button
                  onClick={handleDisconnect}
                  disabled={loading || connectionStatus === "disconnected"}
                  className="btn-danger"
                  data-testid="disconnect-button"
                >
                  <Square className="w-4 h-4 mr-2" />
                  Disconnect
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Settings */}
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Settings className="w-5 h-5" />
                Bot Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Basic Settings */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Shield className="w-5 h-5 text-gray-400" />
                    <div>
                      <Label className="text-gray-300">Offline/Cracked Accounts</Label>
                      <p className="text-gray-500 text-sm">Enable cracked accounts for connection</p>
                    </div>
                  </div>
                  <Switch
                    checked={serverSettings.offline_accounts_enabled}
                    onCheckedChange={(checked) => updateServerSettings({ offline_accounts_enabled: checked })}
                    data-testid="offline-accounts-switch"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Zap className="w-5 h-5 text-gray-400" />
                    <div>
                      <Label className="text-gray-300">Anti-AFK</Label>
                      <p className="text-gray-500 text-sm">Jump every 60 seconds to prevent AFK kick</p>
                    </div>
                  </div>
                  <Switch
                    checked={serverSettings.anti_afk_enabled}
                    onCheckedChange={(checked) => updateServerSettings({ anti_afk_enabled: checked })}
                    data-testid="anti-afk-switch"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <RotateCcw className="w-5 h-5 text-gray-400" />
                    <div>
                      <Label className="text-gray-300">Auto Reconnect</Label>
                      <p className="text-gray-500 text-sm">Automatically reconnect when disconnected</p>
                    </div>
                  </div>
                  <Switch
                    checked={serverSettings.auto_connect_enabled}
                    onCheckedChange={(checked) => updateServerSettings({ auto_connect_enabled: checked })}
                    data-testid="auto-connect-switch"
                  />
                </div>
              </div>

              <Separator className="bg-gray-600" />

              {/* Message Settings */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <MessageCircle className="w-5 h-5 text-gray-400" />
                    <div>
                      <Label className="text-gray-300">Login Messages</Label>
                      <p className="text-gray-500 text-sm">Send messages after connecting to server</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={serverSettings.login_message_enabled}
                      onCheckedChange={(checked) => updateServerSettings({ login_message_enabled: checked })}
                      data-testid="login-messages-switch"
                    />
                    <Dialog open={showLoginMessagesDialog} onOpenChange={setShowLoginMessagesDialog}>
                      <DialogTrigger asChild>
                        <Button variant="ghost" size="sm" data-testid="login-messages-settings">
                          <Settings className="w-4 h-4" />
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="bg-gray-800 border-gray-700 text-white">
                        <DialogHeader>
                          <DialogTitle>Login Messages Configuration</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                          <div className="grid grid-cols-3 gap-2">
                            <Input
                              placeholder="Message"
                              value={newLoginMessage.message}
                              onChange={(e) => setNewLoginMessage({ ...newLoginMessage, message: e.target.value })}
                              className="col-span-2 bg-gray-700 border-gray-600 text-white"
                            />
                            <Input
                              type="number"
                              placeholder="Delay"
                              value={newLoginMessage.delay}
                              onChange={(e) => setNewLoginMessage({ ...newLoginMessage, delay: parseInt(e.target.value) || 2 })}
                              className="bg-gray-700 border-gray-600 text-white"
                              min="1"
                            />
                            <Button onClick={addLoginMessage} className="col-span-3 btn-minecraft">
                              Add Message
                            </Button>
                          </div>
                          <div className="space-y-2 max-h-48 overflow-y-auto">
                            {serverSettings.login_messages.map((msg, index) => (
                              <div key={index} className="flex items-center justify-between p-2 bg-gray-700 rounded">
                                <div>
                                  <span className="text-white">{msg.message}</span>
                                  <span className="text-gray-400 text-sm ml-2">({msg.delay}s)</span>
                                </div>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => removeLoginMessage(index)}
                                  className="text-red-400 hover:bg-red-600/20"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Globe className="w-5 h-5 text-gray-400" />
                    <div>
                      <Label className="text-gray-300">World Change Messages</Label>
                      <p className="text-gray-500 text-sm">Send messages when world/lobby changes</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={serverSettings.world_change_messages_enabled}
                      onCheckedChange={(checked) => updateServerSettings({ world_change_messages_enabled: checked })}
                      data-testid="world-messages-switch"
                    />
                    <Dialog open={showWorldMessagesDialog} onOpenChange={setShowWorldMessagesDialog}>
                      <DialogTrigger asChild>
                        <Button variant="ghost" size="sm" data-testid="world-messages-settings">
                          <Settings className="w-4 h-4" />
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="bg-gray-800 border-gray-700 text-white">
                        <DialogHeader>
                          <DialogTitle>World Change Messages Configuration</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                          <div className="grid grid-cols-3 gap-2">
                            <Input
                              placeholder="Message"
                              value={newWorldMessage.message}
                              onChange={(e) => setNewWorldMessage({ ...newWorldMessage, message: e.target.value })}
                              className="col-span-2 bg-gray-700 border-gray-600 text-white"
                            />
                            <Input
                              type="number"
                              placeholder="Delay"
                              value={newWorldMessage.delay}
                              onChange={(e) => setNewWorldMessage({ ...newWorldMessage, delay: parseInt(e.target.value) || 2 })}
                              className="bg-gray-700 border-gray-600 text-white"
                              min="1"
                            />
                            <Button onClick={addWorldMessage} className="col-span-3 btn-minecraft">
                              Add Message
                            </Button>
                          </div>
                          <div className="space-y-2 max-h-48 overflow-y-auto">
                            {serverSettings.world_change_messages.map((msg, index) => (
                              <div key={index} className="flex items-center justify-between p-2 bg-gray-700 rounded">
                                <div>
                                  <span className="text-white">{msg.message}</span>
                                  <span className="text-gray-400 text-sm ml-2">({msg.delay}s)</span>
                                </div>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => removeWorldMessage(index)}
                                  className="text-red-400 hover:bg-red-600/20"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Account Selection */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                Accounts
              </div>
              <Badge variant="outline" className="text-green-400 border-green-400">
                {selectedAccounts.length}/{availableAccounts.length}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {availableAccounts.length > 0 ? (
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="select-all"
                    checked={selectedAccounts.length === availableAccounts.length}
                    onCheckedChange={handleSelectAll}
                    data-testid="select-all-accounts-checkbox"
                  />
                  <Label htmlFor="select-all" className="text-gray-300 font-medium">
                    Select All
                  </Label>
                </div>
                
                <Separator className="bg-gray-600" />
                
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {availableAccounts.map((account) => (
                    <div 
                      key={account.id} 
                      className="flex items-center justify-between p-3 bg-gray-700 rounded-lg border border-gray-600"
                      data-testid={`connect-account-item-${account.id}`}
                    >
                      <div className="flex items-center space-x-2 flex-1">
                        <Checkbox
                          id={`connect-account-${account.id}`}
                          checked={selectedAccounts.includes(account.id)}
                          onCheckedChange={(checked) => handleAccountToggle(account.id, checked)}
                        />
                        <div className="flex-1">
                          <Label 
                            htmlFor={`connect-account-${account.id}`} 
                            className="text-gray-300 text-sm cursor-pointer"
                          >
                            {getAccountDisplayName(account)}
                          </Label>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge 
                              variant={account.account_type === "microsoft" ? "default" : "secondary"}
                              className="text-xs"
                            >
                              {account.account_type}
                            </Badge>
                            <div className={`w-2 h-2 rounded-full ${account.is_online ? 'bg-green-400' : 'bg-red-400'}`}></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-400">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No accounts available</p>
                <p className="text-xs mt-1">
                  {!serverSettings.offline_accounts_enabled 
                    ? "Enable offline accounts or add Microsoft accounts" 
                    : "Add accounts from the Accounts page"
                  }
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ConnectPage;