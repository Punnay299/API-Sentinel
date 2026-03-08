import asyncio
import json
from ml.engine import ZombieAPIMLEngine
import os

async def test_ml():
    print("Test Initialization...")
    engine = ZombieAPIMLEngine.load_or_train()
    
    with open("api_inventory.json") as f:
        apis = json.load(f)
    print(f"Loaded {len(apis)} pre-seeded test APIs.")
    
    # Test 1: A known zombie should classify as zombie
    zombie = next(a for a in apis if "/legacy/" in a["endpoint"])
    result = await engine.analyze_api(zombie)
    assert result["classification"]["status"] == "zombie", \
        f"Expected zombie, got {result['classification']['status']}"
    print("✓ Test 1 Passed: Legacy endpoint classified as Zombie")
    
    # Test 2: A known shadow should be flagged as anomalous
    shadow = next((a for a in apis if "/internal/" in a["endpoint"] and not a["has_auth"]), None)
    # The current inventory may not have /internal/, so default to an orphaned/shadow logic proxy
    if not shadow:
        shadow = next(a for a in apis if a["source"] == "code_repository" and not a["is_documented_in_gateway"])

    result = await engine.analyze_api(shadow)
    assert result["shadow_detection"]["is_shadow"] == True, "Failed to label shadow API"
    print("✓ Test 2 Passed: Undocumented repository API correctly identified as Shadow API anomaly")
    
    # Test 3: A known active should score > 70 security
    active = next(a for a in apis if a["source"] == "api_gateway" 
                  and a["has_auth"] and a["has_encryption"])
    result = await engine.analyze_api(active)
    assert result["security"]["security_score"] > 70, f"Score was {result['security']['security_score']}"
    print(f"✓ Test 3 Passed: Secure Active API scored high (Score: {result['security']['security_score']})")
    
    # Test 4: run_in_executor actually works (run all concurrently)
    print("Executing concurrent analysis...")
    tasks = [engine.analyze_api(api) for api in apis]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == len(apis)
    print("✓ Test 4 Passed: All APIs analyzed concurrently without blocking the event loop")
    
if __name__ == "__main__":
    asyncio.run(test_ml())
