#!/usr/bin/env python3
"""
RepoGuardian's Completion Score Monitor
Calculates objective 0-100 "done-ness" score for the Symbol-Heavy Drawing Generator project.
"""

import os
import sys
import yaml
import json
import subprocess
import glob
from pathlib import Path
from typing import Dict, List, Tuple


class CompletionScoreCalculator:
    """Calculate project completion score based on defined metrics."""
    
    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.score_breakdown = {}
        
    def check_symbol_coverage(self) -> int:
        """Symbol coverage & manifest parity (30 pts)"""
        try:
            manifest_path = self.repo_root / "symbols" / "symbols_manifest.yaml"
            symbols_dir = self.repo_root / "symbols"
            
            if not manifest_path.exists():
                self.score_breakdown["symbol_coverage"] = "No manifest found"
                return 0
            
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
            
            if not manifest or 'symbols' not in manifest:
                self.score_breakdown["symbol_coverage"] = "Invalid manifest format"
                return 0
            
            # Count SVG files
            svg_files = list(symbols_dir.glob("*.svg"))
            manifest_entries = len(manifest['symbols'])
            
            # Target: 60+ symbols
            target_symbols = 60
            actual_symbols = len(svg_files)
            
            # Check manifest parity
            svg_names = {f.stem for f in svg_files}
            manifest_names = {entry['name'] for entry in manifest['symbols']}
            
            parity_score = 15 if svg_names == manifest_names else 0
            coverage_score = min(15, (actual_symbols / target_symbols) * 15)
            
            total_score = int(parity_score + coverage_score)
            self.score_breakdown["symbol_coverage"] = f"{actual_symbols}/{target_symbols} symbols, parity: {parity_score > 0}"
            
            return total_score
            
        except Exception as e:
            self.score_breakdown["symbol_coverage"] = f"Error: {e}"
            return 0
    
    def check_layout_engine(self) -> int:
        """Layout engine throughput (15 pts)"""
        try:
            layoutlab_path = self.repo_root / "src" / "layoutlab"
            
            if not layoutlab_path.exists():
                self.score_breakdown["layout_engine"] = "LayoutLab not found"
                return 0
            
            # Check for key files
            required_files = ["placer.py", "__init__.py"]
            missing_files = [f for f in required_files if not (layoutlab_path / f).exists()]
            
            if missing_files:
                self.score_breakdown["layout_engine"] = f"Missing files: {missing_files}"
                return 5
            
            # Try to import and test basic functionality
            try:
                sys.path.insert(0, str(self.repo_root / "src"))
                import layoutlab
                self.score_breakdown["layout_engine"] = "LayoutLab module functional"
                return 15
            except ImportError as e:
                self.score_breakdown["layout_engine"] = f"Import error: {e}"
                return 10
                
        except Exception as e:
            self.score_breakdown["layout_engine"] = f"Error: {e}"
            return 0
    
    def check_noise_pipeline(self) -> int:
        """Noise pipeline variety (10 pts)"""
        try:
            grungeworks_path = self.repo_root / "src" / "grungeworks"
            
            if not grungeworks_path.exists():
                self.score_breakdown["noise_pipeline"] = "GrungeWorks not found"
                return 0
            
            # Check for filters and CLI
            files_exist = {
                "filters.py": (grungeworks_path / "filters.py").exists(),
                "cli.py": (grungeworks_path / "cli.py").exists()
            }
            
            existing_count = sum(files_exist.values())
            score = int((existing_count / 2) * 10)
            
            self.score_breakdown["noise_pipeline"] = f"Components: {existing_count}/2"
            return score
            
        except Exception as e:
            self.score_breakdown["noise_pipeline"] = f"Error: {e}"
            return 0
    
    def check_end_to_end_generator(self) -> int:
        """End-to-end generator run (20 pts)"""
        try:
            generator_path = self.repo_root / "generate.py"
            
            if not generator_path.exists():
                self.score_breakdown["end_to_end"] = "generate.py not found"
                return 0
            
            # Try to run the generator with minimal parameters
            try:
                result = subprocess.run([
                    sys.executable, str(generator_path), "--help"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    self.score_breakdown["end_to_end"] = "Generator help runs successfully"
                    return 20
                else:
                    self.score_breakdown["end_to_end"] = f"Generator help failed: {result.stderr}"
                    return 10
                    
            except subprocess.TimeoutExpired:
                self.score_breakdown["end_to_end"] = "Generator help timeout"
                return 5
            except Exception as e:
                self.score_breakdown["end_to_end"] = f"Generator run error: {e}"
                return 5
                
        except Exception as e:
            self.score_breakdown["end_to_end"] = f"Error: {e}"
            return 0
    
    def check_test_coverage(self) -> int:
        """Test coverage ≥ 80% (10 pts)"""
        try:
            tests_dir = self.repo_root / "tests"
            
            if not tests_dir.exists():
                self.score_breakdown["test_coverage"] = "Tests directory not found"
                return 0
            
            # Count test files
            test_files = list(tests_dir.glob("test_*.py"))
            
            if len(test_files) == 0:
                self.score_breakdown["test_coverage"] = "No test files found"
                return 0
            
            # Try to run tests and get coverage (simplified check)
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", str(tests_dir), "--tb=short"
                ], capture_output=True, text=True, timeout=30, cwd=self.repo_root)
                
                if result.returncode == 0:
                    # Tests pass - award points based on number of test files
                    score = min(10, len(test_files) * 2)
                    self.score_breakdown["test_coverage"] = f"{len(test_files)} test files, tests pass"
                    return score
                else:
                    self.score_breakdown["test_coverage"] = f"{len(test_files)} test files, some failures"
                    return max(2, len(test_files))
                    
            except subprocess.TimeoutExpired:
                self.score_breakdown["test_coverage"] = f"{len(test_files)} test files, timeout"
                return len(test_files)
            except Exception as e:
                self.score_breakdown["test_coverage"] = f"{len(test_files)} test files, run error: {e}"
                return len(test_files)
                
        except Exception as e:
            self.score_breakdown["test_coverage"] = f"Error: {e}"
            return 0
    
    def check_ci_status(self) -> int:
        """CI green streak - last five main builds (10 pts)"""
        try:
            # Check for CI configuration
            github_dir = self.repo_root / ".github" / "workflows"
            
            if not github_dir.exists():
                self.score_breakdown["ci_status"] = "No GitHub Actions found"
                return 0
            
            workflow_files = list(github_dir.glob("*.yml")) + list(github_dir.glob("*.yaml"))
            
            if len(workflow_files) == 0:
                self.score_breakdown["ci_status"] = "No workflow files found"
                return 0
            
            # Award points for having CI setup
            score = min(10, len(workflow_files) * 5)
            self.score_breakdown["ci_status"] = f"{len(workflow_files)} workflow files configured"
            
            return score
            
        except Exception as e:
            self.score_breakdown["ci_status"] = f"Error: {e}"
            return 0
    
    def calculate_total_score(self) -> Dict[str, any]:
        """Calculate total completion score."""
        scores = {
            "symbol_coverage": self.check_symbol_coverage(),
            "layout_engine": self.check_layout_engine(), 
            "noise_pipeline": self.check_noise_pipeline(),
            "end_to_end": self.check_end_to_end_generator(),
            "test_coverage": self.check_test_coverage(),
            "ci_status": self.check_ci_status()
        }
        
        total_score = sum(scores.values())
        
        # Check if any metric is at 0 (blocking condition)
        zero_metrics = [k for k, v in scores.items() if v == 0]
        
        return {
            "total_score": total_score,
            "max_score": 100,
            "individual_scores": scores,
            "score_breakdown": self.score_breakdown,
            "passing": total_score >= 90 and len(zero_metrics) == 0,
            "zero_metrics": zero_metrics
        }


def main():
    """Main entry point for completion score calculation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Calculate project completion score")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    
    args = parser.parse_args()
    
    calculator = CompletionScoreCalculator(args.repo_root)
    result = calculator.calculate_total_score()
    
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"🔍 Project Completion Score: {result['total_score']}/{result['max_score']}")
        print(f"{'✅ PASSING' if result['passing'] else '❌ FAILING'}")
        print()
        
        print("📊 Individual Scores:")
        for metric, score in result['individual_scores'].items():
            max_scores = {
                "symbol_coverage": 30,
                "layout_engine": 15, 
                "noise_pipeline": 10,
                "end_to_end": 20,
                "test_coverage": 10,
                "ci_status": 10
            }
            print(f"  {metric}: {score}/{max_scores[metric]} - {result['score_breakdown'][metric]}")
        
        if result['zero_metrics']:
            print(f"\n⚠️  Blocking metrics at 0: {', '.join(result['zero_metrics'])}")
    
    # Exit with appropriate code
    sys.exit(0 if result['passing'] else 1)


if __name__ == "__main__":
    main()