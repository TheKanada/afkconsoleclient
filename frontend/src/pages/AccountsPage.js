import React, { useState, useEffect, useContext } from "react";
import { AuthContext } from "../App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus, Mail, User, Trash2, Circle, Edit } from "lucide-react";
import axios from "axios";

const AccountsPage = () => {
  const { API } = useContext(AuthContext);
  const [accounts, setAccounts] = useState([]);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newAccount, setNewAccount] = useState({
    account_type: "",
    email: "",
    nickname: ""
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAccounts();
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

  const handleAddAccount = async (e) => {
    e.preventDefault();
    
    if (newAccount.account_type === "microsoft" && !newAccount.email) {
      toast.error("Email is required for Microsoft accounts");
      return;
    }
    
    if (newAccount.account_type === "cracked" && !newAccount.nickname) {
      toast.error("Nickname is required for cracked accounts");
      return;
    }

    setLoading(true);

    try {
      await axios.post(`${API}/accounts`, {
        account_type: newAccount.account_type,
        email: newAccount.account_type === "microsoft" ? newAccount.email : null,
        nickname: newAccount.account_type === "cracked" ? newAccount.nickname : null
      });
      
      toast.success("Account added successfully");
      setNewAccount({ account_type: "", email: "", nickname: "" });
      setShowAddDialog(false);
      fetchAccounts();
    } catch (error) {
      console.error("Error adding account:", error);
      toast.error(error.response?.data?.detail || "Failed to add account");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async (accountId) => {
    if (!window.confirm("Are you sure you want to delete this account?")) {
      return;
    }

    try {
      await axios.delete(`${API}/accounts/${accountId}`);
      toast.success("Account deleted successfully");
      fetchAccounts();
    } catch (error) {
      console.error("Error deleting account:", error);
      toast.error("Failed to delete account");
    }
  };

  const handleConnectAccount = async (accountId) => {
    try {
      const response = await axios.post(`${API}/accounts/${accountId}/connect`);
      toast.success("Account connected to Minecraft server successfully!");
      fetchAccounts();
    } catch (error) {
      console.error("Error connecting account:", error);
      if (error.response?.status === 400 && error.response?.data?.detail?.includes("Server IP")) {
        toast.error("Server not configured", {
          description: "Please configure server IP in Connect page first"
        });
      } else if (error.response?.status === 500) {
        toast.error("Connection failed", {
          description: "Check server IP and account credentials. Ensure the Minecraft server is running."
        });
      } else {
        toast.error(error.response?.data?.detail || "Failed to connect account");
      }
    }
  };

  const handleDisconnectAccount = async (accountId) => {
    try {
      const response = await axios.post(`${API}/accounts/${accountId}/disconnect`);
      toast.success("Account disconnected from Minecraft server successfully!");
      fetchAccounts();
    } catch (error) {
      console.error("Error disconnecting account:", error);
      toast.error(error.response?.data?.detail || "Failed to disconnect account");
    }
  };

  const handleClearInventory = async (accountId) => {
    if (!window.confirm("Are you sure you want to clear this account's inventory?")) {
      return;
    }

    try {
      await axios.post(`${API}/accounts/${accountId}/clear-inventory`);
      toast.success("Inventory cleared successfully");
    } catch (error) {
      console.error("Error clearing inventory:", error);
      toast.error(error.response?.data?.detail || "Failed to clear inventory");
    }
  };

  const getAccountIcon = (accountType) => {
    return accountType === "microsoft" ? (
      <Mail className="w-4 h-4" />
    ) : (
      <User className="w-4 h-4" />
    );
  };

  const getAccountBadgeVariant = (accountType) => {
    return accountType === "microsoft" ? "default" : "secondary";
  };

  const getStatusColor = (isOnline) => {
    return isOnline ? "text-green-400" : "text-red-400";
  };

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Minecraft Accounts</h1>
          <p className="text-gray-400 mt-1">
            Manage your Minecraft accounts for AFK sessions
          </p>
        </div>
        
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button className="btn-minecraft" data-testid="add-account-button">
              <Plus className="w-4 h-4 mr-2" />
              Add Account
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-gray-800 border-gray-700 text-white">
            <DialogHeader>
              <DialogTitle>Add New Minecraft Account</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleAddAccount} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="account_type" className="text-gray-300">Account Type</Label>
                <Select 
                  value={newAccount.account_type} 
                  onValueChange={(value) => setNewAccount({ ...newAccount, account_type: value, email: "", nickname: "" })}
                  required
                >
                  <SelectTrigger className="bg-gray-700 border-gray-600 text-white" data-testid="account-type-select">
                    <SelectValue placeholder="Select account type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="microsoft">Microsoft Account</SelectItem>
                    <SelectItem value="cracked">Cracked Account</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {newAccount.account_type === "microsoft" && (
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-gray-300">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    value={newAccount.email}
                    onChange={(e) => setNewAccount({ ...newAccount, email: e.target.value })}
                    className="bg-gray-700 border-gray-600 text-white"
                    placeholder="Enter Microsoft account email"
                    required
                    data-testid="microsoft-email-input"
                  />
                </div>
              )}

              {newAccount.account_type === "cracked" && (
                <div className="space-y-2">
                  <Label htmlFor="nickname" className="text-gray-300">Nickname</Label>
                  <Input
                    id="nickname"
                    type="text"
                    value={newAccount.nickname}
                    onChange={(e) => setNewAccount({ ...newAccount, nickname: e.target.value })}
                    className="bg-gray-700 border-gray-600 text-white"
                    placeholder="Enter nickname"
                    required
                    data-testid="cracked-nickname-input"
                  />
                </div>
              )}

              <div className="flex gap-2 pt-4">
                <Button type="submit" disabled={loading} className="btn-minecraft" data-testid="add-account-submit-button">
                  {loading ? "Adding..." : "Add Account"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowAddDialog(false)}
                  className="border-gray-500 text-gray-300"
                >
                  Cancel
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Accounts List */}
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center justify-between">
            <span>Your Accounts</span>
            <Badge variant="outline" className="text-green-400 border-green-400">
              {accounts.length} Account{accounts.length !== 1 ? 's' : ''}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {accounts.length > 0 ? (
            <div className="grid gap-4">
              {accounts.map((account) => (
                <div key={account.id} className="p-4 bg-gray-700 rounded-lg border border-gray-600" data-testid={`account-item-${account.id}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        {getAccountIcon(account.account_type)}
                        <Badge variant={getAccountBadgeVariant(account.account_type)} className="text-xs">
                          {account.account_type}
                        </Badge>
                      </div>
                      
                      <div>
                        <p className="text-white font-medium">
                          {account.account_type === "microsoft" ? account.email : account.nickname}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <Circle className={`w-2 h-2 fill-current ${getStatusColor(account.is_online)}`} />
                          <span className={`text-sm ${getStatusColor(account.is_online)}`}>
                            {account.is_online ? "Online" : "Offline"}
                          </span>
                          {account.last_seen && (
                            <span className="text-gray-400 text-sm">
                              • Last seen: {new Date(account.last_seen).toLocaleString()}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {account.is_online ? (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleClearInventory(account.id)}
                            className="border-yellow-600 text-yellow-400 hover:bg-yellow-600 hover:text-white"
                            data-testid={`clear-inventory-${account.id}`}
                          >
                            Clear Inventory
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDisconnectAccount(account.id)}
                            className="border-red-600 text-red-400 hover:bg-red-600 hover:text-white"
                            data-testid={`disconnect-account-${account.id}`}
                          >
                            Disconnect
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleConnectAccount(account.id)}
                          className="border-green-600 text-green-400 hover:bg-green-600 hover:text-white"
                          data-testid={`connect-account-${account.id}`}
                        >
                          Connect
                        </Button>
                      )}
                      
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteAccount(account.id)}
                        className="border-red-600 text-red-400 hover:bg-red-600 hover:text-white"
                        data-testid={`delete-account-${account.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <User className="w-12 h-12 mx-auto text-gray-500 mb-4" />
              <p className="text-gray-400 text-lg">No accounts added yet</p>
              <p className="text-gray-500 text-sm mt-1">
                Add your first Minecraft account to get started
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Account Information */}
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Account Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-2">Microsoft Accounts</h4>
              <p className="text-gray-300 text-sm">
                Microsoft accounts require proper authentication and support premium features.
                These accounts can connect to most servers.
              </p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-2">Cracked Accounts</h4>
              <p className="text-gray-300 text-sm">
                Cracked accounts use only a nickname and work with offline-mode servers.
                These accounts may have limited server compatibility.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AccountsPage;