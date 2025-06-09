#!/usr/bin/env python3
"""
Complete Phase 3 Pipeline Test

Tests the full semantic engine pipeline:
Natural Language -> AI Planner -> Feature Plan -> Semantic Engine -> DXF + PNG
"""

import json
import tempfile
import os
from ai_planner import create_plan_from_prompt, get_client
from src.validator.plan_validator import DrawingPlanValidator
import subprocess

def test_complete_pipeline():
    """Test the complete Phase 3 pipeline"""
    
    print("🚀 Testing Complete Phase 3 Semantic Engine Pipeline")
    print("=" * 60)
    
    # Test prompts showcasing different feature types
    test_prompts = [
        "A 120mm x 80mm rectangular mounting bracket with a 25mm center hole, four M6 mounting holes in the corners, and 5mm fillets on all corners",
        "A 100mm diameter circular flange with 8 holes arranged in a circle for M8 bolts, and a 40mm center hole",
        "A 150mm square base plate with slots for adjustment, 10mm thick, with mounting holes and rounded corners"
    ]
    
    results = []
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n📝 Test {i}: {prompt}")
        print("-" * 40)
        
        try:
            # Step 1: AI Planner generates feature-based plan
            print("Step 1: AI Planner generating feature plan...")
            client = get_client()
            plan = create_plan_from_prompt(client, prompt)
            
            if not plan:
                print("❌ AI Planner failed")
                results.append({"test": i, "status": "failed", "step": "ai_planner"})
                continue
            
            # Step 2: Validate the plan
            print("Step 2: Validating feature plan...")
            validator = DrawingPlanValidator()
            is_valid, errors = validator.validate_plan(plan)
            
            if not is_valid:
                print(f"❌ Plan validation failed: {errors}")
                results.append({"test": i, "status": "failed", "step": "validation"})
                continue
            
            # Step 3: Save plan and generate DXF
            print("Step 3: Generating DXF using semantic engine...")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(plan, f, indent=2)
                plan_path = f.name
            
            output_path = f"./out/phase3_test_{i}.dxf"
            
            # Run generator with the feature plan
            cmd = ["python", "generator.py", "--plan", plan_path, "--output", output_path, "--visualize"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ DXF generation successful")
                print("✅ PNG visualization created")
                
                results.append({
                    "test": i,
                    "status": "success",
                    "prompt": prompt,
                    "plan_file": plan_path,
                    "dxf_file": output_path,
                    "png_file": output_path.replace('.dxf', '.png')
                })
            else:
                print(f"❌ DXF generation failed: {result.stderr}")
                results.append({"test": i, "status": "failed", "step": "dxf_generation"})
            
            # Cleanup
            os.unlink(plan_path)
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append({"test": i, "status": "failed", "step": "exception", "error": str(e)})
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PHASE 3 PIPELINE TEST RESULTS")
    print("=" * 60)
    
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    
    print(f"✅ Successful: {len(successful)}/{len(test_prompts)}")
    print(f"❌ Failed: {len(failed)}/{len(test_prompts)}")
    
    if successful:
        print("\n🎉 SUCCESSFUL TESTS:")
        for result in successful:
            print(f"  Test {result['test']}: {result['prompt'][:50]}...")
            print(f"    DXF: {result['dxf_file']}")
            print(f"    PNG: {result['png_file']}")
    
    if failed:
        print("\n💥 FAILED TESTS:")
        for result in failed:
            print(f"  Test {result['test']}: Failed at {result['step']}")
    
    # Phase 3 completion status
    if len(successful) == len(test_prompts):
        print("\n🏆 PHASE 3 SEMANTIC ENGINE: FULLY OPERATIONAL")
        print("   Complete pipeline working: Natural Language → Features → DXF")
        return True
    else:
        print(f"\n⚠️ PHASE 3 PARTIAL SUCCESS: {len(successful)}/{len(test_prompts)} tests passed")
        return False

def create_demonstration_plans():
    """Create some example feature plans to demonstrate capabilities"""
    
    example_plans = [
        {
            "name": "Advanced Bracket",
            "plan": {
                "base_feature": {
                    "type": "plate",
                    "shape": "rectangle", 
                    "width": 150,
                    "height": 100
                },
                "modifying_features": [
                    {"type": "hole", "center": [0, 0], "diameter": 30},
                    {"type": "hole", "center": [-60, 35], "diameter": 8},
                    {"type": "hole", "center": [60, 35], "diameter": 8},
                    {"type": "hole", "center": [-60, -35], "diameter": 8},
                    {"type": "hole", "center": [60, -35], "diameter": 8},
                    {"type": "fillet", "radius": 8, "corners": ["all"]},
                    {"type": "slot", "center": [0, -25], "width": 10, "length": 40}
                ],
                "title_block": {
                    "drawing_title": "Advanced Mounting Bracket",
                    "drawn_by": "Phase 3 Semantic Engine",
                    "date": "2024-06-09"
                }
            }
        }
    ]
    
    for example in example_plans:
        filename = f"./plans/phase3_{example['name'].lower().replace(' ', '_')}.json"
        with open(filename, 'w') as f:
            json.dump(example["plan"], f, indent=2)
        print(f"📄 Created example plan: {filename}")

if __name__ == "__main__":
    print("🔧 Creating demonstration plans...")
    create_demonstration_plans()
    
    print("\n🧪 Running complete Phase 3 pipeline tests...")
    success = test_complete_pipeline()
    
    if success:
        print("\n🎯 Phase 3 Semantic Engine is complete and fully operational!")
        print("   Ready for production use.")
    else:
        print("\n🔧 Phase 3 needs additional work on failed components.")