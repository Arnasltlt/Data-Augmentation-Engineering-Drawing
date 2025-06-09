#!/usr/bin/env python3
"""
QualityGate Comprehensive Test Runner
Super Agent 2 Mission Complete - Test Coverage & Quality Assurance

This script runs the complete QualityGate test suite to validate 80%+ coverage target.
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any


class QualityGateRunner:
    """Main test runner for QualityGate comprehensive testing"""
    
    def __init__(self, project_root: Path, verbose: bool = False):
        self.project_root = project_root
        self.verbose = verbose
        self.results = {}
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete QualityGate test suite"""
        print("🚀 STARTING QUALITYGATE COMPREHENSIVE TESTING")
        print("=" * 80)
        
        start_time = time.time()
        
        # Test categories to run
        test_suites = [
            ("VectorForge Unit Tests", self._run_vectorforge_tests),
            ("LayoutLab Unit Tests", self._run_layoutlab_tests),
            ("GrungeWorks Unit Tests", self._run_grungeworks_tests),
            ("Integration E2E Tests", self._run_integration_tests),
            ("Property-Based Tests", self._run_property_tests),
            ("Schema & Compliance Tests", self._run_compliance_tests),
            ("Performance Benchmarks", self._run_performance_tests),
            ("Coverage Analysis", self._run_coverage_analysis),
        ]
        
        overall_success = True
        
        for suite_name, test_function in test_suites:
            print(f"\n📋 Running {suite_name}...")
            print("-" * 60)
            
            try:
                result = test_function()
                self.results[suite_name] = result
                
                if result.get("success", False):
                    print(f"✅ {suite_name}: PASSED")
                else:
                    print(f"❌ {suite_name}: FAILED")
                    overall_success = False
                    
            except Exception as e:
                print(f"❌ {suite_name}: ERROR - {e}")
                self.results[suite_name] = {"success": False, "error": str(e)}
                overall_success = False
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Generate final report
        self._generate_final_report(duration, overall_success)
        
        return {
            "overall_success": overall_success,
            "duration_seconds": duration,
            "results": self.results
        }
    
    def _run_vectorforge_tests(self) -> Dict[str, Any]:
        """Run VectorForge unit tests"""
        return self._run_pytest_suite([
            "tests/test_vectorforge.py",
            "tests/test_license_compliance.py"
        ], "VectorForge")
    
    def _run_layoutlab_tests(self) -> Dict[str, Any]:
        """Run LayoutLab unit tests"""
        return self._run_pytest_suite([
            "tests/test_overlap.py",
            "tests/test_layoutlab_extended.py"
        ], "LayoutLab")
    
    def _run_grungeworks_tests(self) -> Dict[str, Any]:
        """Run GrungeWorks unit tests"""
        return self._run_pytest_suite([
            "tests/test_noise_alignment.py",
            "tests/test_grungeworks_extended.py"
        ], "GrungeWorks")
    
    def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration and E2E tests"""
        return self._run_pytest_suite([
            "tests/test_integration_e2e.py"
        ], "Integration")
    
    def _run_property_tests(self) -> Dict[str, Any]:
        """Run property-based tests"""
        return self._run_pytest_suite([
            "tests/test_property_based.py"
        ], "Property-Based", extra_args=["--hypothesis-show-statistics"])
    
    def _run_compliance_tests(self) -> Dict[str, Any]:
        """Run schema and compliance tests"""
        return self._run_pytest_suite([
            "tests/test_schema.py",
            "tests/test_overlay.py"
        ], "Compliance")
    
    def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmarks"""
        try:
            # Run specific performance tests
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/test_layoutlab_extended.py::TestScalabilityAndPerformance",
                "--verbose"
            ]
            
            if self.verbose:
                cmd.append("-s")
            
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout if self.verbose else "",
                "error": result.stderr if result.returncode != 0 else "",
                "return_code": result.returncode
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_coverage_analysis(self) -> Dict[str, Any]:
        """Run comprehensive coverage analysis"""
        try:
            # Run coverage analysis
            cmd = [sys.executable, "tests/test_coverage_report.py"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            # Check if coverage report was generated
            coverage_json = self.project_root / "coverage_report.json"
            coverage_achieved = False
            
            if coverage_json.exists():
                import json
                try:
                    with open(coverage_json, 'r') as f:
                        data = json.load(f)
                    
                    overall_coverage = data.get("overall", {}).get("coverage_percentage", 0)
                    target = data.get("target", 80)
                    coverage_achieved = overall_coverage >= target
                    
                except Exception:
                    pass
            
            return {
                "success": result.returncode == 0 and coverage_achieved,
                "coverage_achieved": coverage_achieved,
                "output": result.stdout if self.verbose else "",
                "error": result.stderr if result.returncode != 0 else "",
                "return_code": result.returncode
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_pytest_suite(self, test_files: List[str], suite_name: str, extra_args: List[str] = None) -> Dict[str, Any]:
        """Run a pytest suite with specified test files"""
        try:
            cmd = [sys.executable, "-m", "pytest"] + test_files
            
            if self.verbose:
                cmd.extend(["-v", "-s"])
            else:
                cmd.append("-v")
            
            if extra_args:
                cmd.extend(extra_args)
            
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout if self.verbose else "",
                "error": result.stderr if result.returncode != 0 else "",
                "return_code": result.returncode
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_final_report(self, duration: float, overall_success: bool):
        """Generate final QualityGate report"""
        print("\n" + "=" * 80)
        print("📊 QUALITYGATE FINAL REPORT")
        print("=" * 80)
        
        print(f"⏱️  Total Runtime: {duration:.2f} seconds")
        print(f"🎯 Overall Status: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
        print()
        
        print("📋 Test Suite Results:")
        print("-" * 40)
        
        for suite_name, result in self.results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            print(f"  {status} {suite_name}")
            
            if not result.get("success", False) and "error" in result:
                print(f"    Error: {result['error']}")
        
        print()
        
        # Check if coverage report exists
        coverage_json = self.project_root / "coverage_report.json"
        if coverage_json.exists():
            try:
                import json
                with open(coverage_json, 'r') as f:
                    data = json.load(f)
                
                overall_coverage = data.get("overall", {}).get("coverage_percentage", 0)
                target = data.get("target", 80)
                
                print("📈 Coverage Summary:")
                print("-" * 40)
                print(f"  Overall Coverage: {overall_coverage:.1f}%")
                print(f"  Target Coverage: {target}%")
                print(f"  Status: {'✅ TARGET MET' if overall_coverage >= target else '❌ BELOW TARGET'}")
                
                print("\n  Agent Breakdown:")
                for agent, agent_data in data.get("agents", {}).items():
                    agent_coverage = agent_data.get("coverage_percentage", 0)
                    agent_status = "✅" if agent_coverage >= target else "❌"
                    print(f"    {agent_status} {agent}: {agent_coverage:.1f}%")
                
            except Exception as e:
                print(f"  ⚠️  Could not read coverage report: {e}")
        
        print("\n" + "=" * 80)
        
        if overall_success:
            print("🎉 QUALITYGATE MISSION ACCOMPLISHED!")
            print("   Super Agent 2 has successfully achieved production-ready test coverage.")
            print("   All agents now have comprehensive testing with 80%+ coverage target.")
        else:
            print("⚠️  QUALITYGATE MISSION INCOMPLETE")
            print("   Some test suites failed. Review errors above and rerun.")
        
        print("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="QualityGate Comprehensive Test Runner")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--coverage-only", action="store_true", help="Run only coverage analysis")
    parser.add_argument("--quick", action="store_true", help="Run quick test subset")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent
    runner = QualityGateRunner(project_root, verbose=args.verbose)
    
    if args.coverage_only:
        print("📊 Running coverage analysis only...")
        result = runner._run_coverage_analysis()
        success = result.get("success", False)
        print("✅ Coverage analysis completed" if success else "❌ Coverage analysis failed")
        return 0 if success else 1
    
    # Run complete test suite
    results = runner.run_all_tests()
    
    return 0 if results["overall_success"] else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)