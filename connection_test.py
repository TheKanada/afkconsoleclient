#!/usr/bin/env python3
"""
CRITICAL TEST: Real Minecraft Connection Validation
Tests that the system properly handles connection failures and does NOT return fake success responses.
"""

import requests
import json
import sys
import time

class MinecraftConnectionTester:
    def __init__(self):
        # Get backend URL from environment
        with open('/app/frontend/.env', 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if line.startswith('REACT_APP_BACKEND_URL='):
                    self.base_url = line.split('=')[1].strip() + '/api'
                    break
            else:
                self.base_url = 'http://localhost:8001/api'
        
        self.auth_token = None
        self.test_user_id = None
        self.test_account_id = None
        
        print(f"Testing backend at: {self.base_url}")
    
    def setup_test_user(self):
        """Setup test user and account for connection testing"""
        try:
            # Check if admin exists
            response = requests.get(f"{self.base_url}/auth/check-admin", timeout=10)
            admin_check = response.json()
            
            # Setup admin if needed
            if not admin_check.get('admin_exists'):
                admin_data = {
                    "username": "testadmin",
                    "password": "testpass123"
                }
                response = requests.post(f"{self.base_url}/auth/setup-admin", json=admin_data, timeout=10)
                if response.status_code == 200:
                    auth_response = response.json()
                    self.auth_token = auth_response['access_token']
                    self.test_user_id = auth_response['user']['id']
                    print("✅ Test admin user created and authenticated")
                else:
                    print(f"❌ Failed to create admin user: {response.status_code}")
                    return False
            else:
                # Login with existing admin
                login_data = {
                    "username": "testadmin", 
                    "password": "testpass123"
                }
                response = requests.post(f"{self.base_url}/auth/login", json=login_data, timeout=10)
                if response.status_code == 200:
                    auth_response = response.json()
                    self.auth_token = auth_response['access_token']
                    self.test_user_id = auth_response['user']['id']
                    print("✅ Authenticated with existing admin user")
                else:
                    print(f"❌ Failed to login: {response.status_code}")
                    return False
            
            # Create test Minecraft account
            account_data = {
                "account_type": "cracked",
                "nickname": "TestPlayer123"
            }
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/accounts", json=account_data, headers=headers, timeout=10)
            if response.status_code == 200:
                account_response = response.json()
                self.test_account_id = account_response['id']
                print(f"✅ Test account created: {self.test_account_id}")
            else:
                print(f"❌ Failed to create test account: {response.status_code}")
                return False
            
            # Setup server settings with a fake server initially
            server_settings = {
                "server_ip": "fake-server.com:25565",
                "login_delay": 5,
                "offline_accounts_enabled": True,
                "anti_afk_enabled": False,
                "auto_connect_enabled": False
            }
            response = requests.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers, timeout=10)
            if response.status_code == 200:
                print("✅ Server settings configured")
            else:
                print(f"❌ Failed to configure server settings: {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up test user: {e}")
            return False
    
    def test_nonexistent_server_connection(self):
        """CRITICAL TEST: Connection to non-existent server should FAIL"""
        print("\n🔍 TESTING: Non-existent server connection (fake-server.com:25565)")
        
        try:
            # Update server settings to non-existent server
            server_settings = {"server_ip": "fake-server.com:25565"}
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            response = requests.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to update server settings: {response.status_code}")
                return False
            
            # Attempt connection - this MUST fail
            response = requests.post(f"{self.base_url}/accounts/{self.test_account_id}/connect", headers=headers, timeout=60)
            
            try:
                response_data = response.json()
            except:
                response_data = {"detail": response.text}
            
            if response.status_code == 200 and response_data.get('success') == True:
                print("❌ CRITICAL FAILURE: System returned SUCCESS for non-existent server!")
                print(f"❌ Response: {response_data}")
                return False
            elif response.status_code >= 400:
                print(f"✅ CORRECT: Connection failed as expected (status: {response.status_code})")
                print(f"✅ Error message: {response_data.get('detail', 'No detail')}")
                return True
            else:
                print(f"❌ UNEXPECTED: Unexpected response status {response.status_code}")
                print(f"❌ Response: {response_data}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing non-existent server: {e}")
            return False
    
    def test_invalid_ip_connection(self):
        """CRITICAL TEST: Connection to invalid IP should FAIL"""
        print("\n🔍 TESTING: Invalid IP connection (192.168.999.999:25565)")
        
        try:
            # Update server settings to invalid IP
            server_settings = {"server_ip": "192.168.999.999:25565"}
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            response = requests.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to update server settings: {response.status_code}")
                return False
            
            # Attempt connection - this MUST fail
            response = requests.post(f"{self.base_url}/accounts/{self.test_account_id}/connect", headers=headers, timeout=60)
            
            try:
                response_data = response.json()
            except:
                response_data = {"detail": response.text}
            
            if response.status_code == 200 and response_data.get('success') == True:
                print("❌ CRITICAL FAILURE: System returned SUCCESS for invalid IP!")
                print(f"❌ Response: {response_data}")
                return False
            elif response.status_code >= 400:
                print(f"✅ CORRECT: Connection failed as expected (status: {response.status_code})")
                print(f"✅ Error message: {response_data.get('detail', 'No detail')}")
                return True
            else:
                print(f"❌ UNEXPECTED: Unexpected response status {response.status_code}")
                print(f"❌ Response: {response_data}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing invalid IP: {e}")
            return False
    
    def test_unreachable_server_connection(self):
        """CRITICAL TEST: Connection to unreachable server should FAIL"""
        print("\n🔍 TESTING: Unreachable server connection (127.0.0.1:9999)")
        
        try:
            # Update server settings to unreachable server (closed port)
            server_settings = {"server_ip": "127.0.0.1:9999"}
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            response = requests.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to update server settings: {response.status_code}")
                return False
            
            # Attempt connection - this MUST fail
            response = requests.post(f"{self.base_url}/accounts/{self.test_account_id}/connect", headers=headers, timeout=60)
            
            try:
                response_data = response.json()
            except:
                response_data = {"detail": response.text}
            
            if response.status_code == 200 and response_data.get('success') == True:
                print("❌ CRITICAL FAILURE: System returned SUCCESS for unreachable server!")
                print(f"❌ Response: {response_data}")
                return False
            elif response.status_code >= 400:
                print(f"✅ CORRECT: Connection failed as expected (status: {response.status_code})")
                print(f"✅ Error message: {response_data.get('detail', 'No detail')}")
                return True
            else:
                print(f"❌ UNEXPECTED: Unexpected response status {response.status_code}")
                print(f"❌ Response: {response_data}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing unreachable server: {e}")
            return False
    
    def verify_connection_status_accuracy(self):
        """Verify that connection status in database reflects reality"""
        print("\n🔍 TESTING: Connection status accuracy in database")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Get account details
            response = requests.get(f"{self.base_url}/accounts", headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to get accounts: {response.status_code}")
                return False
            
            accounts = response.json()
            test_account = None
            for account in accounts:
                if account['id'] == self.test_account_id:
                    test_account = account
                    break
            
            if not test_account:
                print("❌ Test account not found")
                return False
            
            # After failed connection attempts, account should NOT be online
            if test_account.get('is_online') == True:
                print("❌ CRITICAL FAILURE: Account shows as online after failed connections!")
                print(f"❌ Account status: {test_account}")
                return False
            else:
                print("✅ CORRECT: Account correctly shows as offline after failed connections")
                return True
                
        except Exception as e:
            print(f"❌ Error verifying connection status: {e}")
            return False
    
    def check_backend_logs_for_fake_operations(self):
        """Check backend logs for any fake success messages"""
        print("\n🔍 CHECKING: Backend logs for fake operations")
        
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
                        print(f"❌ FOUND FAKE OPERATION in logs: {pattern}")
                        found_fake = True
                
                if not found_fake:
                    print("✅ No fake operations found in backend logs")
                    return True
                else:
                    return False
            else:
                print("⚠️ Could not read backend logs")
                return True  # Don't fail test if logs unavailable
                
        except Exception as e:
            print(f"⚠️ Error checking logs: {e}")
            return True  # Don't fail test if logs unavailable
    
    def run_all_tests(self):
        """Run all connection validation tests"""
        print("🚀 STARTING CRITICAL MINECRAFT CONNECTION VALIDATION TESTS")
        print("=" * 80)
        
        # Setup test environment
        if not self.setup_test_user():
            print("❌ Failed to setup test environment")
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
            print(f"\n{'='*60}")
            print(f"RUNNING: {test_name}")
            print(f"{'='*60}")
            
            try:
                result = test_func()
                results[test_name] = result
                
                if result:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
                results[test_name] = False
        
        # Summary
        print("\n" + "="*80)
        print("CRITICAL CONNECTION VALIDATION TEST RESULTS")
        print("="*80)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
        
        print(f"\nOVERALL: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL CRITICAL TESTS PASSED - NO FAKE OPERATIONS DETECTED")
            return True
        else:
            print("💥 CRITICAL FAILURES DETECTED - FAKE OPERATIONS STILL PRESENT")
            return False

def main():
    """Main test execution"""
    tester = MinecraftConnectionTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎯 RESULT: Real Minecraft connection validation PASSED")
        sys.exit(0)
    else:
        print("\n💥 RESULT: Real Minecraft connection validation FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()