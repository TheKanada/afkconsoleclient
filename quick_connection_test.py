#!/usr/bin/env python3
"""
Quick Real Connection Test
=========================
Test one server to verify the pyCraft fix is working
"""

import asyncio
import aiohttp
import json
import time

BACKEND_URL = "https://afkcraft-console.preview.emergentagent.com/api"

async def quick_test():
    async with aiohttp.ClientSession() as session:
        # Reset demo
        await session.post(f"{BACKEND_URL}/demo/reset")
        
        # Setup admin
        admin_data = {"username": "quicktest", "password": "testpass123"}
        async with session.post(f"{BACKEND_URL}/auth/setup-admin", json=admin_data) as resp:
            data = await resp.json()
            token = data["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create account
        account_data = {"account_type": "cracked", "nickname": f"QuickTest_{int(time.time())}"}
        async with session.post(f"{BACKEND_URL}/accounts", json=account_data, headers=headers) as resp:
            account = await resp.json()
            account_id = account["id"]
        
        # Setup server
        settings_data = {"server_ip": "mc.hypixel.net:25565"}
        await session.put(f"{BACKEND_URL}/server-settings", json=settings_data, headers=headers)
        
        # Test connection
        print(f"🚀 Testing connection to mc.hypixel.net:25565...")
        async with session.post(f"{BACKEND_URL}/accounts/{account_id}/connect", headers=headers) as resp:
            print(f"Status: {resp.status}")
            response_text = await resp.text()
            print(f"Response: {response_text}")
        
        # Cleanup
        await session.delete(f"{BACKEND_URL}/accounts/{account_id}", headers=headers)

if __name__ == "__main__":
    asyncio.run(quick_test())