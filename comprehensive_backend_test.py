import requests
import sys
import json
import time
from datetime import datetime

class ComprehensiveMinecraftAPITester:
    def __init__(self, base_url="https://afkcraft-console.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_token = None
        self.user_token = None
        self.admin_user = None
        self.regular_user = None
        self.test_account_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}: {details}")

    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        """Make HTTP request with proper error handling"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text}
                
            return success, response.status_code, response_data

        except Exception as e:
            return False, 0, {"error": str(e)}

    def test_authentication_flow(self):
        """Test complete authentication flow"""
        print("\n🔐 Testing Authentication Flow...")
        
        # Reset demo first
        success, status, _ = self.make_request('POST', 'demo/reset')
        self.log_test("Demo Reset", success, f"Status: {status}")
        
        # Setup admin
        success, status, response = self.make_request(
            'POST', 'auth/setup-admin', 
            {"username": "testadmin", "password": "testpass123", "role": "admin"}
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            self.admin_user = response['user']
            self.log_test("Admin Setup", True, f"Admin created: {self.admin_user['username']}")
        else:
            self.log_test("Admin Setup", False, f"Status: {status}, Response: {response}")
            return False
        
        # Test admin login
        success, status, response = self.make_request(
            'POST', 'auth/login',
            {"username": "testadmin", "password": "testpass123"}
        )
        
        if success and 'access_token' in response:
            self.log_test("Admin Login", True, f"Login successful")
        else:
            self.log_test("Admin Login", False, f"Status: {status}")
            
        return True

    def test_user_management(self):
        """Test user management with role-based access"""
        print("\n👥 Testing User Management...")
        
        # Create regular user as admin
        success, status, response = self.make_request(
            'POST', 'users',
            {"username": "testuser", "password": "userpass123", "role": "user"},
            token=self.admin_token
        )
        self.log_test("Create Regular User", success, f"Status: {status}")
        
        # Create moderator user as admin
        success, status, response = self.make_request(
            'POST', 'users',
            {"username": "testmod", "password": "modpass123", "role": "moderator"},
            token=self.admin_token
        )
        self.log_test("Create Moderator User", success, f"Status: {status}")
        
        # Get users list as admin
        success, status, response = self.make_request('GET', 'users', token=self.admin_token)
        if success:
            user_count = len(response)
            self.log_test("Get Users (Admin)", True, f"Found {user_count} users")
        else:
            self.log_test("Get Users (Admin)", False, f"Status: {status}")
        
        # Login as regular user
        success, status, response = self.make_request(
            'POST', 'auth/login',
            {"username": "testuser", "password": "userpass123"}
        )
        
        if success and 'access_token' in response:
            self.user_token = response['access_token']
            self.regular_user = response['user']
            self.log_test("User Login", True, f"User logged in: {self.regular_user['username']}")
        else:
            self.log_test("User Login", False, f"Status: {status}")
        
        # Test role-based access - regular user trying to get users list (should fail)
        success, status, response = self.make_request('GET', 'users', token=self.user_token, expected_status=403)
        self.log_test("Role-based Access Control", success, f"User correctly denied access: {status}")

    def test_minecraft_account_management(self):
        """Test individual Minecraft account management"""
        print("\n🎮 Testing Minecraft Account Management...")
        
        # Create cracked account
        success, status, response = self.make_request(
            'POST', 'accounts',
            {"account_type": "cracked", "nickname": "TestBot1"},
            token=self.user_token
        )
        
        if success and 'id' in response:
            self.test_account_id = response['id']
            self.log_test("Create Cracked Account", True, f"Account ID: {self.test_account_id}")
        else:
            self.log_test("Create Cracked Account", False, f"Status: {status}")
            return False
        
        # Create Microsoft account (should require email)
        success, status, response = self.make_request(
            'POST', 'accounts',
            {"account_type": "microsoft", "email": "test@example.com"},
            token=self.user_token
        )
        self.log_test("Create Microsoft Account", success, f"Status: {status}")
        
        # Get accounts list
        success, status, response = self.make_request('GET', 'accounts', token=self.user_token)
        if success:
            account_count = len(response)
            self.log_test("Get Accounts", True, f"Found {account_count} accounts")
        else:
            self.log_test("Get Accounts", False, f"Status: {status}")
        
        # Test individual account actions
        if self.test_account_id:
            # Connect account
            success, status, response = self.make_request(
                'POST', f'accounts/{self.test_account_id}/connect',
                token=self.user_token
            )
            self.log_test("Connect Account", success, f"Status: {status}")
            
            # Clear inventory (should work when connected)
            success, status, response = self.make_request(
                'POST', f'accounts/{self.test_account_id}/clear-inventory',
                token=self.user_token
            )
            self.log_test("Clear Inventory", success, f"Status: {status}")
            
            # Disconnect account
            success, status, response = self.make_request(
                'POST', f'accounts/{self.test_account_id}/disconnect',
                token=self.user_token
            )
            self.log_test("Disconnect Account", success, f"Status: {status}")
            
            # Try to clear inventory when disconnected (should fail)
            success, status, response = self.make_request(
                'POST', f'accounts/{self.test_account_id}/clear-inventory',
                token=self.user_token, expected_status=400
            )
            self.log_test("Clear Inventory (Offline)", success, f"Correctly failed: {status}")
            
            # Delete account
            success, status, response = self.make_request(
                'DELETE', f'accounts/{self.test_account_id}',
                token=self.user_token
            )
            self.log_test("Delete Account", success, f"Status: {status}")

    def test_chat_functionality(self):
        """Test chat messaging functionality"""
        print("\n💬 Testing Chat Functionality...")
        
        # First create an account for chat testing
        success, status, response = self.make_request(
            'POST', 'accounts',
            {"account_type": "cracked", "nickname": "ChatBot"},
            token=self.user_token
        )
        
        if success and 'id' in response:
            chat_account_id = response['id']
            
            # Send message
            success, status, response = self.make_request(
                'POST', 'chats/send',
                {"account_ids": [chat_account_id], "message": "Hello from test!"},
                token=self.user_token
            )
            self.log_test("Send Chat Message", success, f"Status: {status}")
            
            # Get chat messages
            success, status, response = self.make_request('GET', 'chats', token=self.user_token)
            if success:
                message_count = len(response)
                self.log_test("Get Chat Messages", True, f"Found {message_count} messages")
            else:
                self.log_test("Get Chat Messages", False, f"Status: {status}")
        else:
            self.log_test("Create Chat Account", False, f"Status: {status}")

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        print("\n📊 Testing Dashboard Statistics...")
        
        # Test as admin (should have access)
        success, status, response = self.make_request('GET', 'dashboard/stats', token=self.admin_token)
        if success:
            stats = response
            self.log_test("Dashboard Stats (Admin)", True, 
                         f"Active: {stats.get('active_accounts', 0)}, Total: {stats.get('total_accounts', 0)}")
        else:
            self.log_test("Dashboard Stats (Admin)", False, f"Status: {status}")
        
        # Test as regular user (should be denied)
        success, status, response = self.make_request('GET', 'dashboard/stats', token=self.user_token, expected_status=403)
        self.log_test("Dashboard Stats (User)", success, f"User correctly denied access: {status}")

    def test_server_settings(self):
        """Test server settings management"""
        print("\n⚙️ Testing Server Settings...")
        
        # Get default settings
        success, status, response = self.make_request('GET', 'server-settings', token=self.user_token)
        self.log_test("Get Server Settings", success, f"Status: {status}")
        
        # Update settings
        settings_update = {
            "server_ip": "test.minecraft.com",
            "login_delay": 10,
            "anti_afk_enabled": True,
            "auto_connect_enabled": True,
            "login_message_enabled": True,
            "login_messages": [{"message": "Hello!", "delay": 5}]
        }
        
        success, status, response = self.make_request(
            'PUT', 'server-settings',
            settings_update,
            token=self.user_token
        )
        self.log_test("Update Server Settings", success, f"Status: {status}")

    def test_server_connection(self):
        """Test server connection functionality"""
        print("\n🔌 Testing Server Connection...")
        
        # Connect to server
        success, status, response = self.make_request('POST', 'server/connect', token=self.user_token)
        self.log_test("Server Connect", success, f"Status: {status}")
        
        # Disconnect from server
        success, status, response = self.make_request('POST', 'server/disconnect', token=self.user_token)
        self.log_test("Server Disconnect", success, f"Status: {status}")

    def test_error_handling(self):
        """Test API error handling"""
        print("\n🚨 Testing Error Handling...")
        
        # Test invalid login
        success, status, response = self.make_request(
            'POST', 'auth/login',
            {"username": "invalid", "password": "invalid"},
            expected_status=401
        )
        self.log_test("Invalid Login", success, f"Correctly returned 401: {status}")
        
        # Test unauthorized access
        success, status, response = self.make_request('GET', 'users', expected_status=401)
        self.log_test("Unauthorized Access", success, f"Correctly returned 401: {status}")
        
        # Test invalid account creation
        success, status, response = self.make_request(
            'POST', 'accounts',
            {"account_type": "cracked"},  # Missing nickname
            token=self.user_token,
            expected_status=400
        )
        self.log_test("Invalid Account Creation", success, f"Correctly returned 400: {status}")

    def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive Minecraft AFK Console API Tests")
        print("=" * 60)
        
        # Run test suites
        if not self.test_authentication_flow():
            print("❌ Authentication failed, stopping tests")
            return False
        
        self.test_user_management()
        self.test_minecraft_account_management()
        self.test_chat_functionality()
        self.test_dashboard_stats()
        self.test_server_settings()
        self.test_server_connection()
        self.test_error_handling()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Comprehensive Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All comprehensive tests passed!")
            return True
        else:
            print("❌ Some tests failed")
            return False

def main():
    tester = ComprehensiveMinecraftAPITester()
    success = tester.run_comprehensive_tests()
    
    # Save detailed results
    with open('/app/test_reports/comprehensive_backend_results.json', 'w') as f:
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