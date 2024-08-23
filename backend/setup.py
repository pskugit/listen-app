from setuptools import setup, find_packages

setup(
    name="listen",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "neo4j",
        "pydantic"
        # Add other dependencies here as needed
    ],
)
