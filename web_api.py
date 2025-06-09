#!/usr/bin/env python3
"""
Web API for Intelligent Drawing Generator
Phase 6: RESTful API for drawing generation and dataset creation
"""

import os
import sys
import json
import time
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import openai

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from generator import generate_from_plan
from prompt_factory import generate_random_prompt
from ai_planner import create_plan_from_prompt
from src.planner_feedback import generate_plan_with_feedback
from src.validator.drawing_standards_validator import validate_drawing_file
from src.solid_validator import validate_drawing_plan_3d
from dataset_generator import generate_dataset
from src.noise_generator import DrawingNoiseGenerator


# Pydantic models for API
class DrawingRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of the drawing")
    use_feedback: bool = Field(False, description="Use planner feedback loop for validation")
    generate_noise: bool = Field(False, description="Generate noisy variants")
    noise_level: float = Field(1.0, ge=0.0, le=2.0, description="Noise level for variants")


class DrawingPlan(BaseModel):
    title_block: Dict[str, Any]
    base_feature: Dict[str, Any]
    modifying_features: List[Dict[str, Any]]
    annotations: Optional[Dict[str, Any]] = None


class DatasetRequest(BaseModel):
    count: int = Field(10, ge=1, le=1000, description="Number of drawings to generate")
    prompts: Optional[List[str]] = Field(None, description="Custom prompts (optional)")
    messy: float = Field(1.0, ge=0.0, le=2.0, description="Noise level for messy variants")
    use_feedback: bool = Field(False, description="Use planner feedback loop")


class ValidationRequest(BaseModel):
    plan: DrawingPlan


# FastAPI app
app = FastAPI(
    title="Intelligent Drawing Generator API",
    description="Generate engineering drawings from natural language descriptions",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
openai_client = None
output_dir = Path("./api_output")
output_dir.mkdir(exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup."""
    global openai_client
    
    # Initialize OpenAI client
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        openai_client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
    else:
        print("⚠️ No OpenAI API key found - AI features will be disabled")
    
    print("🚀 Intelligent Drawing Generator API started")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Intelligent Drawing Generator API",
        "version": "6.0.0",
        "description": "Generate engineering drawings from natural language descriptions",
        "endpoints": {
            "health": "/health",
            "generate": "/generate",
            "validate": "/validate",
            "dataset": "/dataset",
            "random": "/random",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "api_key_configured": openai_client is not None,
        "output_directory": str(output_dir),
        "features": {
            "drawing_generation": True,
            "plan_validation": True,
            "noise_generation": True,
            "dataset_creation": True,
            "3d_validation": True
        }
    }


@app.post("/generate")
async def generate_drawing(request: DrawingRequest):
    """Generate a drawing from a natural language prompt."""
    
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI API not configured")
    
    try:
        start_time = time.time()
        
        # Generate plan
        if request.use_feedback:
            plan, feedback_history = generate_plan_with_feedback(
                openai_client, request.prompt, max_iterations=3
            )
            if not plan:
                raise HTTPException(status_code=400, detail=f"Failed to generate valid plan: {feedback_history[-1] if feedback_history else 'Unknown error'}")
        else:
            plan = create_plan_from_prompt(openai_client, request.prompt)
            if not plan:
                raise HTTPException(status_code=400, detail="Failed to generate plan from prompt")
        
        # Create unique filename
        prompt_hash = hashlib.md5(request.prompt.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        base_filename = f"api_drawing_{timestamp}_{prompt_hash}"
        
        # Save plan
        plan_path = output_dir / f"{base_filename}.json"
        with open(plan_path, 'w') as f:
            json.dump(plan, f, indent=2)
        
        # Generate DXF and PNG
        dxf_path = output_dir / f"{base_filename}.dxf"
        generate_from_plan(str(plan_path), str(dxf_path), visualize=True, validate=True)
        
        png_path = output_dir / f"{base_filename}.png"
        
        # Generate noisy variants if requested
        noisy_files = []
        if request.generate_noise and png_path.exists():
            noise_generator = DrawingNoiseGenerator(request.noise_level)
            noisy_path = output_dir / f"{base_filename}_noisy.png"
            
            if noise_generator.add_noise_to_png(str(png_path), str(noisy_path)):
                noisy_files.append(str(noisy_path))
        
        generation_time = time.time() - start_time
        
        # Return response
        return {
            "success": True,
            "generation_time": generation_time,
            "prompt": request.prompt,
            "files": {
                "plan": str(plan_path),
                "dxf": str(dxf_path),
                "png": str(png_path) if png_path.exists() else None,
                "noisy_variants": noisy_files
            },
            "plan_summary": {
                "title": plan.get("title_block", {}).get("drawing_title", "Untitled"),
                "base_feature": plan.get("base_feature", {}).get("shape", "unknown"),
                "feature_count": len(plan.get("modifying_features", []))
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/validate")
async def validate_plan(request: ValidationRequest):
    """Validate a drawing plan."""
    
    try:
        # Convert pydantic model to dict
        plan_dict = request.plan.dict()
        
        # Save plan to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(plan_dict, f, indent=2)
            plan_path = f.name
        
        try:
            # Run 3D validation
            solid_results = validate_drawing_plan_3d(plan_path)
            
            # Generate DXF for standards validation
            dxf_path = plan_path.replace('.json', '.dxf')
            generate_from_plan(plan_path, dxf_path, visualize=False, validate=False)
            
            # Run standards validation
            standards_results = validate_drawing_file(dxf_path, plan_path)
            
            return {
                "plan_valid": True,
                "solid_validation": {
                    "valid": solid_results['is_valid'],
                    "collision_count": solid_results['collision_count'],
                    "errors": solid_results['errors']
                },
                "standards_validation": {
                    "overall_score": standards_results['overall_score'],
                    "individual_scores": standards_results['individual_scores'],
                    "recommendations": standards_results['recommendations']
                }
            }
            
        finally:
            # Clean up temporary files
            for temp_file in [plan_path, dxf_path]:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.get("/random")
async def generate_random_drawing():
    """Generate a drawing from a random prompt."""
    
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI API not configured")
    
    try:
        # Generate random prompt
        random_prompt = generate_random_prompt()
        
        # Use the generate endpoint with the random prompt
        request = DrawingRequest(prompt=random_prompt, generate_noise=True)
        return await generate_drawing(request)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Random generation failed: {str(e)}")


@app.post("/dataset")
async def create_dataset(request: DatasetRequest, background_tasks: BackgroundTasks):
    """Create a dataset of drawings (runs in background)."""
    
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI API not configured")
    
    # Generate unique dataset ID
    dataset_id = f"dataset_{int(time.time())}"
    dataset_dir = output_dir / dataset_id
    
    # Start dataset generation in background
    background_tasks.add_task(
        _generate_dataset_background,
        openai_client,
        request,
        dataset_dir
    )
    
    return {
        "dataset_id": dataset_id,
        "status": "started",
        "estimated_time_minutes": request.count * 0.5,  # Rough estimate
        "check_status_url": f"/dataset/{dataset_id}/status"
    }


@app.get("/dataset/{dataset_id}/status")
async def get_dataset_status(dataset_id: str):
    """Get status of dataset generation."""
    
    dataset_dir = output_dir / dataset_id
    manifest_path = dataset_dir / "dataset_manifest.json"
    
    if not dataset_dir.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if manifest_path.exists():
        # Dataset complete
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        return {
            "dataset_id": dataset_id,
            "status": "completed",
            "stats": manifest.get("generation_stats", {}),
            "download_url": f"/dataset/{dataset_id}/download"
        }
    else:
        # Dataset in progress - count files
        drawing_files = list(dataset_dir.glob("*.dxf"))
        
        return {
            "dataset_id": dataset_id,
            "status": "in_progress",
            "files_generated": len(drawing_files)
        }


@app.get("/dataset/{dataset_id}/download")
async def download_dataset(dataset_id: str):
    """Download dataset as ZIP file."""
    
    dataset_dir = output_dir / dataset_id
    
    if not dataset_dir.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Create ZIP file
    import zipfile
    zip_path = output_dir / f"{dataset_id}.zip"
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path in dataset_dir.rglob('*'):
            if file_path.is_file():
                zipf.write(file_path, file_path.relative_to(dataset_dir))
    
    return FileResponse(
        path=str(zip_path),
        filename=f"{dataset_id}.zip",
        media_type="application/zip"
    )


@app.get("/files/{filename}")
async def download_file(filename: str):
    """Download a generated file."""
    
    file_path = output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    suffix = file_path.suffix.lower()
    media_types = {
        '.dxf': 'application/dxf',
        '.png': 'image/png',
        '.json': 'application/json'
    }
    
    media_type = media_types.get(suffix, 'application/octet-stream')
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )


async def _generate_dataset_background(client: openai.OpenAI, request: DatasetRequest, dataset_dir: Path):
    """Background task for dataset generation."""
    
    try:
        # Create dataset directory
        dataset_dir.mkdir(exist_ok=True)
        
        # Prepare arguments (simulate argparse.Namespace)
        class Args:
            def __init__(self):
                self.count = request.count
                self.output_dir = str(dataset_dir)
                self.prompts_file = None
                self.messy = request.messy
                self.workers = 1
                self.use_feedback = request.use_feedback
                self.client = client
        
        args = Args()
        
        # Write custom prompts to file if provided
        if request.prompts:
            prompts_file = dataset_dir / "custom_prompts.txt"
            with open(prompts_file, 'w') as f:
                for prompt in request.prompts:
                    f.write(f"{prompt}\n")
            args.prompts_file = str(prompts_file)
        
        # Generate dataset
        from dataset_generator import generate_dataset
        stats = generate_dataset(args)
        
        print(f"✅ Dataset {dataset_dir.name} completed: {stats['successful']} drawings")
        
    except Exception as e:
        print(f"❌ Dataset generation failed: {e}")
        
        # Create error file
        error_file = dataset_dir / "generation_error.txt"
        with open(error_file, 'w') as f:
            f.write(f"Dataset generation failed: {str(e)}")


if __name__ == "__main__":
    # Command line options
    import argparse
    
    parser = argparse.ArgumentParser(description="Web API for Intelligent Drawing Generator")
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    
    args = parser.parse_args()
    
    print(f"🌐 Starting Web API on {args.host}:{args.port}")
    
    uvicorn.run(
        "web_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )