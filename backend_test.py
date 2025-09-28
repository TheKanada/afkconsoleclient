import requests
import sys
import json
from datetime import datetime

class MinecraftAFKAPITester:
    def __init__(self, base_url="https://afkcraft-console.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.admin_user = None
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

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
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