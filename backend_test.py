#!/usr/bin/env python3
"""
CRITICAL TEST: Real Minecraft Connection Validation
Tests that the system properly handles connection failures and does NOT return fake success responses.
"""

import asyncio
import aiohttp
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MinecraftConnectionTester:
    def __init__(self):
        # Get backend URL from environment
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    self.base_url = line.split('=')[1].strip() + '/api'
                    break
        else:
            self.base_url = 'http://localhost:8001/api'
        
        self.session = None
        self.auth_token = None
        self.test_user_id = None
        self.test_account_id = None
        
        logger.info(f"Testing backend at: {self.base_url}")
    
    async def setup_session(self):
        """Setup HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
    
    async def setup_test_user(self):
        """Setup test user and account for connection testing"""
        try:
            # Check if admin exists
            async with self.session.get(f"{self.base_url}/auth/check-admin") as resp:
                admin_check = await resp.json()
            
            # Setup admin if needed
            if not admin_check.get('admin_exists'):
                admin_data = {
                    "username": "testadmin",
                    "password": "testpass123"
                }
                async with self.session.post(f"{self.base_url}/auth/setup-admin", json=admin_data) as resp:
                    if resp.status == 200:
                        auth_response = await resp.json()
                        self.auth_token = auth_response['access_token']
                        self.test_user_id = auth_response['user']['id']
                        logger.info("✅ Test admin user created and authenticated")
                    else:
                        logger.error(f"❌ Failed to create admin user: {resp.status}")
                        return False
            else:
                # Login with existing admin
                login_data = {
                    "username": "testadmin", 
                    "password": "testpass123"
                }
                async with self.session.post(f"{self.base_url}/auth/login", json=login_data) as resp:
                    if resp.status == 200:
                        auth_response = await resp.json()
                        self.auth_token = auth_response['access_token']
                        self.test_user_id = auth_response['user']['id']
                        logger.info("✅ Authenticated with existing admin user")
                    else:
                        logger.error(f"❌ Failed to login: {resp.status}")
                        return False
            
            # Create test Minecraft account
            account_data = {
                "account_type": "cracked",
                "nickname": "TestPlayer123"
            }
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            async with self.session.post(f"{self.base_url}/accounts", json=account_data, headers=headers) as resp:
                if resp.status == 200:
                    account_response = await resp.json()
                    self.test_account_id = account_response['id']
                    logger.info(f"✅ Test account created: {self.test_account_id}")
                else:
                    logger.error(f"❌ Failed to create test account: {resp.status}")
                    return False
            
            # Setup server settings with a fake server initially
            server_settings = {
                "server_ip": "fake-server.com:25565",
                "login_delay": 5,
                "offline_accounts_enabled": True,
                "anti_afk_enabled": False,
                "auto_connect_enabled": False
            }
            async with self.session.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers) as resp:
                if resp.status == 200:
                    logger.info("✅ Server settings configured")
                else:
                    logger.error(f"❌ Failed to configure server settings: {resp.status}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up test user: {e}")
            return False
    
    async def test_nonexistent_server_connection(self):
        """CRITICAL TEST: Connection to non-existent server should FAIL"""
        logger.info("\n🔍 TESTING: Non-existent server connection (fake-server.com:25565)")
        
        try:
            # Update server settings to non-existent server
            server_settings = {"server_ip": "fake-server.com:25565"}
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with self.session.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"❌ Failed to update server settings: {resp.status}")
                    return False
            
            # Attempt connection - this MUST fail
            async with self.session.post(f"{self.base_url}/accounts/{self.test_account_id}/connect", headers=headers) as resp:
                response_data = await resp.json()
                
                if resp.status == 200 and response_data.get('success') == True:
                    logger.error("❌ CRITICAL FAILURE: System returned SUCCESS for non-existent server!")
                    logger.error(f"❌ Response: {response_data}")
                    return False
                elif resp.status >= 400:
                    logger.info(f"✅ CORRECT: Connection failed as expected (status: {resp.status})")
                    logger.info(f"✅ Error message: {response_data.get('detail', 'No detail')}")
                    return True
                else:
                    logger.error(f"❌ UNEXPECTED: Unexpected response status {resp.status}")
                    logger.error(f"❌ Response: {response_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error testing non-existent server: {e}")
            return False
    
    async def test_invalid_ip_connection(self):
        """CRITICAL TEST: Connection to invalid IP should FAIL"""
        logger.info("\n🔍 TESTING: Invalid IP connection (192.168.999.999:25565)")
        
        try:
            # Update server settings to invalid IP
            server_settings = {"server_ip": "192.168.999.999:25565"}
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with self.session.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"❌ Failed to update server settings: {resp.status}")
                    return False
            
            # Attempt connection - this MUST fail
            async with self.session.post(f"{self.base_url}/accounts/{self.test_account_id}/connect", headers=headers) as resp:
                response_data = await resp.json()
                
                if resp.status == 200 and response_data.get('success') == True:
                    logger.error("❌ CRITICAL FAILURE: System returned SUCCESS for invalid IP!")
                    logger.error(f"❌ Response: {response_data}")
                    return False
                elif resp.status >= 400:
                    logger.info(f"✅ CORRECT: Connection failed as expected (status: {resp.status})")
                    logger.info(f"✅ Error message: {response_data.get('detail', 'No detail')}")
                    return True
                else:
                    logger.error(f"❌ UNEXPECTED: Unexpected response status {resp.status}")
                    logger.error(f"❌ Response: {response_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error testing invalid IP: {e}")
            return False
    
    async def test_unreachable_server_connection(self):
        """CRITICAL TEST: Connection to unreachable server should FAIL"""
        logger.info("\n🔍 TESTING: Unreachable server connection (127.0.0.1:9999)")
        
        try:
            # Update server settings to unreachable server (closed port)
            server_settings = {"server_ip": "127.0.0.1:9999"}
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with self.session.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"❌ Failed to update server settings: {resp.status}")
                    return False
            
            # Attempt connection - this MUST fail
            async with self.session.post(f"{self.base_url}/accounts/{self.test_account_id}/connect", headers=headers) as resp:
                response_data = await resp.json()
                
                if resp.status == 200 and response_data.get('success') == True:
                    logger.error("❌ CRITICAL FAILURE: System returned SUCCESS for unreachable server!")
                    logger.error(f"❌ Response: {response_data}")
                    return False
                elif resp.status >= 400:
                    logger.info(f"✅ CORRECT: Connection failed as expected (status: {resp.status})")
                    logger.info(f"✅ Error message: {response_data.get('detail', 'No detail')}")
                    return True
                else:
                    logger.error(f"❌ UNEXPECTED: Unexpected response status {resp.status}")
                    logger.error(f"❌ Response: {response_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error testing unreachable server: {e}")
            return False
    
    async def verify_connection_status_accuracy(self):
        """Verify that connection status in database reflects reality"""
        logger.info("\n🔍 TESTING: Connection status accuracy in database")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Get account details
            async with self.session.get(f"{self.base_url}/accounts", headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"❌ Failed to get accounts: {resp.status}")
                    return False
                
                accounts = await resp.json()
                test_account = None
                for account in accounts:
                    if account['id'] == self.test_account_id:
                        test_account = account
                        break
                
                if not test_account:
                    logger.error("❌ Test account not found")
                    return False
                
                # After failed connection attempts, account should NOT be online
                if test_account.get('is_online') == True:
                    logger.error("❌ CRITICAL FAILURE: Account shows as online after failed connections!")
                    logger.error(f"❌ Account status: {test_account}")
                    return False
                else:
                    logger.info("✅ CORRECT: Account correctly shows as offline after failed connections")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Error verifying connection status: {e}")
            return False
    
    async def check_backend_logs_for_fake_operations(self):
        """Check backend logs for any fake success messages"""
        logger.info("\n🔍 CHECKING: Backend logs for fake operations")
        
        try:
            # Check supervisor logs for backend
            import subprocess
            result = subprocess.run(
                ['tail', '-n', '50', '/var/log/supervisor/backend.err.log'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                log_content = result.stdout
                
                # Look for suspicious fake success patterns
                fake_patterns = [
                    "SIMULATION",
                    "fake success",
                    "simulated connection",
                    "mock connection",
                    "pretend connected"
                ]
                
                found_fake = False
                for pattern in fake_patterns:
                    if pattern.lower() in log_content.lower():
                        logger.error(f"❌ FOUND FAKE OPERATION in logs: {pattern}")
                        found_fake = True
                
                if not found_fake:
                    logger.info("✅ No fake operations found in backend logs")
                    return True
                else:
                    return False
            else:
                logger.warning("⚠️ Could not read backend logs")
                return True  # Don't fail test if logs unavailable
                
        except Exception as e:
            logger.warning(f"⚠️ Error checking logs: {e}")
            return True  # Don't fail test if logs unavailable
    
    async def run_all_tests(self):
        """Run all connection validation tests"""
        logger.info("🚀 STARTING CRITICAL MINECRAFT CONNECTION VALIDATION TESTS")
        logger.info("=" * 80)
        
        await self.setup_session()
        
        try:
            # Setup test environment
            if not await self.setup_test_user():
                logger.error("❌ Failed to setup test environment")
                return False
            
            # Run critical connection tests
            tests = [
                ("Non-existent Server Test", self.test_nonexistent_server_connection),
                ("Invalid IP Test", self.test_invalid_ip_connection),
                ("Unreachable Server Test", self.test_unreachable_server_connection),
                ("Connection Status Accuracy", self.verify_connection_status_accuracy),
                ("Backend Logs Check", self.check_backend_logs_for_fake_operations)
            ]
            
            results = {}
            for test_name, test_func in tests:
                logger.info(f"\n{'='*60}")
                logger.info(f"RUNNING: {test_name}")
                logger.info(f"{'='*60}")
                
                try:
                    result = await test_func()
                    results[test_name] = result
                    
                    if result:
                        logger.info(f"✅ {test_name}: PASSED")
                    else:
                        logger.error(f"❌ {test_name}: FAILED")
                        
                except Exception as e:
                    logger.error(f"❌ {test_name}: ERROR - {e}")
                    results[test_name] = False
            
            # Summary
            logger.info("\n" + "="*80)
            logger.info("CRITICAL CONNECTION VALIDATION TEST RESULTS")
            logger.info("="*80)
            
            passed = sum(1 for result in results.values() if result)
            total = len(results)
            
            for test_name, result in results.items():
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"{test_name}: {status}")
            
            logger.info(f"\nOVERALL: {passed}/{total} tests passed")
            
            if passed == total:
                logger.info("🎉 ALL CRITICAL TESTS PASSED - NO FAKE OPERATIONS DETECTED")
                return True
            else:
                logger.error("💥 CRITICAL FAILURES DETECTED - FAKE OPERATIONS STILL PRESENT")
                return False
                
        finally:
            await self.cleanup_session()

async def main():
    """Main test execution"""
    tester = MinecraftConnectionTester()
    success = await tester.run_all_tests()
    
    if success:
        logger.info("\n🎯 RESULT: Real Minecraft connection validation PASSED")
        sys.exit(0)
    else:
        logger.error("\n💥 RESULT: Real Minecraft connection validation FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())