from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Set
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import asyncio
import json
from minecraft_manager import MinecraftManager

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection with comprehensive setup
try:
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'minecraft_afk_console')
    
    logger.info(f"Connecting to MongoDB: {mongo_url}")
    logger.info(f"Database name: {db_name}")
    
    client = AsyncIOMotorClient(
        mongo_url, 
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        maxPoolSize=10,
        minPoolSize=1
    )
    db = client[db_name]
    
    # Database schema and initialization
    class DatabaseManager:
        def __init__(self, database):
            self.db = database
            
        async def initialize_database(self):
            """Initialize database with required collections and indexes"""
            try:
                logger.info("🔧 Initializing database...")
                
                # Test connection first
                await client.admin.command('ping')
                logger.info("✅ MongoDB connection successful")
                
                # Create collections if they don't exist
                await self.create_collections()
                
                # Create indexes for performance
                await self.create_indexes()
                
                # Create default admin user if none exists
                await self.ensure_admin_user()
                
                logger.info("🎉 Database initialization completed successfully!")
                
            except Exception as e:
                logger.error(f"❌ Database initialization failed: {e}")
                raise
        
        async def create_collections(self):
            """Create all required collections"""
            collections = [
                'users',
                'minecraft_accounts', 
                'chat_messages',
                'server_settings',
                'system_logs'
            ]
            
            existing_collections = await self.db.list_collection_names()
            
            for collection_name in collections:
                if collection_name not in existing_collections:
                    await self.db.create_collection(collection_name)
                    logger.info(f"📁 Created collection: {collection_name}")
                else:
                    logger.info(f"📁 Collection already exists: {collection_name}")
        
        async def create_indexes(self):
            """Create indexes for better performance"""
            try:
                # Users collection indexes
                await self.db.users.create_index("username", unique=True)
                await self.db.users.create_index("role")
                await self.db.users.create_index("created_at")
                
                # Minecraft accounts indexes
                await self.db.minecraft_accounts.create_index("user_id")
                await self.db.minecraft_accounts.create_index("account_type")
                await self.db.minecraft_accounts.create_index("is_online")
                await self.db.minecraft_accounts.create_index([("user_id", 1), ("account_type", 1)])
                
                # Chat messages indexes
                await self.db.chat_messages.create_index("account_id")
                await self.db.chat_messages.create_index("timestamp")
                await self.db.chat_messages.create_index("is_outgoing")
                await self.db.chat_messages.create_index([("account_id", 1), ("timestamp", -1)])
                
                # Server settings indexes
                await self.db.server_settings.create_index("user_id", unique=True)
                
                # System logs indexes
                await self.db.system_logs.create_index("timestamp")
                await self.db.system_logs.create_index("level")
                await self.db.system_logs.create_index("user_id")
                
                logger.info("📊 Database indexes created successfully")
                
            except Exception as e:
                logger.error(f"❌ Error creating indexes: {e}")
                # Don't fail if indexes already exist
                pass
        
        async def ensure_admin_user(self):
            """Ensure at least one admin user exists for first-time setup"""
            try:
                admin_count = await self.db.users.count_documents({"role": "admin"})
                if admin_count == 0:
                    logger.info("👑 No admin users found - ready for admin setup")
                else:
                    logger.info(f"👑 Found {admin_count} admin user(s)")
                    
            except Exception as e:
                logger.error(f"❌ Error checking admin users: {e}")
        
        async def get_database_stats(self):
            """Get database statistics for monitoring"""
            try:
                stats = {
                    "database_name": self.db.name,
                    "collections": {},
                    "total_size": 0
                }
                
                collections = await self.db.list_collection_names()
                for collection_name in collections:
                    collection = self.db[collection_name]
                    count = await collection.count_documents({})
                    stats["collections"][collection_name] = count
                
                return stats
            except Exception as e:
                logger.error(f"Error getting database stats: {e}")
                return {"error": str(e)}
    
    # Initialize database manager
    db_manager = DatabaseManager(db)
    
    # Initialize Minecraft manager
    minecraft_manager = MinecraftManager(db_manager)
            
except Exception as e:
    logger.error(f"❌ Database configuration error: {e}")
    # Don't raise here, let the app start and show a proper error message
    client = None
    db = None
    db_manager = None

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
SECRET_KEY = "minecraft-afk-client-secret-key-2024"
ALGORITHM = "HS256"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    password_hash: str
    role: str  # admin, moderator, user
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AdminSetup(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128)

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="user", pattern="^(admin|moderator|user)$")

class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class MinecraftAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    account_type: str  # microsoft or cracked
    email: Optional[str] = None
    nickname: Optional[str] = None
    is_online: bool = False
    last_seen: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MinecraftAccountCreate(BaseModel):
    account_type: str
    email: Optional[str] = None
    nickname: Optional[str] = None

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    account_id: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_outgoing: bool = False

class SendMessage(BaseModel):
    account_ids: List[str]
    message: str

class SpamMessage(BaseModel):
    account_ids: List[str]
    message: str
    interval_seconds: int

class ServerSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    server_ip: str
    login_delay: int = 5
    offline_accounts_enabled: bool = True
    anti_afk_enabled: bool = False
    auto_connect_enabled: bool = False
    login_message_enabled: bool = False
    login_messages: List[dict] = []
    world_change_messages_enabled: bool = False
    world_change_messages: List[dict] = []
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ServerSettingsUpdate(BaseModel):
    server_ip: Optional[str] = None
    login_delay: Optional[int] = None
    offline_accounts_enabled: Optional[bool] = None
    anti_afk_enabled: Optional[bool] = None
    auto_connect_enabled: Optional[bool] = None
    login_message_enabled: Optional[bool] = None
    login_messages: Optional[List[dict]] = None
    world_change_messages_enabled: Optional[bool] = None
    world_change_messages: Optional[List[dict]] = None

class AccountAction(BaseModel):
    account_id: str
    action: str  # connect, disconnect, clear_inventory

class DashboardStats(BaseModel):
    active_accounts: int
    total_accounts: int
    server_status: str
    messages_today: int
    online_accounts: List[dict]
    recent_activity: List[dict]

# WebSocket Manager for real-time updates
class SystemLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    level: str  # info, warning, error
    message: str
    user_id: Optional[str] = None
    action: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# WebSocket Manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass  # Connection already removed

    async def broadcast_message(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        # Remove dead connections
        for dead_connection in dead_connections:
            try:
                self.active_connections.remove(dead_connection)
            except ValueError:
                pass

    async def log_system_event(self, level: str, message: str, user_id: str = None, action: str = None):
        """Log system events to database"""
        if db is not None:
            try:
                log_entry = SystemLog(
                    level=level,
                    message=message,
                    user_id=user_id,
                    action=action
                )
                await db.system_logs.insert_one(log_entry.dict())
            except Exception as e:
                logger.error(f"Failed to log system event: {e}")

manager = ConnectionManager()

# Helper functions
def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def check_database_connection():
    """Check if database is available"""
    if db is None or client is None:
        raise HTTPException(status_code=503, detail="Database not available. Please check your MongoDB connection.")
    
    try:
        await client.admin.command('ping', maxTimeMS=1000)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Check database first
    await check_database_connection()
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Health Check
@api_router.get("/health")
async def health_check():
    health_status = {
        "status": "ok",
        "message": "Minecraft AFK Console API",
        "database": "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Check database connection
    if client is not None and db is not None:
        try:
            await client.admin.command('ping')
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            health_status["status"] = "warning"
    else:
        health_status["database"] = "not_configured"
        health_status["status"] = "error"
    
    return health_status

# Database Statistics Endpoint
@api_router.get("/database/stats")
async def get_database_stats(current_user: User = Depends(get_current_user)):
    """Get database statistics (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        stats = await db_manager.get_database_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Database Initialization Endpoint (for manual setup)
@api_router.post("/database/initialize")
async def initialize_database_manual():
    """Manually initialize database (useful for troubleshooting)"""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database manager not available")
    
    try:
        await db_manager.initialize_database()
        return {"message": "Database initialized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")

# Demo Reset (for testing only)
@api_router.post("/demo/reset")
async def reset_demo():
    # Clear all users for demo purposes
    await db.users.delete_many({})
    return {"message": "Demo reset - all users deleted"}

# Auth Routes
@api_router.post("/auth/setup-admin", response_model=Token)
async def setup_admin(user_data: AdminSetup):
    # Check database connection
    await check_database_connection()
    
    # Check if any admin exists
    existing_admin = await db.users.find_one({"role": "admin"})
    if existing_admin:
        raise HTTPException(status_code=400, detail="Admin already exists")
    
    # Create admin user (always admin role for first setup)
    hashed_password = hash_password(user_data.password)
    user = User(
        username=user_data.username,
        password_hash=hashed_password,
        role="admin"  # Force admin role for initial setup
    )
    
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    # Check database connection
    await check_database_connection()
    
    user = await db.users.find_one({"username": user_data.username})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user["id"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"]
        }
    }

@api_router.get("/auth/check-admin")
async def check_admin():
    try:
        # Check database connection
        await check_database_connection()
        
        admin_exists = await db.users.find_one({"role": "admin"})
        return {"admin_exists": admin_exists is not None}
    except HTTPException as e:
        if e.status_code == 503:
            # Database not available, assume no admin exists so setup can proceed
            return {"admin_exists": False, "database_status": "unavailable"}
        raise

@api_router.post("/users", response_model=dict)
async def create_user(user_data: UserCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Check if user exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = hash_password(user_data.password)
    user = User(
        username=user_data.username,
        password_hash=hashed_password,
        role=user_data.role
    )
    
    await db.users.insert_one(user.dict())
    
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at
    }

@api_router.get("/users", response_model=List[dict])
async def get_users(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    users = await db.users.find({}, {"password_hash": 0, "_id": 0}).to_list(1000)
    return users

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, user_data: UserCreate, current_user: User = Depends(get_current_user)):
    # Only admins can edit users
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check database connection
    await check_database_connection()
    
    # Find the user
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent editing the last admin
    if user["role"] == "admin" and user_data.role != "admin":
        admin_count = await db.users.count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot change role of the last admin user")
    
    # Prepare update data
    update_data = {
        "username": user_data.username,
        "role": user_data.role
    }
    
    # Update password if provided
    if user_data.password:
        update_data["password_hash"] = hash_password(user_data.password)
    
    # Update user
    await db.users.update_one(
        {"id": user_id}, 
        {"$set": update_data}
    )
    
    # Log update
    await manager.log_system_event(
        "info", 
        f"User {user_data.username} updated by admin {current_user.username}",
        current_user.id,
        "user_update"
    )
    
    return {"message": "User updated successfully"}

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    # Only admins can delete users
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check database connection
    await check_database_connection()
    
    # Find the user
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Prevent deleting the last admin
    if user["role"] == "admin":
        admin_count = await db.users.count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin user")
    
    # Disconnect all accounts of this user
    user_accounts = await db.minecraft_accounts.find({"user_id": user_id}).to_list(1000)
    for account in user_accounts:
        if minecraft_manager.is_account_connected(account["id"]):
            await minecraft_manager.disconnect_account(account["id"])
    
    # Delete user's accounts
    await db.minecraft_accounts.delete_many({"user_id": user_id})
    
    # Delete user's server settings
    await db.server_settings.delete_many({"user_id": user_id})
    
    # Delete the user
    await db.users.delete_one({"id": user_id})
    
    # Log deletion
    await manager.log_system_event(
        "info", 
        f"User {user['username']} and all associated data deleted by admin {current_user.username}",
        current_user.id,
        "user_delete"
    )
    
    return {"message": "User and all associated data deleted successfully"}

# Minecraft Account Routes
@api_router.post("/accounts", response_model=dict)
async def create_minecraft_account(account_data: MinecraftAccountCreate, current_user: User = Depends(get_current_user)):
    if account_data.account_type == "microsoft" and not account_data.email:
        raise HTTPException(status_code=400, detail="Email required for Microsoft accounts")
    elif account_data.account_type == "cracked" and not account_data.nickname:
        raise HTTPException(status_code=400, detail="Nickname required for cracked accounts")
    
    account = MinecraftAccount(
        user_id=current_user.id,
        account_type=account_data.account_type,
        email=account_data.email,
        nickname=account_data.nickname
    )
    
    await db.minecraft_accounts.insert_one(account.dict())
    
    return account.dict()

@api_router.get("/accounts", response_model=List[dict])
async def get_minecraft_accounts(current_user: User = Depends(get_current_user)):
    accounts = await db.minecraft_accounts.find({"user_id": current_user.id}, {"_id": 0}).to_list(1000)
    return accounts

@api_router.put("/accounts/{account_id}")
async def update_minecraft_account(account_id: str, account_data: MinecraftAccountCreate, current_user: User = Depends(get_current_user)):
    # Check database connection
    await check_database_connection()
    
    # Find the account
    account = await db.minecraft_accounts.find_one({"id": account_id, "user_id": current_user.id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Validate input based on account type
    if account_data.account_type == "microsoft" and not account_data.email:
        raise HTTPException(status_code=400, detail="Email required for Microsoft accounts")
    elif account_data.account_type == "cracked" and not account_data.nickname:
        raise HTTPException(status_code=400, detail="Nickname required for cracked accounts")
    
    # Prepare update data
    update_data = {
        "account_type": account_data.account_type,
        "email": account_data.email if account_data.account_type == "microsoft" else None,
        "nickname": account_data.nickname if account_data.account_type == "cracked" else None,
    }
    
    # Update account
    await db.minecraft_accounts.update_one(
        {"id": account_id}, 
        {"$set": update_data}
    )
    
    # Log update
    await manager.log_system_event(
        "info", 
        f"Account {account_id} updated by {current_user.username}",
        current_user.id,
        "account_update"
    )
    
    return {"message": "Account updated successfully"}

@api_router.delete("/accounts/{account_id}")
@api_router.delete("/accounts/{account_id}")
async def delete_minecraft_account(account_id: str, current_user: User = Depends(get_current_user)):
    # Check database connection
    await check_database_connection()
    
    # Find the account
    account = await db.minecraft_accounts.find_one({"id": account_id, "user_id": current_user.id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Disconnect if connected
    if minecraft_manager.is_account_connected(account_id):
        await minecraft_manager.disconnect_account(account_id)
    
    # Delete from database
    await db.minecraft_accounts.delete_one({"id": account_id, "user_id": current_user.id})
    
    # Log deletion
    await manager.log_system_event(
        "info", 
        f"Account {account.get('email') or account.get('nickname')} deleted by {current_user.username}",
        current_user.id,
        "account_delete"
    )
    
    return {"message": "Account deleted successfully"}

@api_router.post("/accounts/{account_id}/connect")
async def connect_account(account_id: str, current_user: User = Depends(get_current_user)):
    # Check database connection
    await check_database_connection()
    
    # Find the account
    account = await db.minecraft_accounts.find_one({"id": account_id, "user_id": current_user.id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Check if server settings exist
    server_settings = await db.server_settings.find_one({"user_id": current_user.id})
    if not server_settings or not server_settings.get("server_ip"):
        raise HTTPException(status_code=400, detail="Server IP not configured. Please set up server connection first.")
    
    # Connect to actual Minecraft server
    try:
        success = await minecraft_manager.connect_account(account, server_settings)
        
        if success:
            # Log successful connection
            await manager.log_system_event(
                "info", 
                f"Account {account.get('email') or account.get('nickname')} connected to {server_settings.get('server_ip')}",
                current_user.id,
                "account_connect"
            )
            
            # Broadcast real-time update
            await manager.broadcast_message({
                "type": "account_connected",
                "account_id": account_id,
                "account_name": account.get("email") or account.get("nickname"),
                "server_ip": server_settings.get("server_ip")
            })
            
            return {
                "message": f"Account successfully connected to {server_settings.get('server_ip')}",
                "success": True
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to Minecraft server. Check server IP and account credentials.")
            
    except Exception as e:
        logger.error(f"Error connecting account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

@api_router.post("/accounts/{account_id}/disconnect")
async def disconnect_account(account_id: str, current_user: User = Depends(get_current_user)):
    # Check database connection
    await check_database_connection()
    
    # Find the account
    account = await db.minecraft_accounts.find_one({"id": account_id, "user_id": current_user.id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Disconnect from actual Minecraft server
    try:
        await minecraft_manager.disconnect_account(account_id)
        
        # Log disconnection
        await manager.log_system_event(
            "info", 
            f"Account {account.get('email') or account.get('nickname')} disconnected",
            current_user.id,
            "account_disconnect"
        )
        
        # Broadcast real-time update
        await manager.broadcast_message({
            "type": "account_disconnected",
            "account_id": account_id,
            "account_name": account.get("email") or account.get("nickname")
        })
        
        return {
            "message": "Account successfully disconnected",
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Disconnection failed: {str(e)}")

@api_router.post("/accounts/{account_id}/clear-inventory")
async def clear_account_inventory(account_id: str, current_user: User = Depends(get_current_user)):
    # Check database connection
    await check_database_connection()
    
    # Find the account
    account = await db.minecraft_accounts.find_one({"id": account_id, "user_id": current_user.id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Check if account is connected
    if not minecraft_manager.is_account_connected(account_id):
        raise HTTPException(status_code=400, detail="Account must be connected to server to clear inventory")
    
    # Clear inventory using Minecraft manager
    try:
        success = await minecraft_manager.clear_account_inventory(account_id)
        
        if success:
            # Log inventory clearing
            await manager.log_system_event(
                "info", 
                f"Inventory cleared for account {account.get('email') or account.get('nickname')}",
                current_user.id,
                "inventory_clear"
            )
            
            # Broadcast real-time update
            await manager.broadcast_message({
                "type": "inventory_cleared",
                "account_id": account_id,
                "account_name": account.get("email") or account.get("nickname")
            })
            
            return {"message": "Inventory cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear inventory")
            
    except Exception as e:
        logger.error(f"Error clearing inventory for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear inventory: {str(e)}")

# Chat Routes
@api_router.get("/chats", response_model=List[dict])
async def get_chat_messages(current_user: User = Depends(get_current_user)):
    # Get user's accounts
    accounts = await db.minecraft_accounts.find({"user_id": current_user.id}, {"_id": 0}).to_list(1000)
    account_ids = [account["id"] for account in accounts]
    
    # Get recent chat messages
    messages = await db.chat_messages.find(
        {"account_id": {"$in": account_ids}}, {"_id": 0}
    ).sort("timestamp", -1).limit(100).to_list(100)
    
    return messages

@api_router.post("/chats/send")
async def send_message(message_data: SendMessage, current_user: User = Depends(get_current_user)):
    # Check database connection first
    await check_database_connection()
    
    # Validate input
    if not message_data.account_ids:
        raise HTTPException(status_code=400, detail="At least one account must be selected")
    
    if not message_data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Verify accounts belong to user
    accounts = await db.minecraft_accounts.find(
        {"id": {"$in": message_data.account_ids}, "user_id": current_user.id}
    ).to_list(1000)
    
    if len(accounts) != len(message_data.account_ids):
        raise HTTPException(status_code=400, detail="Invalid account IDs")
    
    # Send messages through Minecraft manager
    success = await minecraft_manager.send_message_from_accounts(
        message_data.account_ids, 
        message_data.message
    )
    
    if success:
        # Log message sending
        await manager.log_system_event(
            "info", 
            f"Chat message sent from {len(message_data.account_ids)} accounts: {message_data.message}",
            current_user.id,
            "chat_message_send"
        )
        
        return {"message": f"Message sent successfully from {len(message_data.account_ids)} account(s)"}
    else:
        raise HTTPException(status_code=400, detail="No accounts were able to send the message. Ensure accounts are connected to server.")

@api_router.post("/chats/spam")
async def send_spam_message(spam_data: SpamMessage, current_user: User = Depends(get_current_user)):
    """Send spam messages with timed intervals"""
    # Check database connection first
    await check_database_connection()
    
    # Validate input
    if not spam_data.account_ids:
        raise HTTPException(status_code=400, detail="At least one account must be selected")
    
    if not spam_data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if spam_data.interval_seconds < 1 or spam_data.interval_seconds > 3600:
        raise HTTPException(status_code=400, detail="Interval must be between 1 and 3600 seconds")
    
    # Verify accounts belong to user
    accounts = await db.minecraft_accounts.find(
        {"id": {"$in": spam_data.account_ids}, "user_id": current_user.id}
    ).to_list(1000)
    
    if len(accounts) != len(spam_data.account_ids):
        raise HTTPException(status_code=400, detail="Invalid account IDs")
    
    # Start spam task in background
    asyncio.create_task(
        _spam_message_task(
            spam_data.account_ids, 
            spam_data.message, 
            spam_data.interval_seconds,
            current_user.id
        )
    )
    
    # Log spam start
    await manager.log_system_event(
        "info", 
        f"Spam messages started from {len(spam_data.account_ids)} accounts: {spam_data.message} (interval: {spam_data.interval_seconds}s)",
        current_user.id,
        "spam_message_start"
    )
    
    return {
        "message": f"Spam messages started from {len(spam_data.account_ids)} account(s) with {spam_data.interval_seconds}s interval",
        "accounts_count": len(spam_data.account_ids),
        "interval": spam_data.interval_seconds
    }

async def _spam_message_task(account_ids: List[str], message: str, interval: int, user_id: str):
    """Background task to send spam messages at intervals"""
    try:
        spam_count = 0
        # Send messages for a reasonable duration (e.g., 10 iterations)
        for _ in range(10):
            success = await minecraft_manager.send_message_from_accounts(account_ids, message)
            
            if success:
                spam_count += 1
                
            # Wait for the specified interval
            await asyncio.sleep(interval)
        
        # Log spam completion
        await manager.log_system_event(
            "info", 
            f"Spam messages completed: {spam_count} messages sent from {len(account_ids)} accounts",
            user_id,
            "spam_message_complete"
        )
        
    except Exception as e:
        # Log spam error
        await manager.log_system_event(
            "error", 
            f"Spam messages error: {str(e)}",
            user_id,
            "spam_message_error"
        )

# Server Settings Routes
@api_router.get("/server-settings", response_model=dict)
async def get_server_settings(current_user: User = Depends(get_current_user)):
    settings = await db.server_settings.find_one({"user_id": current_user.id}, {"_id": 0})
    if not settings:
        # Create default settings
        default_settings = ServerSettings(user_id=current_user.id, server_ip="")
        await db.server_settings.insert_one(default_settings.dict())
        return default_settings.dict()
    return settings

@api_router.put("/server-settings", response_model=dict)
async def update_server_settings(settings_data: ServerSettingsUpdate, current_user: User = Depends(get_current_user)):
    update_data = {k: v for k, v in settings_data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.server_settings.update_one(
        {"user_id": current_user.id},
        {"$set": update_data},
        upsert=True
    )
    
    updated_settings = await db.server_settings.find_one({"user_id": current_user.id}, {"_id": 0})
    return updated_settings

@api_router.post("/server/connect")
async def connect_to_server(current_user: User = Depends(get_current_user)):
    # Check database connection
    await check_database_connection()
    
    # Get server settings
    server_settings = await db.server_settings.find_one({"user_id": current_user.id})
    if not server_settings or not server_settings.get("server_ip"):
        raise HTTPException(status_code=400, detail="Server IP not configured")
    
    # Log simulation
    await manager.log_system_event(
        "info", 
        f"SIMULATION: Server connection initiated to {server_settings.get('server_ip')}",
        current_user.id,
        "server_connect_simulation"
    )
    
    # TODO: Implement actual Minecraft server connection using minecraft-protocol library
    # For now, just simulate connection
    return {
        "message": f"Server connection simulated for {server_settings.get('server_ip')}",
        "simulation": True,
        "server_ip": server_settings.get("server_ip"),
        "note": "This is a simulation. Real Minecraft server connection not implemented yet."
    }

@api_router.post("/server/disconnect")
async def disconnect_from_server(current_user: User = Depends(get_current_user)):
    # Check database connection
    await check_database_connection()
    
    # Log simulation
    await manager.log_system_event(
        "info", 
        "SIMULATION: Server disconnection initiated",
        current_user.id,
        "server_disconnect_simulation"
    )
    
    # TODO: Implement actual Minecraft server disconnection
    return {
        "message": "Server disconnection simulated",
        "simulation": True,
        "note": "This is a simulation. Real Minecraft server connection not implemented yet."
    }

# Dashboard Stats Route
@api_router.get("/dashboard/stats", response_model=dict)
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get accounts stats
    if current_user.role == "admin":
        # Admin can see all accounts
        total_accounts = await db.minecraft_accounts.count_documents({})
        active_accounts = await db.minecraft_accounts.count_documents({"is_online": True})
        online_accounts = await db.minecraft_accounts.find(
            {"is_online": True}, {"_id": 0}
        ).to_list(50)
    else:
        # Moderator sees only their accounts
        total_accounts = await db.minecraft_accounts.count_documents({"user_id": current_user.id})
        active_accounts = await db.minecraft_accounts.count_documents(
            {"user_id": current_user.id, "is_online": True}
        )
        online_accounts = await db.minecraft_accounts.find(
            {"user_id": current_user.id, "is_online": True}, {"_id": 0}
        ).to_list(50)
    
    # Get messages count for today
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    messages_today = await db.chat_messages.count_documents({
        "timestamp": {"$gte": today}
    })
    
    # Get recent activity
    recent_messages = await db.chat_messages.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(5).to_list(5)
    
    # Server status (simplified)
    server_status = "online" if active_accounts > 0 else "offline"
    
    return {
        "active_accounts": active_accounts,
        "total_accounts": total_accounts,
        "server_status": server_status,
        "messages_today": messages_today,
        "online_accounts": online_accounts,
        "recent_activity": recent_messages
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Include the router in the main app
app.include_router(api_router)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["minecraft-afk.preview.emergentagent.com", "localhost", "127.0.0.1"]
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Logging already configured above

@app.on_event("startup")
async def startup_database():
    """Initialize database on startup"""
    global db_manager
    if db_manager:
        try:
            await db_manager.initialize_database()
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            logger.info("🔧 App will continue running, but some features may not work")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Cleanup on shutdown"""
    if client:
        client.close()
        logger.info("🔌 Database connection closed")