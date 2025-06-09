#!/usr/bin/env python3
"""
Regression Farm System
Phase 6: Nightly regression tests with canonical prompts
"""

import os
import sys
import json
import time
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import openai

# Add the parent directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from generator import generate_from_plan
from ai_planner import create_plan_from_prompt
from src.validator.drawing_standards_validator import validate_drawing_file
from src.solid_validator import validate_drawing_plan_3d


# Canonical test prompts for regression testing
CANONICAL_PROMPTS = [
    "Generate a mounting bracket with 4 corner holes and center lightening hole",
    "Design a flange with 6 bolt holes arranged in a circle and center bore",
    "Create a rectangular plate with slots for adjustment and corner fillets",
    "Generate a circular disc with counterbored holes and chamfered edges",
    "Design a bracket with angled mounting holes and reinforcement ribs",
    "Create a washer with outer diameter 50mm and inner diameter 20mm",
    "Generate a rectangular frame with rounded corners and center cutout",
    "Design a gear blank with center hole and keyway slot",
    "Create a spacer block with through holes and threaded mounting holes",
    "Generate a cover plate with access holes and gasket groove",
    "Design a bearing mount with precision bore and bolt pattern",
    "Create a clamp plate with elongated slots and clamping holes",
    "Generate a motor mount with vibration-damping features",
    "Design a junction box cover with cable entry holes",
    "Create a heat sink plate with cooling fins pattern",
    "Generate a valve body with inlet/outlet ports",
    "Design a sensor mount with adjustable positioning slots",
    "Create a connector plate with standardized hole pattern",
    "Generate a reinforcement gusset with lightening holes",
    "Design a base plate with leveling screw holes and drain opening",
    "Create a pulley blank with hub and spoke pattern",
    "Generate a coupling with keyway and set screw holes",
    "Design a manifold block with cross-drilling pattern",
    "Create a pivot bracket with bearing races",
    "Generate a tensioner plate with adjustment slots",
    "Design a filter housing with retention features",
    "Create a spacer ring with precision dimensions",
    "Generate a mounting pad with isolation features",
    "Design a cover bracket with quick-release mechanism",
    "Create a alignment fixture with reference surfaces",
    "Generate a test specimen with measurement features",
    "Design a jig plate with locating pins and clamps",
    "Create a adapter plate for equipment mounting",
    "Generate a inspection cover with viewing ports",
    "Design a cable routing plate with strain relief",
    "Create a vibration isolator with tuned mass",
    "Generate a thermal barrier with cooling passages",
    "Design a pressure vessel end cap",
    "Create a flow straightener with honeycomb pattern",
    "Generate a structural node with multiple connections",
    "Design a pivot assembly with bearing supports",
    "Create a machine base with anchor bolt pattern",
    "Generate a tool holder with quick-change features",
    "Design a guard plate with safety interlocks",
    "Create a calibration standard with reference features",
    "Generate a alignment target with cross-hairs",
    "Design a clamping fixture with repeatable positioning",
    "Create a test adapter with electrical connections",
    "Generate a mounting interface with thermal expansion joints",
    "Design a precision spacer with ultra-tight tolerances"
]


class RegressionFarm:
    """Manages nightly regression testing with canonical prompts."""
    
    def __init__(self, output_dir: str = "./regression_results"):
        """
        Initialize regression farm.
        
        Args:
            output_dir: Directory for storing regression results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "drawings").mkdir(exist_ok=True)
        (self.output_dir / "reports").mkdir(exist_ok=True)
        (self.output_dir / "baselines").mkdir(exist_ok=True)
    
    def run_regression_suite(self, api_key: str, subset_size: int = 50) -> Dict[str, Any]:
        """
        Run regression suite on canonical prompts.
        
        Args:
            api_key: OpenAI API key
            subset_size: Number of prompts to test (max 50)
            
        Returns:
            Dictionary with regression results
        """
        
        print(f"🧪 Starting Regression Suite")
        print(f"   Prompts: {subset_size}")
        print(f"   Output: {self.output_dir}")
        
        client = openai.OpenAI(api_key=api_key)
        
        # Use subset of canonical prompts
        test_prompts = CANONICAL_PROMPTS[:subset_size]
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_prompts': len(test_prompts),
            'successful_generations': 0,
            'failed_generations': 0,
            'validation_passes': 0,
            'validation_failures': 0,
            'average_generation_time': 0.0,
            'prompt_results': [],
            'failure_reasons': {},
            'performance_metrics': {}
        }
        
        total_generation_time = 0.0
        
        for i, prompt in enumerate(test_prompts):
            print(f"🔄 Testing prompt {i+1}/{len(test_prompts)}")
            
            start_time = time.time()
            prompt_result = self._test_single_prompt(client, prompt, i)
            generation_time = time.time() - start_time
            
            total_generation_time += generation_time
            prompt_result['generation_time'] = generation_time
            
            results['prompt_results'].append(prompt_result)
            
            if prompt_result['success']:
                results['successful_generations'] += 1
                
                if prompt_result['validation_passed']:
                    results['validation_passes'] += 1
                else:
                    results['validation_failures'] += 1
            else:
                results['failed_generations'] += 1
                
                # Track failure reasons
                reason = prompt_result.get('error', 'Unknown error')
                if reason not in results['failure_reasons']:
                    results['failure_reasons'][reason] = 0
                results['failure_reasons'][reason] += 1
        
        # Calculate summary metrics
        if results['total_prompts'] > 0:
            results['success_rate'] = results['successful_generations'] / results['total_prompts'] * 100
            results['validation_rate'] = results['validation_passes'] / results['total_prompts'] * 100
            results['average_generation_time'] = total_generation_time / results['total_prompts']
        
        # Save regression report
        self._save_regression_report(results)
        
        return results
    
    def _test_single_prompt(self, client: openai.OpenAI, prompt: str, prompt_id: int) -> Dict[str, Any]:
        """Test a single prompt through the full pipeline."""
        
        result = {
            'prompt_id': prompt_id,
            'prompt': prompt,
            'success': False,
            'validation_passed': False,
            'error': '',
            'files_generated': {},
            'validation_scores': {}
        }
        
        try:
            # Generate plan
            plan = create_plan_from_prompt(client, prompt)
            if not plan:
                result['error'] = "Failed to generate plan from prompt"
                return result
            
            # Create unique filename
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
            base_filename = f"regression_{prompt_id:03d}_{prompt_hash}"
            
            # Save plan
            plan_path = self.output_dir / "drawings" / f"{base_filename}.json"
            with open(plan_path, 'w') as f:
                json.dump(plan, f, indent=2)
            result['files_generated']['plan'] = str(plan_path)
            
            # Generate DXF
            dxf_path = self.output_dir / "drawings" / f"{base_filename}.dxf"
            generate_from_plan(str(plan_path), str(dxf_path), visualize=True, validate=True)
            result['files_generated']['dxf'] = str(dxf_path)
            
            # PNG should be generated automatically
            png_path = self.output_dir / "drawings" / f"{base_filename}.png"
            if png_path.exists():
                result['files_generated']['png'] = str(png_path)
            
            result['success'] = True
            
            # Run validation checks
            validation_results = self._run_validation_checks(str(plan_path), str(dxf_path))
            result['validation_scores'] = validation_results
            
            # Determine if validation passed (80% threshold)
            avg_score = sum(validation_results.values()) / len(validation_results) if validation_results else 0
            result['validation_passed'] = avg_score >= 0.8
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _run_validation_checks(self, plan_path: str, dxf_path: str) -> Dict[str, float]:
        """Run comprehensive validation on generated files."""
        
        scores = {}
        
        try:
            # Standards validation
            standards_results = validate_drawing_file(dxf_path, plan_path)
            scores['standards_score'] = standards_results['overall_score']
            
            # 3D solid validation
            solid_results = validate_drawing_plan_3d(plan_path)
            scores['solid_score'] = 1.0 if solid_results['is_valid'] else 0.0
            
            # File completeness check
            file_score = 0.0
            if os.path.exists(plan_path):
                file_score += 0.33
            if os.path.exists(dxf_path):
                file_score += 0.33
            if os.path.exists(dxf_path.replace('.dxf', '.png')):
                file_score += 0.34
            scores['file_completeness'] = file_score
            
        except Exception as e:
            print(f"⚠️ Validation error: {e}")
            scores = {'standards_score': 0.0, 'solid_score': 0.0, 'file_completeness': 0.0}
        
        return scores
    
    def _save_regression_report(self, results: Dict[str, Any]) -> None:
        """Save regression results to file."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / "reports" / f"regression_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Also save as latest
        latest_path = self.output_dir / "reports" / "latest_regression.json"
        with open(latest_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📊 Regression report saved: {report_path}")
    
    def compare_with_baseline(self, current_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current results with baseline."""
        
        baseline_path = self.output_dir / "baselines" / "baseline_regression.json"
        
        if not baseline_path.exists():
            print("📝 No baseline found - saving current results as baseline")
            with open(baseline_path, 'w') as f:
                json.dump(current_results, f, indent=2)
            return {'baseline_exists': False, 'regression_detected': False}
        
        # Load baseline
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)
        
        # Compare key metrics
        comparison = {
            'baseline_exists': True,
            'regression_detected': False,
            'metrics_comparison': {}
        }
        
        key_metrics = ['success_rate', 'validation_rate', 'average_generation_time']
        
        for metric in key_metrics:
            current_value = current_results.get(metric, 0)
            baseline_value = baseline.get(metric, 0)
            
            comparison['metrics_comparison'][metric] = {
                'current': current_value,
                'baseline': baseline_value,
                'change': current_value - baseline_value,
                'change_percent': ((current_value - baseline_value) / baseline_value * 100) if baseline_value > 0 else 0
            }
            
            # Detect regression (>5% decrease in success/validation rates)
            if metric in ['success_rate', 'validation_rate'] and comparison['metrics_comparison'][metric]['change_percent'] < -5:
                comparison['regression_detected'] = True
        
        return comparison


def main():
    """Main regression farm entry point."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Regression Farm - Nightly Testing System")
    parser.add_argument('--api-key', type=str, help='OpenAI API key')
    parser.add_argument('--output-dir', type=str, default='./regression_results', help='Output directory')
    parser.add_argument('--count', type=int, default=50, help='Number of prompts to test (max 50)')
    parser.add_argument('--compare-baseline', action='store_true', help='Compare with baseline')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OpenAI API key required. Use --api-key or set OPENAI_API_KEY environment variable.")
        return 1
    
    # Run regression suite
    farm = RegressionFarm(args.output_dir)
    results = farm.run_regression_suite(api_key, min(args.count, 50))
    
    # Print summary
    print(f"\n🎯 Regression Suite Results:")
    print(f"=" * 50)
    print(f"Total Prompts:       {results['total_prompts']}")
    print(f"Successful:          {results['successful_generations']} ({results.get('success_rate', 0):.1f}%)")
    print(f"Validation Passed:   {results['validation_passes']} ({results.get('validation_rate', 0):.1f}%)")
    print(f"Average Time:        {results['average_generation_time']:.1f}s per drawing")
    
    if results['failure_reasons']:
        print(f"\n❌ Failure Reasons:")
        for reason, count in results['failure_reasons'].items():
            print(f"  {reason}: {count}")
    
    # Compare with baseline if requested
    if args.compare_baseline:
        comparison = farm.compare_with_baseline(results)
        
        if comparison['baseline_exists']:
            print(f"\n📊 Baseline Comparison:")
            for metric, data in comparison['metrics_comparison'].items():
                change_str = f"{data['change']:+.1f} ({data['change_percent']:+.1f}%)"
                print(f"  {metric}: {data['current']:.1f} vs {data['baseline']:.1f} [{change_str}]")
            
            if comparison['regression_detected']:
                print(f"\n⚠️ REGRESSION DETECTED - Performance decreased significantly")
                return 1
            else:
                print(f"\n✅ No regression detected")
    
    # Exit with appropriate code
    success_threshold = 80  # 80% success rate required
    if results.get('success_rate', 0) >= success_threshold:
        print(f"\n✅ Regression suite PASSED")
        return 0
    else:
        print(f"\n❌ Regression suite FAILED - Success rate below {success_threshold}%")
        return 1


if __name__ == "__main__":
    sys.exit(main())