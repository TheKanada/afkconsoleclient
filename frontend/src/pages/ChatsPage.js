import React, { useState, useEffect, useContext } from "react";
import { AuthContext } from "../App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { Send, MessageSquare, Timer, Play, Pause, Users } from "lucide-react";
import axios from "axios";

const ChatsPage = () => {
  const { API } = useContext(AuthContext);
  const [accounts, setAccounts] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [selectedAccounts, setSelectedAccounts] = useState([]);
  const [message, setMessage] = useState("");
  const [spamMessage, setSpamMessage] = useState("");
  const [spamInterval, setSpamInterval] = useState(60);
  const [isSpamActive, setIsSpamActive] = useState(false);
  const [spamTimer, setSpamTimer] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    
    if (isMounted) {
      fetchAccounts();
      fetchChatMessages();
    }
    
    // Refresh chat messages every 5 seconds
    const interval = setInterval(() => {
      if (isMounted) {
        fetchChatMessages();
      }
    }, 5000);
    
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    return () => {
      if (spamTimer) {
        clearInterval(spamTimer);
      }
    };
  }, [spamTimer]);

  const fetchAccounts = async () => {
    try {
      const response = await axios.get(`${API}/accounts`);
      // Filter only online accounts for messaging
      const onlineAccounts = response.data.filter(acc => acc.is_online);
      setAccounts(response.data);
    } catch (error) {
      console.error("Error fetching accounts:", error);
      toast.error("Failed to fetch accounts");
    }
  };

  const fetchChatMessages = async () => {
    try {
      const response = await axios.get(`${API}/chats`);
      setChatMessages(response.data);
    } catch (error) {
      console.error("Error fetching chat messages:", error);
    }
  };

  const handleAccountSelection = (accountId, checked) => {
    if (checked) {
      setSelectedAccounts([...selectedAccounts, accountId]);
    } else {
      setSelectedAccounts(selectedAccounts.filter(id => id !== accountId));
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!message.trim()) {
      toast.error("Please enter a message");
      return;
    }
    
    if (selectedAccounts.length === 0) {
      toast.error("Please select at least one account");
      return;
    }

    setLoading(true);

    try {
      await axios.post(`${API}/chats/send`, {
        account_ids: selectedAccounts,
        message: message.trim()
      });
      
      toast.success(`Message sent from ${selectedAccounts.length} account(s)`);
      setMessage("");
      fetchChatMessages();
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error(error.response?.data?.detail || "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  const handleStartSpam = () => {
    if (!spamMessage.trim()) {
      toast.error("Please enter a spam message");
      return;
    }
    
    if (selectedAccounts.length === 0) {
      toast.error("Please select at least one account");
      return;
    }
    
    if (spamInterval < 1) {
      toast.error("Interval must be at least 1 second");
      return;
    }

    const timer = setInterval(async () => {
      try {
        await axios.post(`${API}/chats/send`, {
          account_ids: selectedAccounts,
          message: spamMessage.trim()
        });
        fetchChatMessages();
      } catch (error) {
        console.error("Error sending spam message:", error);
        toast.error("Failed to send spam message");
        handleStopSpam();
      }
    }, spamInterval * 1000);

    setSpamTimer(timer);
    setIsSpamActive(true);
    toast.success(`Spam started: every ${spamInterval} seconds`);
  };

  const handleStopSpam = () => {
    if (spamTimer) {
      clearInterval(spamTimer);
      setSpamTimer(null);
    }
    setIsSpamActive(false);
    toast.success("Spam stopped");
  };

  const getAccountDisplayName = (account) => {
    return account.account_type === "microsoft" ? account.email : account.nickname;
  };

  const onlineAccounts = accounts.filter(acc => acc.is_online);
  const dedupedMessages = chatMessages.reduce((acc, msg) => {
    // Simple deduplication based on message content and timestamp (within 1 second)
    const existing = acc.find(m => 
      m.message === msg.message && 
      Math.abs(new Date(m.timestamp) - new Date(msg.timestamp)) < 1000
    );
    
    if (!existing && !msg.is_outgoing) {
      acc.push(msg);
    } else if (msg.is_outgoing) {
      acc.push(msg);
    }
    
    return acc;
  }, []);

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Chat Messages</h1>
          <p className="text-gray-400 mt-1">
            Monitor and send messages through your Minecraft accounts
          </p>
        </div>
        <Badge variant="outline" className="text-green-400 border-green-400">
          {onlineAccounts.length} Online Account{onlineAccounts.length !== 1 ? 's' : ''}
        </Badge>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Chat Display */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Live Chat Feed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="terminal h-96 overflow-y-auto" data-testid="chat-messages-container">
              <div className="space-y-2">
                {dedupedMessages.length > 0 ? (
                  dedupedMessages
                    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                    .slice(0, 50)
                    .reverse()
                    .map((msg) => {
                      const account = accounts.find(acc => acc.id === msg.account_id);
                      const accountName = account ? getAccountDisplayName(account) : 'Unknown';
                      
                      return (
                        <div 
                          key={msg.id} 
                          className={`chat-message ${msg.is_outgoing ? 'outgoing' : 'incoming'}`}
                          data-testid={`chat-message-${msg.id}`}
                        >
                          <div className="flex items-start gap-2">
                            <span className={`text-xs ${msg.is_outgoing ? 'text-yellow-400' : 'text-green-400'}`}>
                              [{new Date(msg.timestamp).toLocaleTimeString()}]
                            </span>
                            <span className="text-gray-300 text-xs">
                              {accountName}:
                            </span>
                            <span className="text-white text-sm flex-1">
                              {msg.message}
                            </span>
                          </div>
                        </div>
                      );
                    })
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No messages yet</p>
                    <p className="text-sm">Messages will appear here when accounts are active</p>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Messaging Controls */}
        <div className="space-y-6">
          {/* Account Selection */}
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Users className="w-5 h-5" />
                Select Accounts
              </CardTitle>
            </CardHeader>
            <CardContent>
              {onlineAccounts.length > 0 ? (
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {onlineAccounts.map((account) => (
                    <div key={account.id} className="flex items-center space-x-2" data-testid={`account-checkbox-${account.id}`}>
                      <Checkbox
                        id={`account-${account.id}`}
                        checked={selectedAccounts.includes(account.id)}
                        onCheckedChange={(checked) => handleAccountSelection(account.id, checked)}
                      />
                      <Label htmlFor={`account-${account.id}`} className="text-gray-300 text-sm flex-1">
                        {getAccountDisplayName(account)}
                      </Label>
                      <Badge variant="outline" className="text-green-400 border-green-400 text-xs">
                        {account.account_type}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-gray-400">
                  <p className="text-sm">No online accounts available</p>
                  <p className="text-xs mt-1">Connect accounts from the Connect page first</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Send Message */}
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white">Send Message</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSendMessage} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="message" className="text-gray-300">Message</Label>
                  <Textarea
                    id="message"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="bg-gray-700 border-gray-600 text-white"
                    placeholder="Enter your message..."
                    rows={3}
                    data-testid="message-input"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={loading || selectedAccounts.length === 0 || !message.trim()}
                  className="w-full btn-minecraft"
                  data-testid="send-message-button"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {loading ? "Sending..." : `Send from ${selectedAccounts.length} account(s)`}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Spam Messages */}
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Timer className="w-5 h-5" />
                Spam Messages
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="spamMessage" className="text-gray-300">Spam Message</Label>
                  <Textarea
                    id="spamMessage"
                    value={spamMessage}
                    onChange={(e) => setSpamMessage(e.target.value)}
                    className="bg-gray-700 border-gray-600 text-white"
                    placeholder="Enter message to spam..."
                    rows={2}
                    disabled={isSpamActive}
                    data-testid="spam-message-input"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="spamInterval" className="text-gray-300">Interval (seconds)</Label>
                  <Input
                    id="spamInterval"
                    type="number"
                    value={spamInterval}
                    onChange={(e) => setSpamInterval(parseInt(e.target.value) || 60)}
                    className="bg-gray-700 border-gray-600 text-white"
                    min="1"
                    disabled={isSpamActive}
                    data-testid="spam-interval-input"
                  />
                </div>

                <div className="flex gap-2">
                  {!isSpamActive ? (
                    <Button
                      onClick={handleStartSpam}
                      disabled={selectedAccounts.length === 0 || !spamMessage.trim()}
                      className="flex-1 btn-minecraft"
                      data-testid="start-spam-button"
                    >
                      <Play className="w-4 h-4 mr-2" />
                      Start Spam
                    </Button>
                  ) : (
                    <Button
                      onClick={handleStopSpam}
                      className="flex-1 btn-danger"
                      data-testid="stop-spam-button"
                    >
                      <Pause className="w-4 h-4 mr-2" />
                      Stop Spam
                    </Button>
                  )}
                </div>

                {isSpamActive && (
                  <div className="p-3 bg-yellow-500/20 border border-yellow-500/30 rounded-lg">
                    <div className="flex items-center gap-2 text-yellow-400">
                      <Timer className="w-4 h-4" />
                      <span className="text-sm font-medium">
                        Spam active: sending every {spamInterval} seconds
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default ChatsPage;