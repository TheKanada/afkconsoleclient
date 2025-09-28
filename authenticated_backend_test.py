import requests
import sys
import json
from datetime import datetime

class AuthenticatedAPITester:
    def __init__(self, base_url="https://minecraft-afk.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
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

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

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

    def test_login(self, username="testadmin", password="testpass123"):
        """Test login and get token"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"username": username, "password": password}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            return True, response
        return False, {}

    def test_authenticated_endpoints(self):
        """Test all authenticated endpoints"""
        print("\n🔐 Testing Authenticated Endpoints...")
        
        # Test user management
        self.run_test("Get Users List", "GET", "users", 200)
        self.run_test("Create New User", "POST", "users", 200, 
                     data={"username": "apitest", "password": "apitest123", "role": "user"})
        
        # Test minecraft accounts
        self.run_test("Get Minecraft Accounts", "GET", "accounts", 200)
        self.run_test("Create Cracked Account", "POST", "accounts", 200,
                     data={"account_type": "cracked", "nickname": "TestBot"})
        self.run_test("Create Microsoft Account (should fail)", "POST", "accounts", 400,
                     data={"account_type": "microsoft"})  # Missing email
        
        # Test chat functionality
        self.run_test("Get Chat Messages", "GET", "chats", 200)
        
        # Test server settings
        self.run_test("Get Server Settings", "GET", "server-settings", 200)
        self.run_test("Update Server Settings", "PUT", "server-settings", 200,
                     data={"server_ip": "test.example.com", "login_delay": 5})
        
        # Test server connection
        self.run_test("Connect to Server", "POST", "server/connect", 200)
        self.run_test("Disconnect from Server", "POST", "server/disconnect", 200)

    def run_comprehensive_test(self):
        """Run comprehensive authenticated API test"""
        print("🚀 Starting Comprehensive Authenticated API Tests")
        print("=" * 60)
        
        # Login first
        login_success, _ = self.test_login()
        if not login_success:
            print("❌ Cannot proceed without authentication")
            return False
        
        # Run all authenticated tests
        self.test_authenticated_endpoints()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 API testing successful!")
            return True
        else:
            print("⚠️  Some API issues detected")
            return False

def main():
    tester = AuthenticatedAPITester()
    success = tester.run_comprehensive_test()
    
    # Save detailed results
    with open('/app/test_reports/authenticated_api_results.json', 'w') as f:
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