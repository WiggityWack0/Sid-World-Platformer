from setuptools import find_packages, setup

setup(
    name="sids-world",
    version="1.0.0",
    description="A procedurally generated Super Mario World-style platformer",
    author="Sid",
    packages=find_packages(include=["src", "src.*"]),
    install_requires=[
        "pygame-ce>=2.5",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "sids-world=src.main:main",
        ],
    },
)