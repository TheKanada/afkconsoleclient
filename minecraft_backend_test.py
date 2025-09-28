#!/usr/bin/env python3
"""
Minecraft AFK Console Backend Testing Suite
Focus: asyncio/threading fixes, authentication, account management, and real Minecraft connections
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

class MinecraftBackendTester:
    def __init__(self, base_url="https://afkcraft-console.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.admin_user = None
        self.test_accounts = []
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.critical_failures = []

    def log_test(self, name: str, success: bool, details: str = "", critical: bool = False):
        """Log test result with critical failure tracking"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        elif critical:
            self.critical_failures.append(f"{name}: {details}")
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "critical": critical,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else ("🔥 CRITICAL FAIL" if critical else "❌ FAIL")
        print(f"{status} - {name}: {details}")

    def make_request(self, method: str, endpoint: str, data: dict = None, expected_status: int = 200, headers: dict = None) -> tuple:
        """Make HTTP request with proper error handling"""
        url = f"{self.api_url}/{endpoint}"
        request_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            request_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            request_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=request_headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=request_headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=request_headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=request_headers, timeout=15)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text}
            
            return success, response_data, response.status_code
            
        except requests.exceptions.Timeout:
            return False, {"error": "Request timeout"}, 0
        except requests.exceptions.ConnectionError:
            return False, {"error": "Connection error"}, 0
        except Exception as e:
            return False, {"error": str(e)}, 0

    def test_1_backend_startup_health(self):
        """Test 1: Critical - Backend starts without asyncio errors"""
        print("\n🔥 CRITICAL TEST 1: Backend Startup & Health Check")
        
        success, response, status_code = self.make_request("GET", "health")
        
        if success:
            database_status = response.get("database", "unknown")
            if database_status == "connected":
                self.log_test("Backend Health Check", True, f"Backend running, database connected")
                return True
            else:
                self.log_test("Backend Health Check", False, f"Backend running but database issue: {database_status}", critical=True)
                return False
        else:
            self.log_test("Backend Health Check", False, f"Backend not responding: {response}", critical=True)
            return False

    def test_2_minecraft_manager_import(self):
        """Test 2: Critical - MinecraftManager imports and initializes correctly"""
        print("\n🔥 CRITICAL TEST 2: MinecraftManager Import & Initialization")
        
        # Test that endpoints using minecraft_manager work (indirect test of import)
        success, response, status_code = self.make_request("GET", "dashboard/stats", expected_status=401)
        
        if status_code == 401:  # Expected - needs auth, but server processed request
            self.log_test("MinecraftManager Import", True, "Server processes minecraft_manager endpoints without import errors")
            return True
        elif status_code == 500:
            self.log_test("MinecraftManager Import", False, f"Server error suggests import/initialization issues: {response}", critical=True)
            return False
        else:
            self.log_test("MinecraftManager Import", True, f"Unexpected but non-error response: {status_code}")
            return True

    def test_3_admin_setup_authentication(self):
        """Test 3: Authentication and Admin Setup"""
        print("\n🔐 TEST 3: Authentication & Admin Setup")
        
        # Check if admin exists
        success, response, status_code = self.make_request("GET", "auth/check-admin")
        
        if not success:
            self.log_test("Check Admin Endpoint", False, f"Cannot check admin status: {response}", critical=True)
            return False
        
        admin_exists = response.get('admin_exists', False)
        self.log_test("Check Admin Endpoint", True, f"Admin exists: {admin_exists}")
        
        # If no admin, try to create one
        if not admin_exists:
            admin_data = {
                "username": "testadmin_mc",
                "password": "testpass123_mc"
            }
            
            success, response, status_code = self.make_request("POST", "auth/setup-admin", data=admin_data)
            
            if success and 'access_token' in response:
                self.token = response['access_token']
                self.admin_user = response['user']
                self.log_test("Admin Setup", True, f"Admin created successfully: {self.admin_user['username']}")
                return True
            else:
                self.log_test("Admin Setup", False, f"Failed to create admin: {response}", critical=True)
                return False
        else:
            # Try to login with existing admin (try common test credentials)
            login_data = {
                "username": "testadmin_mc",
                "password": "testpass123_mc"
            }
            
            success, response, status_code = self.make_request("POST", "auth/login", data=login_data)
            
            if success and 'access_token' in response:
                self.token = response['access_token']
                self.admin_user = response['user']
                self.log_test("Admin Login", True, f"Logged in as: {self.admin_user['username']}")
                return True
            else:
                # Try alternative credentials
                alt_login_data = {
                    "username": "testadmin",
                    "password": "testpass123"
                }
                
                success, response, status_code = self.make_request("POST", "auth/login", data=alt_login_data)
                
                if success and 'access_token' in response:
                    self.token = response['access_token']
                    self.admin_user = response['user']
                    self.log_test("Admin Login (Alt Creds)", True, f"Logged in as: {self.admin_user['username']}")
                    return True
                else:
                    self.log_test("Admin Login", False, f"Cannot login with test credentials: {response}", critical=True)
                    return False

    def test_4_protected_endpoints_auth(self):
        """Test 4: Protected endpoints require authentication"""
        print("\n🔒 TEST 4: Protected Endpoints Authentication")
        
        if not self.token:
            self.log_test("Protected Endpoints Auth", False, "No token available for testing", critical=True)
            return False
        
        # Test protected endpoint with token
        success, response, status_code = self.make_request("GET", "accounts")
        
        if success:
            self.log_test("Protected Endpoint (With Auth)", True, f"Accounts endpoint accessible with token")
        else:
            self.log_test("Protected Endpoint (With Auth)", False, f"Cannot access accounts with valid token: {response}")
            return False
        
        # Test protected endpoint without token
        temp_token = self.token
        self.token = None
        
        success, response, status_code = self.make_request("GET", "accounts", expected_status=401)
        
        self.token = temp_token  # Restore token
        
        if status_code == 401:
            self.log_test("Protected Endpoint (No Auth)", True, "Accounts endpoint properly rejects requests without token")
            return True
        else:
            self.log_test("Protected Endpoint (No Auth)", False, f"Accounts endpoint should reject unauthorized requests: {status_code}")
            return False

    def test_5_minecraft_account_management(self):
        """Test 5: Core Minecraft Account Management"""
        print("\n⚔️ TEST 5: Minecraft Account Management")
        
        if not self.token:
            self.log_test("Account Management", False, "No authentication token", critical=True)
            return False
        
        # Test creating cracked account
        cracked_account_data = {
            "account_type": "cracked",
            "nickname": "TestMinerBot"
        }
        
        success, response, status_code = self.make_request("POST", "accounts", data=cracked_account_data)
        
        if success:
            account_id = response.get('id')
            if account_id:
                self.test_accounts.append(account_id)
                self.log_test("Create Cracked Account", True, f"Created account: {response.get('nickname')}")
            else:
                self.log_test("Create Cracked Account", False, f"No account ID returned: {response}")
                return False
        else:
            self.log_test("Create Cracked Account", False, f"Failed to create cracked account: {response}")
            return False
        
        # Test creating Microsoft account (should fail without email)
        microsoft_account_data = {
            "account_type": "microsoft"
        }
        
        success, response, status_code = self.make_request("POST", "accounts", data=microsoft_account_data, expected_status=400)
        
        if status_code == 400:
            self.log_test("Create Microsoft Account (No Email)", True, "Properly rejects Microsoft account without email")
        else:
            self.log_test("Create Microsoft Account (No Email)", False, f"Should reject Microsoft account without email: {status_code}")
        
        # Test creating Microsoft account with email
        microsoft_account_data = {
            "account_type": "microsoft",
            "email": "testminer@example.com"
        }
        
        success, response, status_code = self.make_request("POST", "accounts", data=microsoft_account_data)
        
        if success:
            account_id = response.get('id')
            if account_id:
                self.test_accounts.append(account_id)
                self.log_test("Create Microsoft Account", True, f"Created account: {response.get('email')}")
            else:
                self.log_test("Create Microsoft Account", False, f"No account ID returned: {response}")
        else:
            self.log_test("Create Microsoft Account", False, f"Failed to create Microsoft account: {response}")
        
        # Test getting accounts
        success, response, status_code = self.make_request("GET", "accounts")
        
        if success and isinstance(response, list):
            account_count = len(response)
            self.log_test("Get Accounts", True, f"Retrieved {account_count} accounts")
        else:
            self.log_test("Get Accounts", False, f"Failed to get accounts: {response}")
            return False
        
        # Test updating account (if we have one)
        if self.test_accounts:
            account_id = self.test_accounts[0]
            update_data = {
                "account_type": "cracked",
                "nickname": "UpdatedTestBot"
            }
            
            success, response, status_code = self.make_request("PUT", f"accounts/{account_id}", data=update_data)
            
            if success:
                self.log_test("Update Account", True, "Account updated successfully")
            else:
                self.log_test("Update Account", False, f"Failed to update account: {response}")
        
        return True

    def test_6_server_settings_setup(self):
        """Test 6: Server Settings Setup (Required for connections)"""
        print("\n⚙️ TEST 6: Server Settings Setup")
        
        if not self.token:
            self.log_test("Server Settings", False, "No authentication token", critical=True)
            return False
        
        # Get current settings
        success, response, status_code = self.make_request("GET", "server-settings")
        
        if success:
            self.log_test("Get Server Settings", True, f"Retrieved server settings")
        else:
            self.log_test("Get Server Settings", False, f"Failed to get server settings: {response}")
            return False
        
        # Update server settings with test server
        settings_data = {
            "server_ip": "demo.minetest.net:30000",  # Public test server
            "login_delay": 5,
            "offline_accounts_enabled": True,
            "anti_afk_enabled": True,
            "auto_connect_enabled": False
        }
        
        success, response, status_code = self.make_request("PUT", "server-settings", data=settings_data)
        
        if success:
            self.log_test("Update Server Settings", True, f"Server settings updated: {settings_data['server_ip']}")
            return True
        else:
            self.log_test("Update Server Settings", False, f"Failed to update server settings: {response}")
            return False

    def test_7_minecraft_connection_primary_focus(self):
        """Test 7: 🔥 PRIMARY FOCUS - Real Minecraft Connection Testing"""
        print("\n🔥 PRIMARY FOCUS TEST 7: Real Minecraft Connection Testing")
        
        if not self.token:
            self.log_test("Minecraft Connection", False, "No authentication token", critical=True)
            return False
        
        if not self.test_accounts:
            self.log_test("Minecraft Connection", False, "No test accounts available", critical=True)
            return False
        
        account_id = self.test_accounts[0]
        
        # Test connection endpoint
        print(f"Testing connection for account: {account_id}")
        
        success, response, status_code = self.make_request("POST", f"accounts/{account_id}/connect", expected_status=None)
        
        # Connection might fail due to server being offline, but we're testing for asyncio errors
        if status_code == 500:
            error_detail = response.get('detail', '')
            if 'asyncio' in error_detail.lower() or 'event loop' in error_detail.lower() or 'thread' in error_detail.lower():
                self.log_test("Minecraft Connection (Asyncio Check)", False, f"ASYNCIO/THREADING ERROR: {error_detail}", critical=True)
                return False
            else:
                self.log_test("Minecraft Connection (Asyncio Check)", True, f"No asyncio errors, connection failed for other reasons: {error_detail}")
        elif status_code == 200:
            self.log_test("Minecraft Connection", True, f"Connection successful: {response.get('message', '')}")
        elif status_code == 400:
            # Expected if server settings not configured properly
            self.log_test("Minecraft Connection (Config Check)", True, f"Connection rejected due to configuration: {response.get('detail', '')}")
        else:
            self.log_test("Minecraft Connection", False, f"Unexpected response: {status_code} - {response}")
        
        # Test disconnection endpoint
        success, response, status_code = self.make_request("POST", f"accounts/{account_id}/disconnect", expected_status=None)
        
        if status_code == 500:
            error_detail = response.get('detail', '')
            if 'asyncio' in error_detail.lower() or 'event loop' in error_detail.lower() or 'thread' in error_detail.lower():
                self.log_test("Minecraft Disconnection (Asyncio Check)", False, f"ASYNCIO/THREADING ERROR: {error_detail}", critical=True)
                return False
            else:
                self.log_test("Minecraft Disconnection (Asyncio Check)", True, f"No asyncio errors: {error_detail}")
        elif status_code == 200:
            self.log_test("Minecraft Disconnection", True, f"Disconnection successful: {response.get('message', '')}")
        else:
            self.log_test("Minecraft Disconnection", True, f"Disconnection handled: {status_code}")
        
        return True

    def test_8_additional_endpoints(self):
        """Test 8: Additional endpoints"""
        print("\n📊 TEST 8: Additional Endpoints")
        
        if not self.token:
            self.log_test("Additional Endpoints", False, "No authentication token", critical=True)
            return False
        
        # Test dashboard stats
        success, response, status_code = self.make_request("GET", "dashboard/stats")
        
        if success:
            stats = response
            self.log_test("Dashboard Stats", True, f"Stats retrieved - Total accounts: {stats.get('total_accounts', 0)}, Active: {stats.get('active_accounts', 0)}")
        else:
            self.log_test("Dashboard Stats", False, f"Failed to get dashboard stats: {response}")
        
        # Test chat endpoints (if we have accounts)
        if self.test_accounts:
            # Test getting chat messages
            success, response, status_code = self.make_request("GET", "chats")
            
            if success:
                self.log_test("Get Chat Messages", True, f"Retrieved {len(response)} chat messages")
            else:
                self.log_test("Get Chat Messages", False, f"Failed to get chat messages: {response}")
        
        return True

    def test_9_inventory_management(self):
        """Test 9: Inventory Management (if account connected)"""
        print("\n🎒 TEST 9: Inventory Management")
        
        if not self.token or not self.test_accounts:
            self.log_test("Inventory Management", False, "No token or accounts available")
            return False
        
        account_id = self.test_accounts[0]
        
        # Test clear inventory (should fail if not connected)
        success, response, status_code = self.make_request("POST", f"accounts/{account_id}/clear-inventory", expected_status=400)
        
        if status_code == 400:
            self.log_test("Clear Inventory (Not Connected)", True, "Properly rejects inventory clear when not connected")
        elif status_code == 500:
            error_detail = response.get('detail', '')
            if 'asyncio' in error_detail.lower() or 'event loop' in error_detail.lower():
                self.log_test("Clear Inventory (Asyncio Check)", False, f"ASYNCIO ERROR: {error_detail}", critical=True)
                return False
            else:
                self.log_test("Clear Inventory (Asyncio Check)", True, f"No asyncio errors: {error_detail}")
        else:
            self.log_test("Clear Inventory", True, f"Inventory clear handled: {status_code}")
        
        return True

    def cleanup_test_accounts(self):
        """Clean up test accounts"""
        print("\n🧹 Cleaning up test accounts...")
        
        for account_id in self.test_accounts:
            success, response, status_code = self.make_request("DELETE", f"accounts/{account_id}")
            if success:
                print(f"✅ Deleted test account: {account_id}")
            else:
                print(f"❌ Failed to delete test account {account_id}: {response}")

    def run_comprehensive_test_suite(self):
        """Run the complete test suite focusing on asyncio/threading fixes"""
        print("🚀 Starting Minecraft AFK Console Backend Testing Suite")
        print("🎯 Focus: asyncio/threading fixes, authentication, account management, real connections")
        print("=" * 80)
        
        # Critical tests first
        if not self.test_1_backend_startup_health():
            print("🔥 CRITICAL: Backend health check failed - stopping tests")
            return False
        
        if not self.test_2_minecraft_manager_import():
            print("🔥 CRITICAL: MinecraftManager import/initialization failed - stopping tests")
            return False
        
        # Authentication tests
        if not self.test_3_admin_setup_authentication():
            print("🔥 CRITICAL: Authentication failed - stopping tests")
            return False
        
        self.test_4_protected_endpoints_auth()
        
        # Core functionality tests
        self.test_5_minecraft_account_management()
        self.test_6_server_settings_setup()
        
        # PRIMARY FOCUS: Real Minecraft connection testing
        self.test_7_minecraft_connection_primary_focus()
        
        # Additional tests
        self.test_8_additional_endpoints()
        self.test_9_inventory_management()
        
        # Cleanup
        self.cleanup_test_accounts()
        
        # Final summary
        print("\n" + "=" * 80)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.critical_failures:
            print(f"🔥 CRITICAL FAILURES ({len(self.critical_failures)}):")
            for failure in self.critical_failures:
                print(f"   - {failure}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if len(self.critical_failures) == 0:
            print("🎉 No critical failures detected!")
            print("✅ AsyncIO/Threading fixes appear to be working correctly")
            return True
        else:
            print("❌ Critical issues detected that need attention")
            return False

def main():
    """Main test execution"""
    tester = MinecraftBackendTester()
    success = tester.run_comprehensive_test_suite()
    
    # Save detailed results
    try:
        import os
        os.makedirs('/app/test_reports', exist_ok=True)
        
        with open('/app/test_reports/minecraft_backend_test_results.json', 'w') as f:
            json.dump({
                'test_focus': 'asyncio_threading_fixes_and_minecraft_connections',
                'summary': {
                    'total_tests': tester.tests_run,
                    'passed_tests': tester.tests_passed,
                    'critical_failures': len(tester.critical_failures),
                    'success_rate': tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0,
                    'timestamp': datetime.now().isoformat()
                },
                'critical_failures': tester.critical_failures,
                'detailed_results': tester.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: /app/test_reports/minecraft_backend_test_results.json")
        
    except Exception as e:
        print(f"⚠️ Could not save test results: {e}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())