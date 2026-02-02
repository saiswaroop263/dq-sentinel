#!/usr/bin/env python3
"""
DQ Sentinel Backend API Testing Suite
Tests all backend endpoints for the Data Quality monitoring tool
"""

import requests
import sys
import json
import io
import csv
from datetime import datetime
from typing import Dict, Any, Optional

class DQSentinelAPITester:
    def __init__(self, base_url="https://quality-check-25.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.demo_run_id = None
        self.uploaded_dataset_id = None
        self.upload_run_id = None

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Any = None, files: Dict = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, timeout=30)
                else:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                return self.log_test(name, False, f"Unsupported method: {method}"), {}

            success = response.status_code == expected_status
            response_data = {}
            
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    response_data = response.json()
                except:
                    response_data = {}
            
            details = f"Status: {response.status_code}"
            if not success:
                details += f" (expected {expected_status})"
                if response_data.get('detail'):
                    details += f" - {response_data['detail']}"
            
            return self.log_test(name, success, details), response_data

        except requests.exceptions.Timeout:
            return self.log_test(name, False, "Request timeout"), {}
        except requests.exceptions.ConnectionError:
            return self.log_test(name, False, "Connection error"), {}
        except Exception as e:
            return self.log_test(name, False, f"Error: {str(e)}"), {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, data = self.run_test("Root Endpoint", "GET", "", 200)
        if success and data.get('message') == 'DQ Sentinel API':
            return self.log_test("Root Message Check", True, "Correct API message")
        return self.log_test("Root Message Check", False, "Incorrect API message")

    def test_demo_endpoint(self):
        """Test demo data generation and DQ checks"""
        print("\n🔍 Testing Demo Endpoint...")
        success, data = self.run_test("Demo Generation", "POST", "demo", 200)
        
        if success and data:
            # Validate demo response structure
            required_fields = ['run_id', 'dataset_id', 'status', 'summary', 'results']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test("Demo Response Structure", False, f"Missing fields: {missing_fields}")
            
            self.demo_run_id = data['run_id']
            
            # Validate summary
            summary = data.get('summary', {})
            if not all(key in summary for key in ['total_rules', 'passed', 'failed', 'score']):
                return self.log_test("Demo Summary Structure", False, "Missing summary fields")
            
            # Validate results
            results = data.get('results', [])
            if len(results) == 0:
                return self.log_test("Demo Results", False, "No DQ results returned")
            
            # Check for expected DQ rules
            rule_names = [r.get('rule_name', '') for r in results]
            expected_rules = ['Null Rate:', 'Duplicate Rows', 'Unique Key:', 'Email Regex:', 'Outliers:']
            found_rules = [rule for rule in expected_rules if any(rule in name for name in rule_names)]
            
            if len(found_rules) < 3:  # At least 3 rules should be present
                return self.log_test("Demo DQ Rules", False, f"Expected rules not found. Got: {rule_names}")
            
            self.log_test("Demo Response Structure", True, f"Run ID: {self.demo_run_id[:8]}")
            self.log_test("Demo Summary", True, f"Score: {summary.get('score')}%, Rules: {summary.get('total_rules')}")
            return self.log_test("Demo DQ Rules", True, f"Found {len(results)} rules")
        
        return False

    def test_runs_list(self):
        """Test getting list of runs"""
        print("\n🔍 Testing Runs List...")
        success, data = self.run_test("Get Runs List", "GET", "runs", 200)
        
        if success and data:
            runs = data.get('runs', [])
            if len(runs) == 0:
                return self.log_test("Runs List Content", False, "No runs found")
            
            # Check if demo run is in the list
            if self.demo_run_id:
                demo_found = any(run.get('run_id') == self.demo_run_id for run in runs)
                if not demo_found:
                    return self.log_test("Demo Run in List", False, "Demo run not found in runs list")
                self.log_test("Demo Run in List", True)
            
            return self.log_test("Runs List Content", True, f"Found {len(runs)} runs")
        
        return False

    def test_run_details(self):
        """Test getting specific run details"""
        if not self.demo_run_id:
            return self.log_test("Run Details", False, "No demo run ID available")
        
        print("\n🔍 Testing Run Details...")
        success, data = self.run_test("Get Run Details", "GET", f"runs/{self.demo_run_id}", 200)
        
        if success and data:
            # Validate run details structure
            required_fields = ['run_id', 'dataset_id', 'status', 'summary', 'results']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test("Run Details Structure", False, f"Missing fields: {missing_fields}")
            
            results = data.get('results', [])
            if len(results) == 0:
                return self.log_test("Run Details Results", False, "No results in run details")
            
            return self.log_test("Run Details Structure", True, f"Found {len(results)} results")
        
        return False

    def test_json_report(self):
        """Test JSON report generation"""
        if not self.demo_run_id:
            return self.log_test("JSON Report", False, "No demo run ID available")
        
        print("\n🔍 Testing JSON Report...")
        success, data = self.run_test("Get JSON Report", "GET", f"report/{self.demo_run_id}", 200)
        
        if success and data:
            # Validate report structure
            required_fields = ['report_type', 'generated_at', 'run', 'results']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test("JSON Report Structure", False, f"Missing fields: {missing_fields}")
            
            if data.get('report_type') != 'DQ Sentinel Report':
                return self.log_test("JSON Report Type", False, "Incorrect report type")
            
            return self.log_test("JSON Report Structure", True, "Valid JSON report generated")
        
        return False

    def test_html_report(self):
        """Test HTML report generation"""
        if not self.demo_run_id:
            return self.log_test("HTML Report", False, "No demo run ID available")
        
        print("\n🔍 Testing HTML Report...")
        try:
            url = f"{self.base_url}/report/{self.demo_run_id}/html"
            response = requests.get(url, timeout=30)
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                # Check if response is HTML
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type:
                    return self.log_test("HTML Report Content Type", False, f"Expected HTML, got {content_type}")
                
                # Check for key HTML elements
                html_content = response.text
                if 'DQ Sentinel Report' not in html_content:
                    return self.log_test("HTML Report Content", False, "Missing report title")
                
                if 'Overall Score' not in html_content:
                    return self.log_test("HTML Report Content", False, "Missing score section")
                
                return self.log_test("HTML Report", True, "Valid HTML report generated")
            
            return self.log_test("HTML Report", success, details)
            
        except Exception as e:
            return self.log_test("HTML Report", False, f"Error: {str(e)}")

    def create_test_csv(self) -> io.BytesIO:
        """Create a test CSV file for upload testing"""
        csv_data = [
            ['id', 'name', 'email', 'age', 'price'],
            ['1', 'John Doe', 'john@example.com', '25', '100.50'],
            ['2', 'Jane Smith', 'jane@example.com', '30', '200.75'],
            ['3', 'Bob Johnson', 'bob@invalid-email', '35', '150.25'],
            ['4', 'Alice Brown', 'alice@example.com', '28', '300.00'],
            ['5', 'Charlie Wilson', 'charlie@example.com', '45', '250.50']
        ]
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(csv_data)
        
        csv_bytes = io.BytesIO(output.getvalue().encode('utf-8'))
        csv_bytes.name = 'test_data.csv'
        return csv_bytes

    def test_file_upload(self):
        """Test CSV file upload"""
        print("\n🔍 Testing File Upload...")
        
        # Create test CSV
        test_csv = self.create_test_csv()
        files = {'file': ('test_data.csv', test_csv, 'text/csv')}
        
        success, data = self.run_test("Upload CSV File", "POST", "upload", 200, files=files)
        
        if success and data:
            # Validate upload response
            required_fields = ['dataset_id', 'filename', 'columns', 'row_count']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test("Upload Response Structure", False, f"Missing fields: {missing_fields}")
            
            self.uploaded_dataset_id = data['dataset_id']
            
            if data.get('filename') != 'test_data.csv':
                return self.log_test("Upload Filename", False, f"Expected 'test_data.csv', got '{data.get('filename')}'")
            
            if data.get('row_count') != 5:  # 5 data rows
                return self.log_test("Upload Row Count", False, f"Expected 5 rows, got {data.get('row_count')}")
            
            expected_columns = ['id', 'name', 'email', 'age', 'price']
            if data.get('columns') != expected_columns:
                return self.log_test("Upload Columns", False, f"Column mismatch")
            
            self.log_test("Upload Response Structure", True, f"Dataset ID: {self.uploaded_dataset_id[:8]}")
            self.log_test("Upload Filename", True)
            self.log_test("Upload Row Count", True)
            return self.log_test("Upload Columns", True)
        
        return False

    def test_run_checks_on_upload(self):
        """Test running DQ checks on uploaded dataset"""
        if not self.uploaded_dataset_id:
            return self.log_test("Run Checks on Upload", False, "No uploaded dataset ID available")
        
        print("\n🔍 Testing DQ Checks on Uploaded Data...")
        
        run_data = {"dataset_id": self.uploaded_dataset_id}
        success, data = self.run_test("Run DQ Checks", "POST", "run", 200, data=run_data)
        
        if success and data:
            # Validate run response
            required_fields = ['run_id', 'dataset_id', 'status', 'summary', 'results']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test("Run Response Structure", False, f"Missing fields: {missing_fields}")
            
            self.upload_run_id = data['run_id']
            
            if data.get('dataset_id') != self.uploaded_dataset_id:
                return self.log_test("Run Dataset ID", False, "Dataset ID mismatch")
            
            if data.get('status') != 'completed':
                return self.log_test("Run Status", False, f"Expected 'completed', got '{data.get('status')}'")
            
            # Validate summary
            summary = data.get('summary', {})
            if not all(key in summary for key in ['total_rules', 'passed', 'failed', 'score']):
                return self.log_test("Run Summary Structure", False, "Missing summary fields")
            
            results = data.get('results', [])
            if len(results) == 0:
                return self.log_test("Run Results", False, "No DQ results returned")
            
            self.log_test("Run Response Structure", True, f"Run ID: {self.upload_run_id[:8]}")
            self.log_test("Run Dataset ID", True)
            self.log_test("Run Status", True)
            self.log_test("Run Summary Structure", True, f"Score: {summary.get('score')}%")
            return self.log_test("Run Results", True, f"Found {len(results)} results")
        
        return False

    def test_datasets_endpoint(self):
        """Test getting datasets list"""
        print("\n🔍 Testing Datasets List...")
        success, data = self.run_test("Get Datasets", "GET", "datasets", 200)
        
        if success and data:
            datasets = data.get('datasets', [])
            if len(datasets) == 0:
                return self.log_test("Datasets List", False, "No datasets found")
            
            # Check if uploaded dataset is in the list
            if self.uploaded_dataset_id:
                dataset_found = any(ds.get('dataset_id') == self.uploaded_dataset_id for ds in datasets)
                if not dataset_found:
                    return self.log_test("Uploaded Dataset in List", False, "Uploaded dataset not found")
                self.log_test("Uploaded Dataset in List", True)
            
            return self.log_test("Datasets List", True, f"Found {len(datasets)} datasets")
        
        return False

    def test_invalid_endpoints(self):
        """Test error handling for invalid requests"""
        print("\n🔍 Testing Error Handling...")
        
        # Test invalid run ID
        success, _ = self.run_test("Invalid Run ID", "GET", "runs/invalid-id", 404)
        
        # Test invalid report ID
        success2, _ = self.run_test("Invalid Report ID", "GET", "report/invalid-id", 404)
        
        # Test run without dataset_id
        success3, _ = self.run_test("Run Without Dataset ID", "POST", "run", 422, data={})
        
        return success and success2 and success3

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting DQ Sentinel Backend API Tests")
        print("=" * 60)
        
        # Basic connectivity
        self.test_root_endpoint()
        
        # Demo workflow
        self.test_demo_endpoint()
        self.test_runs_list()
        self.test_run_details()
        self.test_json_report()
        self.test_html_report()
        
        # Upload workflow
        self.test_file_upload()
        self.test_run_checks_on_upload()
        self.test_datasets_endpoint()
        
        # Error handling
        self.test_invalid_endpoints()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    """Main test runner"""
    tester = DQSentinelAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())