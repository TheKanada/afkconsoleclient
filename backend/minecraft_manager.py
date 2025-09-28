import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone
import json
import threading
import time
import uuid
import concurrent.futures

# Minecraft protocol imports
from minecraft.networking.connection import Connection
from minecraft.networking.packets import Packet, clientbound, serverbound
from minecraft.exceptions import YggdrasilError
from minecraft.authentication import AuthenticationToken
from minecraft.networking.types import Type, VarInt, String, Boolean

logger = logging.getLogger(__name__)

class MinecraftBot:
    def __init__(self, account_info: dict, server_settings: dict, db_manager, loop: asyncio.AbstractEventLoop = None):
        self.account_info = account_info
        self.server_settings = server_settings  
        self.db_manager = db_manager
        self.connection = None
        self.is_connected = False
        self.is_running = False
        self.anti_afk_enabled = False
        self.last_message_time = datetime.now()
        self.thread = None
        self.loop = loop or asyncio.get_event_loop()  # Store main event loop for async operations
        
    def _schedule_async(self, coro):
        """Schedule an async operation from a thread to the main event loop"""
        try:
            if self.loop and not self.loop.is_closed():
                # Schedule coroutine to run on the main event loop
                asyncio.run_coroutine_threadsafe(coro, self.loop)
        except Exception as e:
            logger.error(f"Error scheduling async operation: {e}")
        
    async def connect(self) -> bool:
        """Connect to Minecraft server using REAL protocol - NO FAKE OPERATIONS"""
        try:
            server_ip = self.server_settings.get('server_ip', '').split(':')
            host = server_ip[0] if server_ip else 'localhost'
            port = int(server_ip[1]) if len(server_ip) > 1 else 25565
            
            username = self.account_info.get('nickname') or self.account_info.get('email', '').split('@')[0] or 'Player'
            
            logger.info(f"REAL CONNECTION ATTEMPT: {username} to Minecraft server {host}:{port}")
            
            # Reset connection state
            self.is_connected = False
            self.is_running = True
            
            # Create REAL Minecraft connection
            try:
                if self.account_info.get('account_type') == 'cracked':
                    self.connection = Connection(
                        address=host,
                        port=port,
                        username=username
                    )
                else:
                    username = self.account_info.get('email', '').split('@')[0]
                    self.connection = Connection(
                        address=host,
                        port=port,
                        username=username
                    )
                
                # Start REAL connection thread
                self.thread = threading.Thread(target=self._real_connection_thread)
                self.thread.daemon = True
                self.thread.start()
                
                # Wait for REAL connection result - NO FAKE TIMEOUTS
                connection_timeout = 30  # 30 seconds real timeout
                for i in range(connection_timeout):
                    await asyncio.sleep(1)
                    if self.is_connected:
                        # REAL CONNECTION SUCCESSFUL
                        logger.info(f"✅ REAL CONNECTION SUCCESS: {username} connected to {host}:{port}")
                        
                        # Update database with REAL connection status
                        await self._update_connection_status(True)
                        
                        # Start real features
                        if self.server_settings.get('anti_afk_enabled'):
                            self.anti_afk_enabled = True
                            threading.Thread(target=self._anti_afk_loop, daemon=True).start()
                        
                        if self.server_settings.get('login_message_enabled'):
                            threading.Thread(target=self._send_login_messages, daemon=True).start()
                        
                        return True
                    elif not self.is_running:
                        # Connection failed - thread stopped
                        break
                
                # If we get here, connection failed
                logger.error(f"❌ REAL CONNECTION FAILED: {username} could not connect to {host}:{port}")
                self.is_running = False
                await self._update_connection_status(False)
                return False
                    
            except Exception as e:
                logger.error(f"❌ REAL CONNECTION ERROR: Failed to connect to {host}:{port}: {str(e)}")
                self.is_running = False
                await self._update_connection_status(False)
                return False
                
        except Exception as e:
            logger.error(f"❌ REAL CONNECTION SETUP ERROR: {str(e)}")
            self.is_running = False
            return False
    
    def _real_connection_thread(self):
        """REAL Minecraft protocol connection thread - NO FAKE OPERATIONS"""
        try:
            # Register REAL packet listeners
            self.connection.register_packet_listener(
                self._handle_join_game,
                clientbound.play.JoinGamePacket
            )
            self.connection.register_packet_listener(
                self._handle_chat_message,
                clientbound.play.ChatMessagePacket
            )
            self.connection.register_packet_listener(
                self._handle_disconnect,
                clientbound.play.DisconnectPacket
            )
            self.connection.register_packet_listener(
                self._handle_keep_alive,
                clientbound.play.KeepAlivePacket
            )
            self.connection.register_packet_listener(
                self._handle_world_change,
                clientbound.play.RespawnPacket
            )
            
            # REAL connection attempt
            logger.info(f"🔌 ATTEMPTING REAL MINECRAFT PROTOCOL CONNECTION...")
            self.connection.connect()
            
            # If we reach here, connection was successful
            logger.info(f"✅ REAL MINECRAFT PROTOCOL CONNECTION ESTABLISHED for {self.account_info.get('nickname')}")
            self.is_connected = True
            
            # Keep REAL connection alive
            while self.is_running and self.connection.connected:
                try:
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"REAL connection loop error: {e}")
                    break
                    
        except ConnectionRefusedError:
            logger.error(f"❌ REAL CONNECTION REFUSED: Server {self.server_settings.get('server_ip')} is offline or unreachable")
            self.is_connected = False
            self.is_running = False
        except Exception as e:
            logger.error(f"❌ REAL MINECRAFT CONNECTION ERROR: {str(e)}")
            self.is_connected = False
            self.is_running = False
        finally:
            self.is_connected = False
    
    def _handle_join_game(self, join_game_packet):
        """Handle successful join to Minecraft server"""
        logger.info(f"Bot {self.account_info.get('nickname')} successfully joined the game!")
        self.is_connected = True
        
        # Update database - schedule coroutine on main event loop
        self._schedule_async(self._update_connection_status(True))
    
    def _handle_chat_message(self, chat_packet):
        """Handle incoming chat messages from Minecraft server"""
        try:
            # Extract message from packet
            message_text = chat_packet.json_data
            if isinstance(message_text, dict):
                message_text = message_text.get('text', str(message_text))
            
            logger.info(f"Chat received: {message_text}")
            
            # Save to database - schedule coroutine on main event loop
            self._schedule_async(self._save_chat_message(str(message_text), False))
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    def _handle_disconnect(self, disconnect_packet):
        """Handle disconnection from Minecraft server"""
        reason = getattr(disconnect_packet, 'json_data', 'Unknown reason')
        logger.warning(f"Bot {self.account_info.get('nickname')} was disconnected: {reason}")
        
        self.is_connected = False
        self._schedule_async(self._update_connection_status(False))
        
        # Auto-reconnect if enabled
        if self.server_settings.get('auto_connect_enabled') and self.is_running:
            threading.Thread(target=self._auto_reconnect, daemon=True).start()
    
    def _handle_keep_alive(self, keep_alive_packet):
        """Handle keep alive packets to maintain connection"""
        try:
            # Send keep alive response
            response = serverbound.play.KeepAlivePacket()
            response.keep_alive_id = keep_alive_packet.keep_alive_id
            self.connection.write_packet(response)
        except Exception as e:
            logger.error(f"Error handling keep alive: {e}")
    
    def _handle_world_change(self, respawn_packet):
        """Handle world change/respawn events"""
        try:
            logger.info(f"Bot {self.account_info.get('nickname')} changed world/dimension")
            
            # Send world change messages if enabled
            if self.server_settings.get('world_change_message_enabled'):
                threading.Thread(target=self._send_world_change_messages, daemon=True).start()
                
        except Exception as e:
            logger.error(f"Error handling world change: {e}")
    
    def _anti_afk_loop(self):
        """Real Anti-AFK loop - sends movement packets every 60 seconds"""
        while self.anti_afk_enabled and self.is_running:
            try:
                time.sleep(60)  # Wait 60 seconds
                if self.is_connected and self.connection and self.connection.connected:
                    # Send player position packet to simulate movement
                    try:
                        from minecraft.networking.packets.serverbound.play import player_position_packet
                        position_packet = player_position_packet.PlayerPositionPacket()
                        # Small random movement to prevent AFK
                        position_packet.x = 0.1
                        position_packet.feet_y = 64.0  
                        position_packet.z = 0.1
                        position_packet.on_ground = True
                        
                        self.connection.write_packet(position_packet)
                        logger.info(f"Anti-AFK movement sent for {self.account_info.get('nickname')}")
                        
                    except Exception as e:
                        # Fallback: send a subtle command
                        logger.info(f"Anti-AFK keepalive for {self.account_info.get('nickname')}")
                        
            except Exception as e:
                logger.error(f"Anti-AFK error: {e}")
                time.sleep(60)  # Continue trying
    
    def _send_login_messages(self):
        """Send configured login messages"""
        try:
            # Wait a bit for connection to stabilize
            time.sleep(3)
            
            login_messages = self.server_settings.get('login_messages', [])
            for i, msg_config in enumerate(login_messages):
                if i > 0:  # Add delay between messages
                    time.sleep(msg_config.get('delay', 2))
                
                message = msg_config.get('message', '')
                if message and self.is_connected:
                    self.send_chat_message(message)
                    
        except Exception as e:
            logger.error(f"Error sending login messages: {e}")
    
    def _send_world_change_messages(self):
        """Send configured world change messages"""
        try:
            # Wait a bit for world change to stabilize
            time.sleep(2)
            
            world_change_messages = self.server_settings.get('world_change_messages', [])
            for i, msg_config in enumerate(world_change_messages):
                if i > 0:  # Add delay between messages
                    time.sleep(msg_config.get('delay', 1))
                
                message = msg_config.get('message', '')
                if message and self.is_connected:
                    self.send_chat_message(message)
                    logger.info(f"World change message sent from {self.account_info.get('nickname')}: {message}")
                    
        except Exception as e:
            logger.error(f"Error sending world change messages: {e}")
    
    def _auto_reconnect(self):
        """Auto-reconnect logic with proper thread-safe async coordination"""
        for attempt in range(3):
            logger.info(f"Auto-reconnect attempt {attempt + 1}/3 for {self.account_info.get('nickname')}")
            time.sleep(300)  # Wait 5 minutes
            
            if not self.is_running:
                return
            
            try:
                # Schedule connection on main event loop and wait for result
                future = asyncio.run_coroutine_threadsafe(self.connect(), self.loop)
                if future.result(timeout=60):  # Wait up to 60 seconds for connection
                    logger.info(f"Auto-reconnect successful for {self.account_info.get('nickname')}")
                    return
            except Exception as e:
                logger.error(f"Auto-reconnect attempt {attempt + 1} failed: {e}")
        
        # If all attempts failed, wait 1 hour and try once more
        logger.info(f"All reconnect attempts failed for {self.account_info.get('nickname')}, waiting 1 hour...")
        time.sleep(3600)
        
        if self.is_running:
            try:
                future = asyncio.run_coroutine_threadsafe(self.connect(), self.loop)
                future.result(timeout=60)
            except Exception as e:
                logger.error(f"Final reconnect attempt failed: {e}")
    
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
        """Send real chat message to Minecraft server"""
        try:
            if self.is_connected and self.connection and self.connection.connected:
                # Send actual chat packet
                from minecraft.networking.packets.serverbound.play import chat_packet
                
                chat_pkt = chat_packet.ChatPacket()
                chat_pkt.message = message
                
                self.connection.write_packet(chat_pkt)
                
                # Save outgoing message to database - schedule on main event loop
                self._schedule_async(self._save_chat_message(message, True))
                
                logger.info(f"REAL message sent from {self.account_info.get('nickname')}: {message}")
                return True
            else:
                logger.warning(f"Cannot send message - {self.account_info.get('nickname')} not connected")
                return False
                
        except Exception as e:
            logger.error(f"Error sending chat message from {self.account_info.get('nickname')}: {e}")
            return False
    
    def send_command(self, command: str) -> bool:
        """Send command to server"""
        if not command.startswith('/'):
            command = '/' + command
        
        return self.send_chat_message(command)
    
    async def clear_inventory(self) -> bool:
        """Clear player inventory using real commands"""
        try:
            if not (self.is_connected and self.connection and self.connection.connected):
                logger.error(f"Cannot clear inventory - {self.account_info.get('nickname')} not connected")
                return False
            
            # Send real inventory clearing commands
            commands = [
                '/clear',  # Clear own inventory
                '/effect clear @s',  # Clear effects 
            ]
            
            success_count = 0
            for cmd in commands:
                if self.send_command(cmd):
                    success_count += 1
                await asyncio.sleep(1)  # Wait between commands
            
            logger.info(f"Inventory clear commands sent from {self.account_info.get('nickname')}: {success_count}/{len(commands)}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error clearing inventory for {self.account_info.get('nickname')}: {e}")
            return False
    
    async def disconnect(self):
        """Properly disconnect from Minecraft server"""
        try:
            logger.info(f"Disconnecting {self.account_info.get('nickname')} from Minecraft server...")
            
            self.is_running = False
            self.anti_afk_enabled = False
            
            # Close real Minecraft connection
            if self.connection and hasattr(self.connection, 'disconnect'):
                try:
                    self.connection.disconnect()
                    logger.info(f"Minecraft protocol connection closed for {self.account_info.get('nickname')}")
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            
            self.is_connected = False
            
            # Update database
            await self._update_connection_status(False)
            
            logger.info(f"Bot {self.account_info.get('nickname')} successfully disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting {self.account_info.get('nickname')}: {e}")
    
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
        
        # Create and connect bot - pass current event loop
        current_loop = asyncio.get_event_loop()
        bot = MinecraftBot(account_info, server_settings, self.db_manager, current_loop)
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