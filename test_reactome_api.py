#!/usr/bin/env python3
"""
Test Reactome API endpoints to find working ones
"""

import requests
import json

def test_reactome_endpoints():
    """Test various Reactome API endpoints"""
    
    # Try different base URLs and API versions
    base_urls = [
        "https://reactome.org/ContentService/data",
        "https://reactome.org/ContentService",
        "https://reactome.org/api",
        "https://reactome.org/ContentService/v1",
        "https://reactome.org/ContentService/v2",
        "https://reactome.org/ContentService/rest",
        "https://reactome.org/ContentService/api"
    ]
    
    endpoints_to_test = [
        "/query",
        "/pathways", 
        "/events",
        "/search",
        "/data/query",
        "/data/pathways",
        "/data/events",
        "/data/search",
        "/pathway",
        "/event",
        "/entity"
    ]
    
    print("Testing Reactome API endpoints...")
    print("=" * 70)
    
    working_endpoints = []
    
    for base_url in base_urls:
        print(f"\n🔍 Testing base URL: {base_url}")
        print("-" * 50)
        
        for endpoint in endpoints_to_test:
            url = base_url + endpoint
            print(f"\nTesting: {url}")
            
            # Test with different parameters
            test_params = [
                {'query': 'cancer', 'species': 'Homo sapiens'},
                {'species': 'Homo sapiens'},
                {'query': 'cancer'},
                {}
            ]
            
            for params in test_params:
                try:
                    response = requests.get(url, params=params, timeout=10)
                    print(f"  Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        print("  ✅ SUCCESS")
                        try:
                            data = response.json()
                            if isinstance(data, list):
                                print(f"     Found {len(data)} items")
                                if data:
                                    print(f"     First item type: {data[0].get('schemaClass', 'Unknown')}")
                            elif isinstance(data, dict):
                                print(f"     Response keys: {list(data.keys())}")
                        except:
                            print("     Response is not JSON")
                        
                        working_endpoints.append({
                            'url': url,
                            'params': params,
                            'status': 'working'
                        })
                        break  # Found working endpoint, move to next
                    else:
                        print(f"  ❌ FAILED: {response.text[:50]}")
                        
                except Exception as e:
                    print(f"  ❌ ERROR: {e}")
                    continue
    
    # Test GraphQL endpoint
    print(f"\n🔍 Testing GraphQL endpoint")
    print("-" * 50)
    
    graphql_url = "https://reactome.org/ContentService/data/graphql"
    graphql_query = """
    query {
        pathways(species: "Homo sapiens") {
            stId
            displayName
            schemaClass
        }
    }
    """
    
    try:
        response = requests.post(graphql_url, json={'query': graphql_query}, timeout=10)
        print(f"GraphQL Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ GraphQL SUCCESS")
            try:
                data = response.json()
                print(f"     Response keys: {list(data.keys())}")
            except:
                print("     Response is not JSON")
        else:
            print(f"❌ GraphQL FAILED: {response.text[:50]}")
    except Exception as e:
        print(f"❌ GraphQL ERROR: {e}")
    
    print("\n" + "=" * 70)
    print("Testing complete!")
    
    if working_endpoints:
        print(f"\n🎉 Found {len(working_endpoints)} working endpoints:")
        for endpoint in working_endpoints:
            print(f"  • {endpoint['url']}")
    else:
        print("\n❌ No working endpoints found. Reactome API may be deprecated or changed.")

if __name__ == "__main__":
    test_reactome_endpoints() 