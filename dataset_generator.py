#!/usr/bin/env python3
"""
Dataset Generator CLI
Phase 6: Batch generation of engineering drawings with noise and ground truth
"""

import argparse
import json
import os
import sys
import time
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import openai

from generator import generate_from_plan
from prompt_factory import generate_random_prompt
from ai_planner import create_plan_from_prompt
from src.planner_feedback import generate_plan_with_feedback
from src.noise_generator import DrawingNoiseGenerator, generate_noisy_dataset
import tempfile
import shutil


def generate_single_drawing(args: argparse.Namespace, drawing_id: int) -> Dict[str, Any]:
    """
    Generate a single drawing with all outputs.
    
    Args:
        args: Command line arguments
        drawing_id: Unique drawing identifier
        
    Returns:
        Dictionary with generation results
    """
    
    result = {
        'drawing_id': drawing_id,
        'success': False,
        'prompt': '',
        'plan_path': '',
        'dxf_path': '',
        'png_path': '',
        'noisy_paths': [],
        'generation_time': 0.0,
        'error': ''
    }
    
    start_time = time.time()
    
    try:
        # Generate random prompt or use provided one
        if args.prompts_file:
            # Read prompts from file
            with open(args.prompts_file, 'r') as f:
                prompts = [line.strip() for line in f if line.strip()]
            
            if drawing_id < len(prompts):
                prompt = prompts[drawing_id]
            else:
                prompt = generate_random_prompt()
        else:
            prompt = generate_random_prompt()
        
        result['prompt'] = prompt
        
        # Generate plan using feedback loop if enabled
        if args.use_feedback:
            plan, feedback_history = generate_plan_with_feedback(
                args.client, prompt, max_iterations=3
            )
            if not plan:
                result['error'] = f"Failed to generate valid plan after feedback: {feedback_history[-1] if feedback_history else 'Unknown error'}"
                return result
        else:
            plan = create_plan_from_prompt(args.client, prompt)
            if not plan:
                result['error'] = "Failed to generate plan"
                return result
        
        # Create unique filename based on content hash
        plan_content = json.dumps(plan, sort_keys=True)
        content_hash = hashlib.md5(plan_content.encode()).hexdigest()[:8]
        base_filename = f"drawing_{drawing_id:06d}_{content_hash}"
        
        # Save plan
        plan_path = os.path.join(args.output_dir, f"{base_filename}.json")
        with open(plan_path, 'w') as f:
            json.dump(plan, f, indent=2)
        result['plan_path'] = plan_path
        
        # Generate DXF
        dxf_path = os.path.join(args.output_dir, f"{base_filename}.dxf")
        generate_from_plan(plan_path, dxf_path, visualize=True, validate=True)
        result['dxf_path'] = dxf_path
        
        # PNG should be generated automatically
        png_path = os.path.join(args.output_dir, f"{base_filename}.png")
        result['png_path'] = png_path
        
        # Generate noisy versions if requested
        if args.messy > 0 and os.path.exists(png_path):
            noisy_dir = os.path.join(args.output_dir, "noisy")
            os.makedirs(noisy_dir, exist_ok=True)
            
            # Generate multiple noise levels
            noise_levels = [0.3, 0.6, 1.0, 1.5]
            for i, noise_level in enumerate(noise_levels[:int(args.messy * 4)]):
                noise_generator = DrawingNoiseGenerator(noise_level)
                noisy_filename = f"{base_filename}_noisy_{i+1:02d}_level_{noise_level:.1f}.png"
                noisy_path = os.path.join(noisy_dir, noisy_filename)
                
                if noise_generator.add_noise_to_png(png_path, noisy_path):
                    result['noisy_paths'].append(noisy_path)
        
        result['success'] = True
        result['generation_time'] = time.time() - start_time
        
        print(f"✅ Generated drawing {drawing_id:06d} ({result['generation_time']:.1f}s)")
        
    except Exception as e:
        result['error'] = str(e)
        result['generation_time'] = time.time() - start_time
        print(f"❌ Failed drawing {drawing_id:06d}: {e}")
    
    return result


def generate_dataset(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Generate a complete dataset of engineering drawings.
    
    Args:
        args: Command line arguments
        
    Returns:
        Dictionary with dataset generation statistics
    """
    
    print(f"🚀 Starting dataset generation:")
    print(f"   Count: {args.count}")
    print(f"   Output: {args.output_dir}")
    print(f"   Noise level: {args.messy}")
    print(f"   Workers: {args.workers}")
    print(f"   Feedback loop: {'enabled' if args.use_feedback else 'disabled'}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize OpenAI client
    args.client = openai.OpenAI(api_key=args.api_key)
    
    # Generate drawings
    start_time = time.time()
    results = []
    
    if args.workers > 1:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(generate_single_drawing, args, i)
                for i in range(args.count)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
    else:
        # Sequential processing
        for i in range(args.count):
            results.append(generate_single_drawing(args, i))
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    total_noisy = sum(len(r['noisy_paths']) for r in successful)
    avg_time = sum(r['generation_time'] for r in results) / len(results) if results else 0
    throughput = len(successful) / (total_time / 60)  # drawings per minute
    
    stats = {
        'total_requested': args.count,
        'successful': len(successful),
        'failed': len(failed),
        'success_rate': len(successful) / args.count * 100 if args.count > 0 else 0,
        'total_time_minutes': total_time / 60,
        'average_generation_time': avg_time,
        'throughput_per_minute': throughput,
        'noisy_variants_generated': total_noisy,
        'output_directory': args.output_dir
    }
    
    # Save dataset manifest
    manifest = {
        'generation_stats': stats,
        'drawings': results,
        'generation_args': {
            'count': args.count,
            'messy': args.messy,
            'use_feedback': args.use_feedback,
            'prompts_file': args.prompts_file
        }
    }
    
    manifest_path = os.path.join(args.output_dir, 'dataset_manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Generate datasets of engineering drawings with ground truth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 100 drawings with moderate noise
  python dataset_generator.py --count 100 --messy 1.0 --output ./dataset

  # Generate from specific prompts file  
  python dataset_generator.py --prompts prompts.txt --count 50 --output ./custom_dataset

  # High-throughput generation with feedback loop
  python dataset_generator.py --count 1000 --workers 4 --use-feedback --output ./large_dataset
        """
    )
    
    parser.add_argument('--count', type=int, default=10,
                       help='Number of drawings to generate (default: 10)')
    
    parser.add_argument('--output', type=str, default='./dataset_output',
                       dest='output_dir',
                       help='Output directory for dataset (default: ./dataset_output)')
    
    parser.add_argument('--prompts', type=str, dest='prompts_file',
                       help='File containing prompts (one per line)')
    
    parser.add_argument('--messy', type=float, default=1.0,
                       help='Noise level for messy variants (0.0-2.0, default: 1.0)')
    
    parser.add_argument('--workers', type=int, default=1,
                       help='Number of parallel workers (default: 1)')
    
    parser.add_argument('--use-feedback', action='store_true',
                       help='Use planner feedback loop for validation')
    
    parser.add_argument('--api-key', type=str,
                       help='OpenAI API key (or set OPENAI_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Get API key
    if not args.api_key:
        args.api_key = os.environ.get('OPENAI_API_KEY')
    
    if not args.api_key:
        print("❌ OpenAI API key required. Use --api-key or set OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
    # Generate dataset
    stats = generate_dataset(args)
    
    # Print results
    print(f"\n🎯 Dataset Generation Complete!")
    print(f"=" * 50)
    print(f"Total Requested:       {stats['total_requested']}")
    print(f"Successfully Generated: {stats['successful']}")
    print(f"Failed:                {stats['failed']}")
    print(f"Success Rate:          {stats['success_rate']:.1f}%")
    print(f"Total Time:            {stats['total_time_minutes']:.1f} minutes")
    print(f"Average Time/Drawing:  {stats['average_generation_time']:.1f} seconds")
    print(f"Throughput:            {stats['throughput_per_minute']:.1f} drawings/minute")
    print(f"Noisy Variants:        {stats['noisy_variants_generated']}")
    print(f"Output Directory:      {stats['output_directory']}")
    
    # Exit with error code if too many failures
    if stats['success_rate'] < 80:
        print(f"\n⚠️ Low success rate ({stats['success_rate']:.1f}%) - check configuration")
        sys.exit(1)
    else:
        print(f"\n✅ Dataset generation successful!")
        sys.exit(0)


if __name__ == "__main__":
    main()