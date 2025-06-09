"""
AI Planner Module

Converts natural language descriptions into structured JSON drawing plans
using OpenAI's GPT models.
"""

import json
import os
import yaml
from typing import Dict, Any, Optional
from datetime import datetime
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIPlanner:
    """Converts natural language prompts to JSON drawing plans"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI Planner with OpenAI API key"""
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        self.client = openai.OpenAI(api_key=api_key)
        
        # Load symbol manifest for context
        self.symbol_manifest = self._load_symbol_manifest()
        
    def _load_symbol_manifest(self) -> Dict[str, Any]:
        """Load the symbol manifest for AI context"""
        try:
            manifest_path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'symbols', 'symbols_manifest.yaml'
            )
            with open(manifest_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load symbol manifest: {e}")
            return {"symbols": []}
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with engineering context"""
        
        # Get available symbols for context
        available_symbols = [s['name'] for s in self.symbol_manifest.get('symbols', [])]
        symbol_categories = {
            'GD&T': [s for s in available_symbols if s.startswith('gdt_')],
            'Surface Finish': [s for s in available_symbols if s.startswith('surface_')],
            'Welding': [s for s in available_symbols if s.startswith('weld_')],
            'Threading': [s for s in available_symbols if s.startswith('thread_')],
            'Dimensions': [s for s in available_symbols if s.endswith('_symbol')],
            'Machining': ['counterbore', 'countersink', 'spotface_symbol']
        }
        
        system_prompt = f"""You are an expert mechanical engineer and technical draftsperson. Your task is to convert natural language descriptions of mechanical parts into structured JSON drawing plans that can be rendered as professional engineering drawings.

CRITICAL REQUIREMENTS:
1. Output ONLY valid JSON - no explanations, no markdown formatting
2. Follow the exact schema structure provided
3. Use engineering best practices for dimensioning and annotation
4. All dimensions in millimeters unless specified otherwise
5. Place symbols logically near relevant features

AVAILABLE SYMBOLS BY CATEGORY:
"""
        
        for category, symbols in symbol_categories.items():
            if symbols:
                system_prompt += f"\n{category}: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}"
        
        system_prompt += f"""

JSON SCHEMA STRUCTURE:
{{
  "geometry": {{
    "lines": [{{ "start": [x, y], "end": [x, y] }}],
    "circles": [{{ "center": [x, y], "radius": number }}],
    "arcs": [{{ "center": [x, y], "radius": number, "start_angle": degrees, "end_angle": degrees }}],
    "rectangles": [{{ "corner1": [x, y], "corner2": [x, y] }}]
  }},
  "annotations": {{
    "dimensions": [{{
      "type": "linear|diameter|radius",
      "p1": [x, y], "p2": [x, y], "base": [x, y],  // for linear
      "center": [x, y], "radius": number, "location": [x, y]  // for diameter/radius
    }}],
    "symbols": [{{
      "name": "symbol_name_from_available_list",
      "location": [x, y],
      "rotation": 0,
      "scale": 1.0
    }}],
    "notes": [{{
      "text": "ALL DIMENSIONS IN MM",
      "location": [x, y],
      "height": 3.5
    }}]
  }},
  "title_block": {{
    "drawing_title": "Part Name",
    "drawing_number": "Part-001",
    "scale": "1:1",
    "date": "{datetime.now().strftime('%Y-%m-%d')}",
    "drawn_by": "AI Generator",
    "material": "Steel/Aluminum/etc",
    "finish": "Mill Finish/Anodized/etc"
  }}
}}

ENGINEERING BEST PRACTICES:
- Center geometric features appropriately in coordinate space
- Place dimensions outside the part boundaries
- Use diameter symbols for holes, radius symbols for fillets
- Add surface finish symbols near machined surfaces
- Include GD&T callouts for critical features
- Add threading callouts for threaded holes
- Place welding symbols near weld locations
- Use standard drawing notes (materials, finishes, tolerances)
- Ensure dimension lines don't overlap geometry
- Place title block information consistently

COORDINATE SYSTEM:
- Origin at lower-left
- Positive X rightward, positive Y upward
- Plan for ~200x150mm drawing area
- Leave margins for dimensions and annotations

Remember: Output ONLY the JSON structure. No additional text or formatting."""

        return system_prompt
    
    def prompt_to_plan(self, user_prompt: str, model: str = "gpt-4") -> Dict[str, Any]:
        """
        Convert a natural language prompt to a JSON drawing plan
        
        Args:
            user_prompt: Natural language description of the part
            model: OpenAI model to use
            
        Returns:
            Dictionary containing the drawing plan
        """
        
        system_prompt = self._build_system_prompt()
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.3  # Lower temperature for more consistent technical output
            )
            
            # Extract the JSON response
            response_text = response.choices[0].message.content.strip()
            
            # Clean up response - remove any markdown formatting if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            # Parse the JSON
            plan = json.loads(response_text)
            
            # Add metadata
            if 'metadata' not in plan:
                plan['metadata'] = {}
            
            plan['metadata'].update({
                'generated_by': 'AI Planner',
                'source_prompt': user_prompt,
                'created_date': datetime.now().isoformat(),
                'model_used': model
            })
            
            return plan
            
        except json.JSONDecodeError as e:
            raise ValueError(f"AI response was not valid JSON: {e}\\nResponse: {response_text}")
        except Exception as e:
            raise RuntimeError(f"Failed to generate plan: {e}")
    
    def generate_and_validate_plan(self, user_prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Generate a plan with validation and retry logic
        
        Args:
            user_prompt: Natural language description
            max_retries: Maximum number of retry attempts
            
        Returns:
            Validated drawing plan
        """
        from ..validator.plan_validator import DrawingPlanValidator
        
        validator = DrawingPlanValidator()
        
        for attempt in range(max_retries):
            try:
                print(f"Generating plan (attempt {attempt + 1}/{max_retries})...")
                
                plan = self.prompt_to_plan(user_prompt)
                
                # Validate the generated plan
                is_valid, errors = validator.validate_plan(plan)
                
                if is_valid:
                    print("✅ Generated valid plan")
                    return plan
                else:
                    print(f"❌ Generated plan has validation errors:")
                    for error in errors[:3]:  # Show first 3 errors
                        print(f"  - {error}")
                    
                    if attempt < max_retries - 1:
                        print("Retrying with error feedback...")
                        # Add error feedback to the prompt
                        error_feedback = f"Previous attempt failed validation with errors: {'; '.join(errors[:2])}. Please fix these issues."
                        user_prompt_with_feedback = f"{user_prompt}\\n\\nIMPORTANT: {error_feedback}"
                        user_prompt = user_prompt_with_feedback
            
            except Exception as e:
                print(f"❌ Error in attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
        
        raise RuntimeError(f"Failed to generate valid plan after {max_retries} attempts")


def generate_plan_from_prompt(prompt: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to generate a plan from a prompt
    
    Args:
        prompt: Natural language description of the part
        output_path: Optional path to save the generated plan
        
    Returns:
        Generated drawing plan
    """
    planner = AIPlanner()
    plan = planner.generate_and_validate_plan(prompt)
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(plan, f, indent=2)
        print(f"Plan saved to: {output_path}")
    
    return plan


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python planner.py '<description>' [output_file.json]")
        sys.exit(1)
    
    description = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        plan = generate_plan_from_prompt(description, output_file)
        print("\\nGenerated plan successfully!")
        if not output_file:
            print(json.dumps(plan, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)