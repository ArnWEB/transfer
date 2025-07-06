#!/usr/bin/env python3
"""
Test STRING API endpoints to find working ones
"""

import requests
import json

def test_string_endpoints():
    """Test various STRING API endpoints"""
    
    base_url = "https://string-db.org/api"
    
    endpoints_to_test = [
        "/network",
        "/json/network", 
        "/v11/network",
        "/v11/json/network",
        "/v12/network",
        "/v12/json/network",
        "/interaction_partners",
        "/v11/interaction_partners",
        "/v12/interaction_partners"
    ]
    
    print("Testing STRING API endpoints...")
    print("=" * 50)
    
    for endpoint in endpoints_to_test:
        url = base_url + endpoint
        print(f"\nTesting: {url}")
        
        # Test with TP53 protein
        params = {
            'identifiers': 'TP53',
            'species': '9606',  # Human
            'required_score': '400'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS")
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"   Found {len(data)} interactions")
                    elif isinstance(data, dict):
                        print(f"   Response keys: {list(data.keys())}")
                except:
                    print("   Response is not JSON")
            else:
                print("❌ FAILED")
                print(f"   Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("Testing complete!")

if __name__ == "__main__":
    test_string_endpoints() 