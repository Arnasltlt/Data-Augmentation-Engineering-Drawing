"""
Drawing Standards Validator
Phase 5: Validates drawings against drafting standards and completeness rules
"""

import ezdxf
import json
from typing import List, Tuple, Dict, Any


class DrawingStandardsValidator:
    """Validates drawings against engineering drafting standards."""
    
    def __init__(self):
        self.validation_rules = {
            'dimension_completeness': True,
            'layer_compliance': True,
            'symbol_usage': True,
            'title_block_completeness': True,
            'annotation_standards': True
        }
    
    def validate_drawing(self, dxf_path: str, plan: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, float]]:
        """
        Validates a drawing against drafting standards.
        Returns: (is_valid, error_list, scores_dict)
        """
        errors = []
        scores = {}
        
        try:
            doc = ezdxf.readfile(dxf_path)
            
            # Run all validation checks
            dimension_score = self._check_dimension_completeness(doc, plan)
            layer_score = self._check_layer_compliance(doc)
            symbol_score = self._check_symbol_usage(doc, plan)
            title_score = self._check_title_block_completeness(doc, plan)
            annotation_score = self._check_annotation_standards(doc)
            
            scores = {
                'dimension_completeness': dimension_score,
                'layer_compliance': layer_score,
                'symbol_usage': symbol_score,
                'title_block_completeness': title_score,
                'annotation_standards': annotation_score
            }
            
            # Collect errors based on scores
            if dimension_score < 0.95:
                errors.append(f"Dimension completeness: {dimension_score:.1%} (target: ≥95%)")
            if layer_score < 1.0:
                errors.append(f"Layer compliance: {layer_score:.1%} (target: 100%)")
            if symbol_score < 0.8:
                errors.append(f"Symbol usage: {symbol_score:.1%} (target: ≥80%)")
            if title_score < 1.0:
                errors.append(f"Title block completeness: {title_score:.1%} (target: 100%)")
            if annotation_score < 0.9:
                errors.append(f"Annotation standards: {annotation_score:.1%} (target: ≥90%)")
            
            is_valid = len(errors) == 0
            
        except Exception as e:
            errors.append(f"Failed to validate drawing: {str(e)}")
            scores = {key: 0.0 for key in self.validation_rules.keys()}
            is_valid = False
        
        return is_valid, errors, scores
    
    def _check_dimension_completeness(self, doc, plan: Dict[str, Any]) -> float:
        """Check what percentage of features are properly dimensioned."""
        
        # Count dimensions in the drawing
        dimension_count = 0
        for entity in doc.modelspace():
            if entity.dxftype() in ['DIMENSION', 'QDIM', 'LEADER']:
                dimension_count += 1
        
        # Calculate expected dimensions based on features
        base_feature = plan.get('base_feature', {})
        modifying_features = plan.get('modifying_features', [])
        
        expected_dimensions = 0
        
        # Base feature should have 2 dimensions (width, height or diameter)
        if base_feature.get('shape') == 'rectangle':
            expected_dimensions += 2  # width + height
        elif base_feature.get('shape') == 'circle':
            expected_dimensions += 1  # diameter
        
        # Each modifying feature should have at least 1 dimension
        for feature in modifying_features:
            feature_type = feature.get('type')
            if feature_type in ['hole', 'counterbore', 'countersink', 'tapped_hole']:
                expected_dimensions += 1  # diameter
            elif feature_type == 'slot':
                expected_dimensions += 2  # width + length
            # fillets and chamfers don't always need explicit dimensions
        
        if expected_dimensions == 0:
            return 1.0
        
        completion_rate = min(dimension_count / expected_dimensions, 1.0)
        return completion_rate
    
    def _check_layer_compliance(self, doc) -> float:
        """Check if all required layers are present and properly used."""
        
        required_layers = ['OUTLINE', 'HIDDEN', 'CENTER', 'CONSTRUCTION', 'DIMENSIONS', 'TEXT']
        existing_layers = [layer.dxf.name for layer in doc.layers]
        
        present_layers = [layer for layer in required_layers if layer in existing_layers]
        compliance_rate = len(present_layers) / len(required_layers)
        
        return compliance_rate
    
    def _check_symbol_usage(self, doc, plan: Dict[str, Any]) -> float:
        """Check appropriate use of symbols and annotations."""
        
        # Count block references (symbols)
        symbol_count = 0
        for entity in doc.modelspace():
            if entity.dxftype() == 'INSERT':
                symbol_count += 1
        
        # Count text entities (annotations)
        text_count = 0
        for entity in doc.modelspace():
            if entity.dxftype() in ['TEXT', 'MTEXT']:
                text_count += 1
        
        # Simple heuristic: expect at least some symbols/text based on complexity
        modifying_features = plan.get('modifying_features', [])
        feature_count = len(modifying_features)
        
        # Expect at least 1 symbol/text per 2 features, minimum of 3
        expected_annotations = max(3, feature_count // 2)
        
        total_annotations = symbol_count + text_count
        usage_rate = min(total_annotations / expected_annotations, 1.0)
        
        return usage_rate
    
    def _check_title_block_completeness(self, doc, plan: Dict[str, Any]) -> float:
        """Check if title block contains all required information."""
        
        title_block_data = plan.get('title_block', {})
        
        required_fields = [
            'drawing_title', 'drawing_number', 'date', 'drawn_by', 
            'scale', 'material', 'finish', 'revision'
        ]
        
        present_fields = []
        for field in required_fields:
            value = title_block_data.get(field)
            if value and value != 'N/A' and value != 'TBD':
                present_fields.append(field)
        
        completeness_rate = len(present_fields) / len(required_fields)
        return completeness_rate
    
    def _check_annotation_standards(self, doc) -> float:
        """Check if annotations follow standard conventions."""
        
        # Check for proper layer usage in annotations
        dimension_entities = []
        text_entities = []
        
        for entity in doc.modelspace():
            if entity.dxftype() in ['DIMENSION', 'QDIM']:
                dimension_entities.append(entity)
            elif entity.dxftype() in ['TEXT', 'MTEXT']:
                text_entities.append(entity)
        
        # Check if dimensions are on DIMENSIONS layer
        correct_dimension_layers = 0
        for dim in dimension_entities:
            if hasattr(dim.dxf, 'layer') and dim.dxf.layer == 'DIMENSIONS':
                correct_dimension_layers += 1
        
        # Check if text is on TEXT layer  
        correct_text_layers = 0
        for text in text_entities:
            if hasattr(text.dxf, 'layer') and text.dxf.layer == 'TEXT':
                correct_text_layers += 1
        
        total_annotations = len(dimension_entities) + len(text_entities)
        if total_annotations == 0:
            return 1.0
        
        correct_annotations = correct_dimension_layers + correct_text_layers
        standards_compliance = correct_annotations / total_annotations
        
        return standards_compliance


def validate_drawing_file(dxf_path: str, plan_path: str = None) -> Dict[str, Any]:
    """
    Validate a drawing file against standards.
    
    Args:
        dxf_path: Path to DXF file
        plan_path: Optional path to JSON plan file
    
    Returns:
        Dictionary with validation results
    """
    
    # Load plan if provided
    plan = {}
    if plan_path:
        try:
            with open(plan_path, 'r') as f:
                plan = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load plan file: {e}")
    
    validator = DrawingStandardsValidator()
    is_valid, errors, scores = validator.validate_drawing(dxf_path, plan)
    
    # Calculate overall score
    overall_score = sum(scores.values()) / len(scores) if scores else 0.0
    
    return {
        'is_valid': is_valid,
        'overall_score': overall_score,
        'individual_scores': scores,
        'errors': errors,
        'recommendations': _generate_recommendations(scores)
    }


def _generate_recommendations(scores: Dict[str, float]) -> List[str]:
    """Generate improvement recommendations based on scores."""
    
    recommendations = []
    
    if scores.get('dimension_completeness', 1.0) < 0.95:
        recommendations.append("Add missing dimensions to fully define all features")
    
    if scores.get('layer_compliance', 1.0) < 1.0:
        recommendations.append("Ensure all required CAD layers are present and properly named")
    
    if scores.get('symbol_usage', 1.0) < 0.8:
        recommendations.append("Add more symbols and annotations for clarity")
    
    if scores.get('title_block_completeness', 1.0) < 1.0:
        recommendations.append("Complete all required title block fields")
    
    if scores.get('annotation_standards', 1.0) < 0.9:
        recommendations.append("Place annotations on correct layers per CAD standards")
    
    if not recommendations:
        recommendations.append("Drawing meets all standards requirements")
    
    return recommendations


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python drawing_standards_validator.py <dxf_file> [plan_file]")
        sys.exit(1)
    
    dxf_file = sys.argv[1]
    plan_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    results = validate_drawing_file(dxf_file, plan_file)
    
    print(f"📊 Drawing Standards Validation Report")
    print(f"=" * 50)
    print(f"Overall Score: {results['overall_score']:.1%}")
    print(f"Valid: {'✅ Yes' if results['is_valid'] else '❌ No'}")
    
    print(f"\n📋 Individual Scores:")
    for metric, score in results['individual_scores'].items():
        print(f"  {metric}: {score:.1%}")
    
    if results['errors']:
        print(f"\n❌ Issues Found:")
        for error in results['errors']:
            print(f"  - {error}")
    
    if results['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in results['recommendations']:
            print(f"  - {rec}")