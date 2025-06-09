#!/bin/bash
# Build script for Symbol-Heavy Drawing Generator

set -e

echo "🐳 Building Docker image..."
docker build -t drawing-generator:latest .

echo "📏 Checking image size..."
docker images drawing-generator:latest

echo "✅ Testing Docker image..."
docker run --rm drawing-generator:latest --help

echo "🎯 Running demo generation..."
mkdir -p ./out
docker run --rm -v $(pwd)/out:/app/out drawing-generator:latest -n 3 --sheet-size A4 --noise-level 1

echo "📊 Generated files:"
ls -la ./out/

echo "✅ Build completed successfully!"