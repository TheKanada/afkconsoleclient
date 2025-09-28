from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import asyncio
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
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
    username: str
    password: str
    role: str = "user"

class UserLogin(BaseModel):
    username: str
    password: str

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

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

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
    
    users = await db.users.find({}, {"password_hash": 0}).to_list(1000)
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
    accounts = await db.minecraft_accounts.find({"user_id": current_user.id}).to_list(1000)
    return accounts

@api_router.delete("/accounts/{account_id}")
async def delete_minecraft_account(account_id: str, current_user: User = Depends(get_current_user)):
    result = await db.minecraft_accounts.delete_one({"id": account_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account deleted successfully"}

# Chat Routes
@api_router.get("/chats", response_model=List[dict])
async def get_chat_messages(current_user: User = Depends(get_current_user)):
    # Get user's accounts
    accounts = await db.minecraft_accounts.find({"user_id": current_user.id}).to_list(1000)
    account_ids = [account["id"] for account in accounts]
    
    # Get recent chat messages
    messages = await db.chat_messages.find(
        {"account_id": {"$in": account_ids}}
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
    settings = await db.server_settings.find_one({"user_id": current_user.id})
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
    
    updated_settings = await db.server_settings.find_one({"user_id": current_user.id})
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
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