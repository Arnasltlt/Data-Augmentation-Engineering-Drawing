"""
Planner Feedback Loop System - Fixed Version
Phase 6: Auto-requests revised plans from LLM when validation fails
"""

import json
import tempfile
from typing import Dict, Any, Optional, Tuple, List
import openai

from ai_planner import create_plan_from_prompt
from src.validator.plan_validator import DrawingPlanValidator
from src.validator.drawing_standards_validator import DrawingStandardsValidator
from src.solid_validator import SolidValidator


class PlannerFeedbackLoop:
    """Manages iterative plan refinement with LLM feedback."""
    
    def __init__(self, client: openai.OpenAI, max_iterations: int = 3):
        """
        Initialize feedback loop system.
        
        Args:
            client: OpenAI client instance
            max_iterations: Maximum number of revision attempts
        """
        self.client = client
        self.max_iterations = max_iterations
        self.plan_validator = DrawingPlanValidator()
        self.standards_validator = DrawingStandardsValidator()
        self.solid_validator = SolidValidator()
    
    def generate_validated_plan(self, prompt: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Generate a plan with iterative validation and feedback.
        
        Args:
            prompt: Initial prompt for plan generation
            
        Returns:
            Tuple of (final_plan, feedback_history)
        """
        
        feedback_history = []
        current_prompt = prompt
        
        for iteration in range(self.max_iterations):
            print(f"🔄 Iteration {iteration + 1}/{self.max_iterations}")
            
            # Generate plan
            plan = create_plan_from_prompt(self.client, current_prompt)
            if not plan:
                feedback_history.append(f"Iteration {iteration + 1}: Failed to generate plan")
                continue
            
            # Validate the plan
            validation_results = self._comprehensive_validation(plan)
            
            if validation_results['is_valid']:
                feedback_history.append(f"Iteration {iteration + 1}: Plan validated successfully")
                print(f"✅ Plan validated on iteration {iteration + 1}")
                return plan, feedback_history
            
            # Plan failed validation - generate feedback
            feedback = self._generate_feedback(validation_results)
            feedback_history.append(f"Iteration {iteration + 1}: {feedback}")
            
            # Create revised prompt
            current_prompt = self._create_revision_prompt(prompt, feedback, plan)
            
            print(f"⚠️ Validation failed, generating revision...")
        
        # Max iterations reached
        feedback_history.append(f"Max iterations ({self.max_iterations}) reached without valid plan")
        print(f"❌ Failed to generate valid plan after {self.max_iterations} iterations")
        return None, feedback_history
    
    def _comprehensive_validation(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Run all validation checks on a plan."""
        
        results = {
            'is_valid': True,
            'schema_valid': True,
            'schema_errors': [],
            'solid_valid': True,
            'solid_errors': [],
            'standards_score': 1.0,
            'standards_errors': []
        }
        
        # Schema validation
        try:
            schema_valid, schema_errors = self.plan_validator.validate_plan(plan)
            results['schema_valid'] = schema_valid
            results['schema_errors'] = schema_errors
            
            if not schema_valid:
                results['is_valid'] = False
        except Exception as e:
            results['schema_valid'] = False
            results['schema_errors'] = [f"Schema validation error: {str(e)}"]
            results['is_valid'] = False
        
        # 3D solid validation (if schema is valid)
        if results['schema_valid']:
            try:
                solid_valid, solid_errors, collisions = self.solid_validator.validate_plan(plan)
                
                # Filter out expected collisions (features with base)
                unexpected_collisions = self._filter_expected_collisions(collisions)
                
                results['solid_valid'] = len(unexpected_collisions) == 0
                results['solid_errors'] = [error for error in solid_errors 
                                         if not self._is_expected_collision_error(error)]
                
                if not results['solid_valid']:
                    results['is_valid'] = False
            except Exception as e:
                results['solid_valid'] = False
                results['solid_errors'] = [f"3D validation error: {str(e)}"]
                results['is_valid'] = False
        
        return results
    
    def _filter_expected_collisions(self, collisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out expected collisions (e.g., holes with base feature)."""
        
        unexpected = []
        
        for collision in collisions:
            # Expected: Features (Cylinder/Box) intersecting with base (Box at origin)
            is_base_feature_collision = (
                (collision['geometry1_center'] == [0, 0, 0] or 
                 collision['geometry2_center'] == [0, 0, 0]) and
                (collision['geometry1_type'] != collision['geometry2_type'])
            )
            
            if not is_base_feature_collision:
                unexpected.append(collision)
        
        return unexpected
    
    def _is_expected_collision_error(self, error: str) -> bool:
        """Check if an error message describes an expected collision."""
        return "at [0, 0, 0]" in error and ("Cylinder" in error or "Box" in error)
    
    def _generate_feedback(self, validation_results: Dict[str, Any]) -> str:
        """Generate human-readable feedback from validation results."""
        
        feedback_parts = []
        
        if not validation_results['schema_valid']:
            feedback_parts.append("Schema validation failed:")
            for error in validation_results['schema_errors']:
                feedback_parts.append(f"  - {error}")
        
        if not validation_results['solid_valid']:
            feedback_parts.append("3D geometry validation failed:")
            for error in validation_results['solid_errors']:
                feedback_parts.append(f"  - {error}")
        
        return " ".join(feedback_parts)
    
    def _create_revision_prompt(self, original_prompt: str, feedback: str, failed_plan: Dict[str, Any]) -> str:
        """Create a revised prompt incorporating feedback."""
        
        revision_prompt = (
            "Revise the following engineering drawing plan based on validation feedback.\n\n"
            f"Original Request: {original_prompt}\n\n"
            f"Validation Feedback: {feedback}\n\n"
            "Previous Plan Issues:\n"
            f"{json.dumps(failed_plan, indent=2)}\n\n"
            "Please generate a corrected plan that addresses these validation issues while maintaining the original design intent."
        )
        
        return revision_prompt


def generate_plan_with_feedback(client: openai.OpenAI, prompt: str, max_iterations: int = 3) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Convenience function for generating validated plans."""
    
    feedback_loop = PlannerFeedbackLoop(client, max_iterations)
    return feedback_loop.generate_validated_plan(prompt)


if __name__ == "__main__":
    import sys
    import os
    
    if len(sys.argv) < 3:
        print("Usage: python planner_feedback_fixed.py <api_key> <prompt>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    prompt = sys.argv[2]
    
    client = openai.OpenAI(api_key=api_key)
    
    plan, history = generate_plan_with_feedback(client, prompt)
    
    print(f"\n🎯 Feedback Loop Results:")
    print(f"=" * 40)
    
    for entry in history:
        print(f"  {entry}")
    
    if plan:
        print(f"\n✅ Final Plan Generated:")
        print(json.dumps(plan, indent=2))
    else:
        print(f"\n❌ Failed to generate valid plan")