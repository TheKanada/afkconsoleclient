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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_message(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
    return {"status": "ok", "message": "Minecraft AFK Console API"}

# Demo Reset (for testing only)
@api_router.post("/demo/reset")
async def reset_demo():
    # Clear all users for demo purposes
    await db.users.delete_many({})
    return {"message": "Demo reset - all users deleted"}

# Auth Routes
@api_router.post("/auth/setup-admin", response_model=Token)
async def setup_admin(user_data: UserCreate):
    # Check if any admin exists
    existing_admin = await db.users.find_one({"role": "admin"})
    if existing_admin:
        raise HTTPException(status_code=400, detail="Admin already exists")
    
    # Create admin user
    hashed_password = hash_password(user_data.password)
    user = User(
        username=user_data.username,
        password_hash=hashed_password,
        role="admin"
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
    admin_exists = await db.users.find_one({"role": "admin"})
    return {"admin_exists": admin_exists is not None}

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

@api_router.delete("/accounts/{account_id}")
async def delete_minecraft_account(account_id: str, current_user: User = Depends(get_current_user)):
    result = await db.minecraft_accounts.delete_one({"id": account_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account deleted successfully"}

@api_router.post("/accounts/{account_id}/connect")
async def connect_account(account_id: str, current_user: User = Depends(get_current_user)):
    # Find the account
    account = await db.minecraft_accounts.find_one({"id": account_id, "user_id": current_user.id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Update account status to online
    await db.minecraft_accounts.update_one(
        {"id": account_id}, 
        {"$set": {"is_online": True, "last_seen": datetime.now(timezone.utc)}}
    )
    
    # Broadcast real-time update
    await manager.broadcast_message({
        "type": "account_connected",
        "account_id": account_id,
        "account_name": account.get("email") or account.get("nickname")
    })
    
    return {"message": "Account connected successfully"}

@api_router.post("/accounts/{account_id}/disconnect")
async def disconnect_account(account_id: str, current_user: User = Depends(get_current_user)):
    # Find the account
    account = await db.minecraft_accounts.find_one({"id": account_id, "user_id": current_user.id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Update account status to offline
    await db.minecraft_accounts.update_one(
        {"id": account_id}, 
        {"$set": {"is_online": False, "last_seen": datetime.now(timezone.utc)}}
    )
    
    # Broadcast real-time update
    await manager.broadcast_message({
        "type": "account_disconnected",
        "account_id": account_id,
        "account_name": account.get("email") or account.get("nickname")
    })
    
    return {"message": "Account disconnected successfully"}

@api_router.post("/accounts/{account_id}/clear-inventory")
async def clear_account_inventory(account_id: str, current_user: User = Depends(get_current_user)):
    # Find the account
    account = await db.minecraft_accounts.find_one({"id": account_id, "user_id": current_user.id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if not account.get("is_online"):
        raise HTTPException(status_code=400, detail="Account must be online to clear inventory")
    
    # TODO: Implement actual inventory clearing logic
    # For now, we'll simulate it
    
    # Broadcast real-time update
    await manager.broadcast_message({
        "type": "inventory_cleared",
        "account_id": account_id,
        "account_name": account.get("email") or account.get("nickname")
    })
    
    return {"message": "Inventory cleared successfully"}

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
    # Verify accounts belong to user
    accounts = await db.minecraft_accounts.find(
        {"id": {"$in": message_data.account_ids}, "user_id": current_user.id}
    ).to_list(1000)
    
    if len(accounts) != len(message_data.account_ids):
        raise HTTPException(status_code=400, detail="Invalid account IDs")
    
    # Store outgoing messages
    messages = []
    for account_id in message_data.account_ids:
        message = ChatMessage(
            account_id=account_id,
            message=message_data.message,
            is_outgoing=True
        )
        messages.append(message.dict())
    
    await db.chat_messages.insert_many(messages)
    
    # TODO: Send actual messages to Minecraft server
    
    return {"message": "Messages sent successfully"}

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
    
    result = await db.server_settings.update_one(
        {"user_id": current_user.id},
        {"$set": update_data},
        upsert=True
    )
    
    updated_settings = await db.server_settings.find_one({"user_id": current_user.id}, {"_id": 0})
    return updated_settings

@api_router.post("/server/connect")
async def connect_to_server(current_user: User = Depends(get_current_user)):
    # TODO: Implement actual Minecraft server connection
    # For now, just simulate connection
    return {"message": "Connection initiated"}

@api_router.post("/server/disconnect")
async def disconnect_from_server(current_user: User = Depends(get_current_user)):
    # TODO: Implement actual Minecraft server disconnection
    return {"message": "Disconnection initiated"}

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()