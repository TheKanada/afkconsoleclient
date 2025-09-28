import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone
import json
import uuid
from minecraft import authentication
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection
from minecraft.networking.packets import Packet, clientbound, serverbound
import threading
import time

logger = logging.getLogger(__name__)

class MinecraftBot:
    def __init__(self, account_info: dict, server_settings: dict, db_manager):
        self.account_info = account_info
        self.server_settings = server_settings  
        self.db_manager = db_manager
        self.connection = None
        self.is_connected = False
        self.is_running = False
        self.anti_afk_enabled = False
        self.last_message_time = datetime.now()
        self.thread = None
        
    async def connect(self) -> bool:
        """Connect to Minecraft server"""
        try:
            server_ip = self.server_settings.get('server_ip', '').split(':')
            host = server_ip[0] if server_ip else 'localhost'
            port = int(server_ip[1]) if len(server_ip) > 1 else 25565
            
            logger.info(f"Connecting {self.account_info.get('nickname', self.account_info.get('email'))} to {host}:{port}")
            
            # Handle different account types
            if self.account_info.get('account_type') == 'microsoft':
                # For Microsoft accounts - would need proper OAuth flow
                # For now, we'll use offline mode with the email as username
                username = self.account_info.get('email', '').split('@')[0]
                auth_token = None
            else:
                # Cracked/offline account
                username = self.account_info.get('nickname', 'Player')
                auth_token = None
            
            # Create connection
            self.connection = Connection(
                address=host,
                port=port,
                username=username,
                auth_token=auth_token
            )
            
            # Start connection in separate thread
            self.is_running = True
            self.thread = threading.Thread(target=self._connection_loop)
            self.thread.daemon = True
            self.thread.start()
            
            # Wait a bit to see if connection is successful
            await asyncio.sleep(2)
            
            if self.is_connected:
                logger.info(f"Successfully connected {username} to {host}:{port}")
                return True
            else:
                logger.error(f"Failed to connect {username} to {host}:{port}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Minecraft server: {e}")
            return False
    
    def _connection_loop(self):
        """Main connection loop running in separate thread"""
        try:
            # Connect to server
            self.connection.connect()
            self.is_connected = True
            
            logger.info(f"Bot {self.account_info.get('nickname', self.account_info.get('email'))} connected successfully")
            
            # Start anti-AFK if enabled
            if self.server_settings.get('anti_afk_enabled'):
                self.anti_afk_enabled = True
                threading.Thread(target=self._anti_afk_loop, daemon=True).start()
            
            # Send login messages if configured
            if self.server_settings.get('login_message_enabled'):
                self._send_login_messages()
            
            # Keep connection alive
            while self.is_running and self.is_connected:
                try:
                    time.sleep(1)  # Keep bot alive
                except Exception as e:
                    logger.error(f"Error in connection loop: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Connection loop error: {e}")
            self.is_connected = False
        finally:
            self._cleanup()
    
    def _handle_join_game(self, join_game_packet):
        """Handle successful join to game"""
        logger.info(f"Bot {self.account_info.get('nickname', self.account_info.get('email'))} joined the game")
        self.is_connected = True
        
        # Update database
        asyncio.create_task(self._update_connection_status(True))
    
    def _handle_chat_message(self, chat_packet):
        """Handle incoming chat messages"""
        try:
            message = chat_packet.json_data
            if isinstance(message, str):
                message_text = message
            else:
                message_text = json.loads(message).get('text', str(message))
            
            logger.info(f"Chat message received: {message_text}")
            
            # Save to database
            asyncio.create_task(self._save_chat_message(message_text, False))
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    def _handle_disconnect(self, disconnect_packet):
        """Handle disconnection from server"""
        logger.info(f"Bot {self.account_info.get('nickname', self.account_info.get('email'))} was disconnected")
        self.is_connected = False
        
        # Update database
        asyncio.create_task(self._update_connection_status(False))
        
        # Auto-reconnect if enabled
        if self.server_settings.get('auto_connect_enabled') and self.is_running:
            threading.Thread(target=self._auto_reconnect, daemon=True).start()
    
    def _anti_afk_loop(self):
        """Anti-AFK loop - jump every 60 seconds"""
        while self.anti_afk_enabled and self.is_connected and self.is_running:
            try:
                time.sleep(60)  # Wait 60 seconds
                if self.is_connected:
                    self.send_command('/jump')  # Send jump command
                    logger.debug(f"Anti-AFK jump sent for {self.account_info.get('nickname')}")
            except Exception as e:
                logger.error(f"Anti-AFK error: {e}")
    
    def _send_login_messages(self):
        """Send configured login messages"""
        try:
            login_messages = self.server_settings.get('login_messages', [])
            for i, msg_config in enumerate(login_messages):
                if i > 0:  # Add delay between messages
                    time.sleep(msg_config.get('delay', 2))
                
                message = msg_config.get('message', '')
                if message:
                    self.send_chat_message(message)
                    
        except Exception as e:
            logger.error(f"Error sending login messages: {e}")
    
    def _auto_reconnect(self):
        """Auto-reconnect logic"""
        for attempt in range(3):
            logger.info(f"Auto-reconnect attempt {attempt + 1}/3")
            time.sleep(300)  # Wait 5 minutes
            
            if asyncio.run(self.connect()):
                return
        
        # If all attempts failed, wait 1 hour and try once more
        logger.info("All reconnect attempts failed, waiting 1 hour...")
        time.sleep(3600)
        asyncio.run(self.connect())
    
    async def _update_connection_status(self, is_online: bool):
        """Update account connection status in database"""
        try:
            if self.db_manager and self.db_manager.db is not None:
                await self.db_manager.db.minecraft_accounts.update_one(
                    {"id": self.account_info.get('id')},
                    {
                        "$set": {
                            "is_online": is_online,
                            "last_seen": datetime.now(timezone.utc),
                            "connection_status": "connected" if is_online else "disconnected"
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Error updating connection status: {e}")
    
    async def _save_chat_message(self, message: str, is_outgoing: bool):
        """Save chat message to database"""
        try:
            if self.db_manager and self.db_manager.db is not None:
                chat_message = {
                    "id": str(uuid.uuid4()),
                    "account_id": self.account_info.get('id'),
                    "message": message,
                    "timestamp": datetime.now(timezone.utc),
                    "is_outgoing": is_outgoing
                }
                await self.db_manager.db.chat_messages.insert_one(chat_message)
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
    
    def send_chat_message(self, message: str) -> bool:
        """Send chat message to server"""
        try:
            if self.is_connected and self.connection:
                chat_packet = serverbound.play.ChatPacket()
                chat_packet.message = message
                self.connection.write_packet(chat_packet)
                
                # Save outgoing message
                asyncio.create_task(self._save_chat_message(message, True))
                
                logger.info(f"Message sent from {self.account_info.get('nickname')}: {message}")
                return True
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
            return False
        
        return False
    
    def send_command(self, command: str) -> bool:
        """Send command to server"""
        if not command.startswith('/'):
            command = '/' + command
        
        return self.send_chat_message(command)
    
    async def clear_inventory(self) -> bool:
        """Clear player inventory"""
        try:
            # Send inventory clearing commands
            commands = [
                '/clear @s',  # Clear inventory
                '/effect clear @s',  # Clear effects
            ]
            
            for cmd in commands:
                self.send_command(cmd)
                await asyncio.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"Error clearing inventory: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from server"""
        try:
            self.is_running = False
            self.anti_afk_enabled = False
            
            if self.connection and self.is_connected:
                self.connection.disconnect()
            
            self.is_connected = False
            await self._update_connection_status(False)
            
            logger.info(f"Bot {self.account_info.get('nickname', self.account_info.get('email'))} disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    def _cleanup(self):
        """Clean up resources"""
        self.is_connected = False
        self.is_running = False
        self.anti_afk_enabled = False


class MinecraftManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.active_bots: Dict[str, MinecraftBot] = {}
        
    async def connect_account(self, account_info: dict, server_settings: dict) -> bool:
        """Connect a Minecraft account to server"""
        account_id = account_info.get('id')
        
        # Disconnect if already connected
        if account_id in self.active_bots:
            await self.disconnect_account(account_id)
        
        # Create and connect bot
        bot = MinecraftBot(account_info, server_settings, self.db_manager)
        success = await bot.connect()
        
        if success:
            self.active_bots[account_id] = bot
            return True
        else:
            await bot.disconnect()
            return False
    
    async def disconnect_account(self, account_id: str) -> bool:
        """Disconnect a Minecraft account"""
        if account_id in self.active_bots:
            bot = self.active_bots[account_id]
            await bot.disconnect()
            del self.active_bots[account_id]
            return True
        return False
    
    async def send_message_from_accounts(self, account_ids: List[str], message: str) -> bool:
        """Send message from multiple accounts"""
        success_count = 0
        
        for account_id in account_ids:
            if account_id in self.active_bots:
                bot = self.active_bots[account_id]
                if bot.send_chat_message(message):
                    success_count += 1
        
        return success_count > 0
    
    async def clear_account_inventory(self, account_id: str) -> bool:
        """Clear inventory for a specific account"""
        if account_id in self.active_bots:
            bot = self.active_bots[account_id]
            return await bot.clear_inventory()
        return False
    
    def get_connected_accounts(self) -> List[str]:
        """Get list of connected account IDs"""
        return [aid for aid, bot in self.active_bots.items() if bot.is_connected]
    
    def is_account_connected(self, account_id: str) -> bool:
        """Check if account is connected"""
        return account_id in self.active_bots and self.active_bots[account_id].is_connected
    
    async def disconnect_all(self):
        """Disconnect all accounts"""
        for account_id in list(self.active_bots.keys()):
            await self.disconnect_account(account_id)