#!/usr/bin/env python3
"""
Setup script for the Drug Discovery Pipeline package
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements from requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="drug-discovery-pipeline",
    version="1.0.0",
    author="Drug Discovery Team",
    author_email="contact@drugdiscovery.example.com",
    description="Pathway Analysis for Protein Target Selection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/drug-discovery-pipeline",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "viz": [
            "matplotlib>=3.7.0",
            "seaborn>=0.12.0",
            "plotly>=5.0.0",
            "networkx[default]>=3.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "drug-discovery=drug_discovery.main:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/example/drug-discovery-pipeline/issues",
        "Source": "https://github.com/example/drug-discovery-pipeline",
        "Documentation": "https://github.com/example/drug-discovery-pipeline/wiki",
    },
    keywords="drug discovery, protein targets, pathway analysis, bioinformatics, systems biology",
    package_data={
        "drug_discovery": ["*.py"],
    },
    include_package_data=True,
    zip_safe=False,
)