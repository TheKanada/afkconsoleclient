#!/usr/bin/env python3
"""
REAL MINECRAFT SERVER CONNECTION TEST
=====================================

This test verifies that the Minecraft AFK Console makes REAL connections to actual Minecraft servers,
not fake/simulated operations. Tests with public servers and validates real protocol attempts.

Test Focus:
- Real connection attempts to public Minecraft servers
- Proper error handling for unreachable servers  
- Backend logs verification for actual protocol attempts
- No fake success responses
"""

import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime
import subprocess
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BACKEND_URL = "https://afkcraft-console.preview.emergentagent.com/api"
TEST_RESULTS = []

# Public Minecraft servers for testing REAL connections
PUBLIC_SERVERS = [
    "mc.hypixel.net:25565",
    "play.cubecraft.net:25565", 
    "2b2t.org:25565",
    "localhost:25565",  # Should fail if no local server
    "fake-server.com:25565",  # Should fail - non-existent
    "192.168.999.999:25565",  # Should fail - invalid IP
    "127.0.0.1:9999"  # Should fail - unreachable port
]

class RealMinecraftConnectionTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.test_user_id = None
        self.test_accounts = []
        
    async def setup_session(self):
        """Setup HTTP session and authentication"""
        self.session = aiohttp.ClientSession()
        
        # Setup admin user for testing
        admin_data = {
            "username": "testadmin_real",
            "password": "testpass123"
        }
        
        try:
            # Try to setup admin
            async with self.session.post(f"{BACKEND_URL}/auth/setup-admin", json=admin_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.auth_token = data["access_token"]
                    self.test_user_id = data["user"]["id"]
                    logger.info("✅ Admin setup successful")
                elif resp.status == 400:
                    # Admin exists, try login
                    async with self.session.post(f"{BACKEND_URL}/auth/login", json=admin_data) as login_resp:
                        if login_resp.status == 200:
                            data = await login_resp.json()
                            self.auth_token = data["access_token"]
                            self.test_user_id = data["user"]["id"]
                            logger.info("✅ Admin login successful")
                        else:
                            raise Exception("Failed to login as admin")
                else:
                    raise Exception(f"Failed to setup admin: {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ Authentication setup failed: {e}")
            raise
    
    async def create_test_account(self, server_ip: str) -> str:
        """Create a cracked test account for real connection testing"""
        account_data = {
            "account_type": "cracked",
            "nickname": f"RealTestBot_{int(time.time())}"
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            async with self.session.post(f"{BACKEND_URL}/accounts", json=account_data, headers=headers) as resp:
                if resp.status == 200:
                    account = await resp.json()
                    account_id = account["id"]
                    self.test_accounts.append(account_id)
                    logger.info(f"✅ Created test account: {account['nickname']} (ID: {account_id})")
                    return account_id
                else:
                    error_text = await resp.text()
                    raise Exception(f"Failed to create account: {resp.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"❌ Account creation failed: {e}")
            raise
    
    async def setup_server_settings(self, server_ip: str):
        """Configure server settings for testing"""
        settings_data = {
            "server_ip": server_ip,
            "login_delay": 2,
            "offline_accounts_enabled": True,
            "anti_afk_enabled": False,
            "auto_connect_enabled": False
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            async with self.session.put(f"{BACKEND_URL}/server-settings", json=settings_data, headers=headers) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Server settings configured for {server_ip}")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Failed to configure server settings: {resp.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Server settings configuration failed: {e}")
            return False
    
    async def test_real_connection(self, server_ip: str) -> dict:
        """Test REAL connection to a Minecraft server"""
        logger.info(f"\n🔍 TESTING REAL CONNECTION TO: {server_ip}")
        
        test_result = {
            "server": server_ip,
            "connection_attempted": False,
            "connection_successful": False,
            "proper_error_handling": False,
            "backend_logs_show_real_attempt": False,
            "no_fake_success": True,
            "error_message": None,
            "response_time": 0
        }
        
        try:
            # Setup server settings
            if not await self.setup_server_settings(server_ip):
                test_result["error_message"] = "Failed to configure server settings"
                return test_result
            
            # Create test account
            account_id = await self.create_test_account(server_ip)
            
            # Attempt REAL connection
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            start_time = time.time()
            
            logger.info(f"🚀 Attempting REAL connection to {server_ip}...")
            
            async with self.session.post(f"{BACKEND_URL}/accounts/{account_id}/connect", headers=headers) as resp:
                end_time = time.time()
                test_result["response_time"] = end_time - start_time
                test_result["connection_attempted"] = True
                
                response_text = await resp.text()
                
                if resp.status == 200:
                    response_data = await resp.json() if response_text else {}
                    test_result["connection_successful"] = True
                    
                    # Check for fake success indicators
                    if "simulation" in response_text.lower() or "fake" in response_text.lower():
                        test_result["no_fake_success"] = False
                        test_result["error_message"] = "Response contains simulation/fake indicators"
                    
                    logger.info(f"✅ Connection response: {response_data}")
                    
                elif resp.status == 500:
                    # Expected for unreachable servers - this is GOOD (real error handling)
                    test_result["proper_error_handling"] = True
                    test_result["error_message"] = response_text
                    logger.info(f"✅ Proper error handling for unreachable server: {resp.status}")
                    
                else:
                    test_result["error_message"] = f"Unexpected status {resp.status}: {response_text}"
                    logger.warning(f"⚠️ Unexpected response: {resp.status} - {response_text}")
            
            # Check backend logs for real connection attempts
            await self.check_backend_logs_for_real_attempts(server_ip, test_result)
            
            # Wait a moment then disconnect
            await asyncio.sleep(2)
            await self.disconnect_account(account_id)
            
        except Exception as e:
            test_result["error_message"] = str(e)
            logger.error(f"❌ Connection test failed: {e}")
        
        return test_result
    
    async def check_backend_logs_for_real_attempts(self, server_ip: str, test_result: dict):
        """Check backend logs to verify real connection attempts"""
        try:
            # Check supervisor backend logs
            log_files = [
                "/var/log/supervisor/backend.out.log",
                "/var/log/supervisor/backend.err.log"
            ]
            
            real_attempt_indicators = [
                "REAL CONNECTION ATTEMPT",
                "ATTEMPTING REAL MINECRAFT PROTOCOL CONNECTION",
                "REAL CONNECTION ERROR",
                "REAL CONNECTION FAILED",
                "REAL CONNECTION SUCCESS",
                f"to Minecraft server {server_ip.split(':')[0]}",
                "ConnectionRefusedError",
                "minecraft.networking.connection"
            ]
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        # Get recent log entries
                        result = subprocess.run(
                            ["tail", "-n", "50", log_file], 
                            capture_output=True, 
                            text=True, 
                            timeout=5
                        )
                        
                        log_content = result.stdout.lower()
                        
                        # Check for real connection attempt indicators
                        for indicator in real_attempt_indicators:
                            if indicator.lower() in log_content:
                                test_result["backend_logs_show_real_attempt"] = True
                                logger.info(f"✅ Found real connection attempt in logs: {indicator}")
                                break
                                
                    except Exception as e:
                        logger.warning(f"Could not read log file {log_file}: {e}")
            
            if not test_result["backend_logs_show_real_attempt"]:
                logger.warning("⚠️ No clear evidence of real connection attempts in backend logs")
                
        except Exception as e:
            logger.error(f"Error checking backend logs: {e}")
    
    async def disconnect_account(self, account_id: str):
        """Disconnect test account"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            async with self.session.post(f"{BACKEND_URL}/accounts/{account_id}/disconnect", headers=headers) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Account {account_id} disconnected")
                else:
                    logger.warning(f"⚠️ Disconnect response: {resp.status}")
        except Exception as e:
            logger.error(f"Error disconnecting account: {e}")
    
    async def cleanup_test_accounts(self):
        """Clean up test accounts"""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        for account_id in self.test_accounts:
            try:
                async with self.session.delete(f"{BACKEND_URL}/accounts/{account_id}", headers=headers) as resp:
                    if resp.status == 200:
                        logger.info(f"✅ Cleaned up test account {account_id}")
                    else:
                        logger.warning(f"⚠️ Cleanup response for {account_id}: {resp.status}")
            except Exception as e:
                logger.error(f"Error cleaning up account {account_id}: {e}")
    
    async def run_comprehensive_test(self):
        """Run comprehensive real connection tests"""
        logger.info("🚀 STARTING REAL MINECRAFT CONNECTION TESTS")
        logger.info("=" * 60)
        
        try:
            await self.setup_session()
            
            # Test each server
            for server_ip in PUBLIC_SERVERS:
                test_result = await self.test_real_connection(server_ip)
                TEST_RESULTS.append(test_result)
                
                # Brief pause between tests
                await asyncio.sleep(3)
            
            # Generate comprehensive report
            await self.generate_test_report()
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            raise
        finally:
            await self.cleanup_test_accounts()
            if self.session:
                await self.session.close()
    
    async def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 REAL MINECRAFT CONNECTION TEST REPORT")
        logger.info("=" * 60)
        
        total_tests = len(TEST_RESULTS)
        successful_connections = sum(1 for r in TEST_RESULTS if r["connection_successful"])
        proper_error_handling = sum(1 for r in TEST_RESULTS if r["proper_error_handling"])
        real_attempts_detected = sum(1 for r in TEST_RESULTS if r["backend_logs_show_real_attempt"])
        no_fake_operations = sum(1 for r in TEST_RESULTS if r["no_fake_success"])
        
        logger.info(f"📈 SUMMARY:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Successful Connections: {successful_connections}")
        logger.info(f"   Proper Error Handling: {proper_error_handling}")
        logger.info(f"   Real Attempts Detected: {real_attempts_detected}")
        logger.info(f"   No Fake Operations: {no_fake_operations}")
        
        logger.info(f"\n📋 DETAILED RESULTS:")
        
        for result in TEST_RESULTS:
            status = "✅ PASS" if (result["connection_successful"] or result["proper_error_handling"]) else "❌ FAIL"
            logger.info(f"\n🎯 {result['server']}: {status}")
            logger.info(f"   Connection Attempted: {'✅' if result['connection_attempted'] else '❌'}")
            logger.info(f"   Connection Successful: {'✅' if result['connection_successful'] else '❌'}")
            logger.info(f"   Proper Error Handling: {'✅' if result['proper_error_handling'] else '❌'}")
            logger.info(f"   Real Attempts in Logs: {'✅' if result['backend_logs_show_real_attempt'] else '❌'}")
            logger.info(f"   No Fake Operations: {'✅' if result['no_fake_success'] else '❌'}")
            logger.info(f"   Response Time: {result['response_time']:.2f}s")
            
            if result["error_message"]:
                logger.info(f"   Error: {result['error_message']}")
        
        # Final assessment
        logger.info(f"\n🎯 FINAL ASSESSMENT:")
        
        if real_attempts_detected > 0:
            logger.info("✅ REAL CONNECTION ATTEMPTS DETECTED - System is making actual Minecraft protocol connections")
        else:
            logger.info("❌ NO REAL CONNECTION ATTEMPTS DETECTED - System may still be using fake operations")
        
        if no_fake_operations == total_tests:
            logger.info("✅ NO FAKE OPERATIONS DETECTED - All responses appear genuine")
        else:
            logger.info("❌ FAKE OPERATIONS DETECTED - Some responses contain simulation indicators")
        
        if proper_error_handling > 0:
            logger.info("✅ PROPER ERROR HANDLING - System correctly handles unreachable servers")
        else:
            logger.info("❌ POOR ERROR HANDLING - System may not be handling connection failures properly")
        
        logger.info("=" * 60)

async def main():
    """Main test execution"""
    tester = RealMinecraftConnectionTester()
    
    try:
        await tester.run_comprehensive_test()
        logger.info("🎉 REAL MINECRAFT CONNECTION TESTS COMPLETED")
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)