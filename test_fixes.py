#!/usr/bin/env python3
"""
Simple test script to verify the fixes work
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pathway_analysis():
    """Test pathway analysis fixes"""
    print("Testing pathway analysis fixes...")
    
    try:
        from drug_discovery.pathway_analysis import PathwayAnalyzer
        
        analyzer = PathwayAnalyzer()
        
        # Test disease to pathway mapping
        pathways = analyzer.get_pathway_ids_from_disease("cancer")
        print(f"Found {len(pathways)} pathways for cancer")
        
        # Test protein extraction from pathways
        if pathways:
            proteins = analyzer.get_proteins_from_pathway(pathways[0])
            print(f"Found {len(proteins)} proteins in first pathway")
        
        print("✅ Pathway analysis fixes working")
        return True
        
    except Exception as e:
        print(f"❌ Pathway analysis test failed: {e}")
        return False

def test_protein_analysis():
    """Test protein analysis fixes"""
    print("Testing protein analysis fixes...")
    
    try:
        from drug_discovery.protein_analysis import ProteinAnalyzer
        
        analyzer = ProteinAnalyzer()
        
        # Test protein analysis with fallback
        result = analyzer.get_protein_function_and_druggability("TP53")
        print(f"Protein analysis result: {result['protein_name']}")
        print(f"Druggability score: {result['druggability_score']}")
        
        print("✅ Protein analysis fixes working")
        return True
        
    except Exception as e:
        print(f"❌ Protein analysis test failed: {e}")
        return False

def test_network_analysis():
    """Test network analysis fixes"""
    print("Testing network analysis fixes...")
    
    try:
        from drug_discovery.network_analysis import NetworkAnalyzer
        
        analyzer = NetworkAnalyzer()
        
        # Test protein interactions with fallback
        interactions = analyzer.get_protein_interactions("TP53")
        print(f"Found {len(interactions)} interactions for TP53")
        
        print("✅ Network analysis fixes working")
        return True
        
    except Exception as e:
        print(f"❌ Network analysis test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🔬 Testing Drug Discovery Pipeline Fixes")
    print("=" * 50)
    
    tests = [
        test_pathway_analysis,
        test_protein_analysis,
        test_network_analysis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All fixes are working correctly!")
    else:
        print("⚠️  Some fixes need attention")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 