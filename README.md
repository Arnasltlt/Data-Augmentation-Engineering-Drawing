# GD&T Extraction Model Evaluation Framework

Replicates the methodology from "Fine-Tuning Vision-Language Model for Automated Engineering Drawing Information Extraction" to evaluate new vision-language models on Geometric Dimensioning and Tolerancing extraction tasks.

## Overview

This framework implements the exact evaluation methodology from the research paper to test new vision models like GPT-4.1, Claude Sonnet 4, and others on engineering drawing analysis.

## Features

- **Exact methodology replication** from the academic paper
- **Zero-shot evaluation** for new vision-language models
- **Same metrics**: Precision, Recall, F1-score, Hallucination rate
- **Compatible dataset format** with JSON annotations
- **Automated comparison** with baseline models
- **Visualization and reporting** tools

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API keys**:
   ```bash
   export OPENAI_API_KEY="your_openai_key"
   export ANTHROPIC_API_KEY="your_anthropic_key"
   ```

3. **Run evaluation**:
   ```bash
   python run_evaluation.py
   ```

## Dataset Format

The framework expects:
- **Images**: PNG format engineering drawings
- **Annotations**: JSON format with:
  - `geometric_characteristics`: GD&T symbols, tolerances, datums
  - `datum_features`: Datum labels and feature types  
  - `dimensions`: Nominal values and tolerances

## Adding New Models

Edit `run_evaluation.py` and add to `MODELS_TO_TEST`:
```python
("model-name", "openai" | "anthropic")
```

## Paper Reference

Based on: "Fine-Tuning Vision-Language Model for Automated Engineering Drawing Information Extraction" by Khan et al.

## File Structure

- `evaluation_metrics.py`: Core metrics implementation
- `dataset_utils.py`: Dataset loading and annotation handling
- `model_evaluator.py`: Model inference and evaluation pipeline
- `visualization.py`: Results comparison and plotting
- `run_evaluation.py`: Main execution script