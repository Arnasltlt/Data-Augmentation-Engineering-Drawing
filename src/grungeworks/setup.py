"""Setup script for GrungeWorks package."""

from setuptools import setup, find_packages

setup(
    name="grungeworks",
    version="0.1.0",
    description="Scanner-style noise and rasterization agent for engineering drawings",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "Pillow>=9.0.0",
        "opencv-python>=4.8.0",
        "PyMuPDF>=1.23.0",
        "pdf2image>=3.1.0",
        "scikit-image>=0.21.0",
    ],
    entry_points={
        "console_scripts": [
            "grungeworks=grungeworks.cli:main",
        ],
    },
    python_requires=">=3.8",
)