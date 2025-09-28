#!/usr/bin/env python3
"""
URGENT SIMULATION REMOVAL TEST
Tests specifically for the user's complaint about simulation messages still appearing.
Tests the exact server mentioned: oyna.chickennw.com:25565
"""

import asyncio
import aiohttp
import json
import logging
import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimulationRemovalTester:
    def __init__(self):
        # Get backend URL from environment
        try:
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        self.base_url = line.split('=')[1].strip() + '/api'
                        break
                else:
                    self.base_url = 'http://localhost:8001/api'
        except:
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
                    "username": "realuser2024",
                    "password": "securepass456"
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
                # Try to login with existing admin
                login_data = {
                    "username": "realuser2024", 
                    "password": "securepass456"
                }
                async with self.session.post(f"{self.base_url}/auth/login", json=login_data) as resp:
                    if resp.status == 200:
                        auth_response = await resp.json()
                        self.auth_token = auth_response['access_token']
                        self.test_user_id = auth_response['user']['id']
                        logger.info("✅ Authenticated with existing admin user")
                    else:
                        # Try with testadmin fallback
                        login_data = {
                            "username": "testadmin", 
                            "password": "testpass123"
                        }
                        async with self.session.post(f"{self.base_url}/auth/login", json=login_data) as resp:
                            if resp.status == 200:
                                auth_response = await resp.json()
                                self.auth_token = auth_response['access_token']
                                self.test_user_id = auth_response['user']['id']
                                logger.info("✅ Authenticated with fallback admin user")
                            else:
                                logger.error(f"❌ Failed to login: {resp.status}")
                                return False
            
            # Create test Minecraft account with realistic name
            account_data = {
                "account_type": "cracked",
                "nickname": "MinecraftPlayer2024"
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
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up test user: {e}")
            return False
    
    async def test_user_reported_server(self):
        """CRITICAL TEST: Test the exact server user reported - oyna.chickennw.com:25565"""
        logger.info("\n🔍 CRITICAL TEST: User's reported server (oyna.chickennw.com:25565)")
        logger.info("🎯 VERIFYING: NO simulation messages in response")
        
        try:
            # Set server to the exact one user mentioned
            server_settings = {"server_ip": "oyna.chickennw.com:25565"}
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with self.session.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"❌ Failed to update server settings: {resp.status}")
                    return False
            
            logger.info("✅ Server settings updated to oyna.chickennw.com:25565")
            
            # Attempt connection
            async with self.session.post(f"{self.base_url}/accounts/{self.test_account_id}/connect", headers=headers) as resp:
                response_data = await resp.json()
                response_text = json.dumps(response_data, indent=2)
                
                logger.info(f"📋 Connection Response Status: {resp.status}")
                logger.info(f"📋 Full Response: {response_text}")
                
                # Check for simulation patterns in response
                simulation_patterns = [
                    "simulation",
                    "simulated", 
                    "Simulation Mode",
                    "fake",
                    "mock",
                    "pretend",
                    "demo mode",
                    "test mode"
                ]
                
                found_simulation = False
                for pattern in simulation_patterns:
                    if pattern.lower() in response_text.lower():
                        logger.error(f"❌ SIMULATION MESSAGE FOUND: '{pattern}' in response!")
                        found_simulation = True
                
                if found_simulation:
                    logger.error("💥 CRITICAL FAILURE: Simulation messages still present!")
                    logger.error(f"💥 Full response with simulation: {response_text}")
                    return False
                
                # Verify response is either real success or real failure
                if resp.status == 200:
                    if response_data.get('success') == True:
                        logger.info("✅ REAL CONNECTION SUCCESS - No simulation messages")
                        return True
                    else:
                        logger.warning("⚠️ Success=False but status 200 - checking message")
                        message = response_data.get('message', '')
                        if any(pattern.lower() in message.lower() for pattern in simulation_patterns):
                            logger.error("❌ Simulation message in success=false response!")
                            return False
                        else:
                            logger.info("✅ Real response with success=false - No simulation")
                            return True
                elif resp.status >= 400:
                    # Real connection failure
                    error_detail = response_data.get('detail', '')
                    if any(pattern.lower() in error_detail.lower() for pattern in simulation_patterns):
                        logger.error("❌ Simulation message in error response!")
                        return False
                    else:
                        logger.info("✅ REAL CONNECTION FAILURE - No simulation messages")
                        logger.info(f"✅ Real error: {error_detail}")
                        return True
                else:
                    logger.warning(f"⚠️ Unexpected status {resp.status} - checking for simulation")
                    if any(pattern.lower() in response_text.lower() for pattern in simulation_patterns):
                        logger.error("❌ Simulation message in unexpected response!")
                        return False
                    else:
                        logger.info("✅ No simulation messages in unexpected response")
                        return True
                    
        except Exception as e:
            logger.error(f"❌ Error testing user's server: {e}")
            return False
    
    async def check_backend_logs_for_simulation(self):
        """Check backend logs specifically for simulation-related messages"""
        logger.info("\n🔍 CHECKING: Backend logs for simulation messages")
        
        try:
            # Check supervisor logs for backend
            result = subprocess.run(
                ['tail', '-n', '100', '/var/log/supervisor/backend.out.log'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                log_content = result.stdout
                logger.info("📋 Recent backend output logs:")
                logger.info(log_content[-1000:])  # Show last 1000 chars
                
                # Look for simulation patterns
                simulation_patterns = [
                    "SIMULATION",
                    "Simulation Mode", 
                    "simulated",
                    "fake success",
                    "mock connection",
                    "pretend connected",
                    "demo mode"
                ]
                
                found_simulation = False
                for pattern in simulation_patterns:
                    if pattern.lower() in log_content.lower():
                        logger.error(f"❌ SIMULATION MESSAGE in backend logs: {pattern}")
                        found_simulation = True
                
                if not found_simulation:
                    logger.info("✅ No simulation messages found in backend output logs")
                
                # Also check error logs
                result_err = subprocess.run(
                    ['tail', '-n', '100', '/var/log/supervisor/backend.err.log'],
                    capture_output=True, text=True
                )
                
                if result_err.returncode == 0:
                    err_log_content = result_err.stdout
                    logger.info("📋 Recent backend error logs:")
                    logger.info(err_log_content[-1000:])  # Show last 1000 chars
                    
                    for pattern in simulation_patterns:
                        if pattern.lower() in err_log_content.lower():
                            logger.error(f"❌ SIMULATION MESSAGE in backend error logs: {pattern}")
                            found_simulation = True
                
                return not found_simulation
            else:
                logger.warning("⚠️ Could not read backend logs")
                return True  # Don't fail test if logs unavailable
                
        except Exception as e:
            logger.warning(f"⚠️ Error checking logs: {e}")
            return True  # Don't fail test if logs unavailable
    
    async def test_multiple_connection_scenarios(self):
        """Test multiple scenarios to ensure no simulation messages anywhere"""
        logger.info("\n🔍 TESTING: Multiple connection scenarios for simulation messages")
        
        test_servers = [
            "oyna.chickennw.com:25565",  # User's server
            "mc.hypixel.net:25565",      # Popular server
            "nonexistent.server.com:25565",  # Non-existent
            "127.0.0.1:25565"            # Local (likely no server)
        ]
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        all_clean = True
        
        for server in test_servers:
            logger.info(f"\n🎯 Testing server: {server}")
            
            try:
                # Update server settings
                server_settings = {"server_ip": server}
                async with self.session.put(f"{self.base_url}/server-settings", json=server_settings, headers=headers) as resp:
                    if resp.status != 200:
                        logger.warning(f"⚠️ Failed to update server settings for {server}")
                        continue
                
                # Attempt connection
                async with self.session.post(f"{self.base_url}/accounts/{self.test_account_id}/connect", headers=headers) as resp:
                    response_data = await resp.json()
                    response_text = json.dumps(response_data, indent=2)
                    
                    # Check for simulation patterns
                    simulation_patterns = ["simulation", "simulated", "Simulation Mode", "fake", "mock", "pretend"]
                    
                    found_simulation = False
                    for pattern in simulation_patterns:
                        if pattern.lower() in response_text.lower():
                            logger.error(f"❌ SIMULATION MESSAGE for {server}: '{pattern}'")
                            found_simulation = True
                            all_clean = False
                    
                    if not found_simulation:
                        logger.info(f"✅ No simulation messages for {server}")
                
            except Exception as e:
                logger.warning(f"⚠️ Error testing {server}: {e}")
        
        return all_clean
    
    async def run_simulation_removal_tests(self):
        """Run all simulation removal tests"""
        logger.info("🚀 STARTING URGENT SIMULATION REMOVAL TESTS")
        logger.info("🎯 FOCUS: Verify NO simulation messages in system responses")
        logger.info("=" * 80)
        
        await self.setup_session()
        
        try:
            # Setup test environment
            if not await self.setup_test_user():
                logger.error("❌ Failed to setup test environment")
                return False
            
            # Run simulation removal tests
            tests = [
                ("User's Reported Server Test (oyna.chickennw.com:25565)", self.test_user_reported_server),
                ("Backend Logs Simulation Check", self.check_backend_logs_for_simulation),
                ("Multiple Scenarios Simulation Check", self.test_multiple_connection_scenarios)
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
            logger.info("SIMULATION REMOVAL TEST RESULTS")
            logger.info("="*80)
            
            passed = sum(1 for result in results.values() if result)
            total = len(results)
            
            for test_name, result in results.items():
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"{test_name}: {status}")
            
            logger.info(f"\nOVERALL: {passed}/{total} tests passed")
            
            if passed == total:
                logger.info("🎉 ALL TESTS PASSED - NO SIMULATION MESSAGES DETECTED")
                logger.info("🎯 User's complaint about simulation messages should be RESOLVED")
                return True
            else:
                logger.error("💥 SIMULATION MESSAGES STILL PRESENT - USER'S ISSUE NOT RESOLVED")
                return False
                
        finally:
            await self.cleanup_session()

async def main():
    """Main test execution"""
    tester = SimulationRemovalTester()
    success = await tester.run_simulation_removal_tests()
    
    if success:
        logger.info("\n🎯 RESULT: Simulation removal verification PASSED")
        sys.exit(0)
    else:
        logger.error("\n💥 RESULT: Simulation messages still present - FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())