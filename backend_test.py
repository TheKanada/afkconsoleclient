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