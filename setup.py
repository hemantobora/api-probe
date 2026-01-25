"""Setup configuration for api-probe."""

from setuptools import setup, find_packages

setup(
    name="api-probe",
    version="0.1.0",
    description="Containerized API validation tool for CI/CD pipelines",
    author="Hemanto Bora",
    python_requires=">=3.9",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "PyYAML>=6.0.1",
        "requests>=2.31.0",
        "jsonpath-ng>=1.6.1",
        "lxml>=5.1.0",
    ],
    entry_points={
        "console_scripts": [
            "api-probe=api_probe.cli:main",
        ],
    },
)
