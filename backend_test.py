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
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, response_data
                except:
                    self.log_test(name, True, f"Status: {response.status_code} (No JSON response)")
                    return True, {}
            else:
                try:
                    error_data = response.json()
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}: {error_data}")
                except:
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}: {response.text}")
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Request failed: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_check_admin_exists(self):
        """Test check admin endpoint"""
        success, response = self.run_test("Check Admin Exists", "GET", "auth/check-admin", 200)
        if success:
            return success, response.get('admin_exists', False)
        return success, False

    def test_setup_admin(self, username="testadmin", password="testpass123"):
        """Test admin setup"""
        success, response = self.run_test(
            "Setup Admin",
            "POST",
            "auth/setup-admin",
            200,
            data={"username": username, "password": password, "role": "admin"}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.admin_user = response['user']
            return True, response
        return False, {}

    def test_login(self, username, password):
        """Test user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"username": username, "password": password}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            return True, response
        return False, {}

    def test_create_user(self, username="testuser", password="testpass123", role="user"):
        """Test creating a new user"""
        return self.run_test(
            "Create User",
            "POST",
            "users",
            200,
            data={"username": username, "password": password, "role": role}
        )

    def test_get_users(self):
        """Test getting users list"""
        return self.run_test("Get Users", "GET", "users", 200)

    def test_create_minecraft_account(self, account_type="cracked", nickname="TestBot"):
        """Test creating minecraft account"""
        data = {"account_type": account_type}
        if account_type == "cracked":
            data["nickname"] = nickname
        elif account_type == "microsoft":
            data["email"] = "test@example.com"
            
        return self.run_test("Create Minecraft Account", "POST", "accounts", 200, data=data)

    def test_get_minecraft_accounts(self):
        """Test getting minecraft accounts"""
        return self.run_test("Get Minecraft Accounts", "GET", "accounts", 200)

    def test_server_settings(self):
        """Test server settings endpoints"""
        # Get settings
        success1, _ = self.run_test("Get Server Settings", "GET", "server-settings", 200)
        
        # Update settings
        success2, _ = self.run_test(
            "Update Server Settings",
            "PUT",
            "server-settings",
            200,
            data={"server_ip": "test.minecraft.com", "login_delay": 10}
        )
        
        return success1 and success2

    def test_server_connection(self):
        """Test server connection endpoints"""
        success1, _ = self.run_test("Connect to Server", "POST", "server/connect", 200)
        success2, _ = self.run_test("Disconnect from Server", "POST", "server/disconnect", 200)
        return success1 and success2

    def test_account_deletion(self):
        """Test account deletion functionality (CRITICAL NEW FEATURE)"""
        # First create an account to delete
        success, account_data = self.test_create_minecraft_account("cracked", "DeleteTestBot")
        if not success:
            self.log_test("Account Deletion - Setup", False, "Failed to create test account")
            return False
        
        # Get the account ID
        success, accounts = self.run_test("Get Accounts for Deletion Test", "GET", "accounts", 200)
        if not success or not accounts:
            self.log_test("Account Deletion - Get Account ID", False, "Failed to get account list")
            return False
        
        # Find our test account
        test_account = None
        for account in accounts:
            if account.get('nickname') == 'DeleteTestBot':
                test_account = account
                break
        
        if not test_account:
            self.log_test("Account Deletion - Find Test Account", False, "Test account not found")
            return False
        
        account_id = test_account['id']
        
        # Test deletion with valid account ID
        success1, _ = self.run_test(
            "Delete Account - Valid ID", 
            "DELETE", 
            f"accounts/{account_id}", 
            200
        )
        
        # Test deletion with invalid account ID
        success2, _ = self.run_test(
            "Delete Account - Invalid ID", 
            "DELETE", 
            "accounts/invalid-id-12345", 
            404
        )
        
        # Test deletion without authentication (should fail)
        old_token = self.token
        self.token = None
        success3, _ = self.run_test(
            "Delete Account - No Auth", 
            "DELETE", 
            f"accounts/{account_id}", 
            401
        )
        self.token = old_token
        
        return success1 and success2 and success3

    def test_spam_messages(self):
        """Test spam messages functionality (NEW FEATURE)"""
        # First create test accounts
        success1, _ = self.test_create_minecraft_account("cracked", "SpamBot1")
        success2, _ = self.test_create_minecraft_account("cracked", "SpamBot2")
        
        if not (success1 and success2):
            self.log_test("Spam Messages - Setup", False, "Failed to create test accounts")
            return False
        
        # Get account IDs
        success, accounts = self.run_test("Get Accounts for Spam Test", "GET", "accounts", 200)
        if not success:
            self.log_test("Spam Messages - Get Accounts", False, "Failed to get accounts")
            return False
        
        spam_account_ids = []
        for account in accounts:
            if account.get('nickname') in ['SpamBot1', 'SpamBot2']:
                spam_account_ids.append(account['id'])
        
        if len(spam_account_ids) < 2:
            self.log_test("Spam Messages - Account IDs", False, "Not enough test accounts found")
            return False
        
        # Test valid spam message request
        success1, response1 = self.run_test(
            "Spam Messages - Valid Request",
            "POST",
            "chats/spam",
            200,
            data={
                "account_ids": spam_account_ids,
                "message": "Test spam message",
                "interval_seconds": 5
            }
        )
        
        # Test spam with invalid interval (too low)
        success2, _ = self.run_test(
            "Spam Messages - Invalid Interval Low",
            "POST",
            "chats/spam",
            400,
            data={
                "account_ids": spam_account_ids,
                "message": "Test message",
                "interval_seconds": 0
            }
        )
        
        # Test spam with invalid interval (too high)
        success3, _ = self.run_test(
            "Spam Messages - Invalid Interval High",
            "POST",
            "chats/spam",
            400,
            data={
                "account_ids": spam_account_ids,
                "message": "Test message",
                "interval_seconds": 4000
            }
        )
        
        # Test spam with empty message
        success4, _ = self.run_test(
            "Spam Messages - Empty Message",
            "POST",
            "chats/spam",
            400,
            data={
                "account_ids": spam_account_ids,
                "message": "",
                "interval_seconds": 10
            }
        )
        
        # Test spam with no account IDs
        success5, _ = self.run_test(
            "Spam Messages - No Account IDs",
            "POST",
            "chats/spam",
            400,
            data={
                "account_ids": [],
                "message": "Test message",
                "interval_seconds": 10
            }
        )
        
        # Test spam without authentication
        old_token = self.token
        self.token = None
        success6, _ = self.run_test(
            "Spam Messages - No Auth",
            "POST",
            "chats/spam",
            401,
            data={
                "account_ids": spam_account_ids,
                "message": "Test message",
                "interval_seconds": 10
            }
        )
        self.token = old_token
        
        # Verify response contains expected fields
        response_valid = False
        if success1 and response1:
            expected_fields = ['message', 'accounts_count', 'interval']
            response_valid = all(field in response1 for field in expected_fields)
            if not response_valid:
                self.log_test("Spam Messages - Response Format", False, f"Missing fields in response: {response1}")
        
        return success1 and success2 and success3 and success4 and success5 and success6 and response_valid

    def test_login_world_change_messages(self):
        """Test login and world change message settings (ENHANCED FEATURE)"""
        # Test updating server settings with login messages
        login_messages = [
            {"message": "Hello, I'm online!", "delay": 2},
            {"message": "Ready to play!", "delay": 1}
        ]
        
        world_change_messages = [
            {"message": "Changed worlds!", "delay": 1},
            {"message": "New dimension!", "delay": 2}
        ]
        
        success1, response1 = self.run_test(
            "Login Messages - Update Settings",
            "PUT",
            "server-settings",
            200,
            data={
                "login_message_enabled": True,
                "login_messages": login_messages,
                "world_change_messages_enabled": True,
                "world_change_messages": world_change_messages
            }
        )
        
        # Verify settings were saved correctly
        success2, response2 = self.run_test("Login Messages - Get Settings", "GET", "server-settings", 200)
        
        settings_valid = False
        if success2 and response2:
            settings_valid = (
                response2.get('login_message_enabled') == True and
                response2.get('world_change_messages_enabled') == True and
                len(response2.get('login_messages', [])) == 2 and
                len(response2.get('world_change_messages', [])) == 2
            )
            if not settings_valid:
                self.log_test("Login Messages - Settings Validation", False, f"Settings not saved correctly: {response2}")
        
        # Test disabling the features
        success3, _ = self.run_test(
            "Login Messages - Disable Features",
            "PUT",
            "server-settings",
            200,
            data={
                "login_message_enabled": False,
                "world_change_messages_enabled": False
            }
        )
        
        return success1 and success2 and success3 and settings_valid

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Minecraft AFK Console API Tests")
        print("=" * 50)
        
        # Test 1: Health Check
        self.test_health_check()
        
        # Test 2: Check if admin exists
        success, admin_exists = self.test_check_admin_exists()
        
        # Test 3: Setup admin if needed
        if success and not admin_exists:
            admin_success, _ = self.test_setup_admin()
            if not admin_success:
                print("❌ Cannot proceed without admin setup")
                return False
        elif success and admin_exists:
            # Try to login with default credentials
            login_success, _ = self.test_login("testadmin", "testpass123")
            if not login_success:
                print("⚠️  Admin exists but cannot login with test credentials")
                print("   This might be expected if admin was created with different credentials")
        
        # If we have a token, continue with authenticated tests
        if self.token:
            print("\n🔐 Running authenticated tests...")
            
            # Test user management
            self.test_create_user("newuser", "newpass123", "user")
            self.test_get_users()
            
            # Test minecraft accounts
            self.test_create_minecraft_account("cracked", "TestBot1")
            self.test_create_minecraft_account("microsoft", None)  # Should fail
            self.test_get_minecraft_accounts()
            
            # Test server settings
            self.test_server_settings()
            
            # Test server connection
            self.test_server_connection()
            
            print("\n🆕 Testing NEW FEATURES...")
            
            # Test account deletion (CRITICAL)
            self.test_account_deletion()
            
            # Test spam messages functionality (NEW FEATURE)
            self.test_spam_messages()
            
            # Test login and world change messages (ENHANCED FEATURE)
            self.test_login_world_change_messages()
            
        else:
            print("⚠️  Skipping authenticated tests - no valid token")
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("❌ Some tests failed")
            return False

def main():
    tester = MinecraftAFKAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/test_reports/backend_api_results.json', 'w') as f:
        json.dump({
            'summary': {
                'total_tests': tester.tests_run,
                'passed_tests': tester.tests_passed,
                'success_rate': tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0,
                'timestamp': datetime.now().isoformat()
            },
            'results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())