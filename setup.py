from setuptools import setup, find_packages

setup(
    name="jarvis-assistant",
    version="1.0.0",
    description="Local-First Personal AI Assistant for Windows (JARVIS)",
    author="Antigravity",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "PySide6>=6.6.0",
        "faster-whisper>=1.0.0",
        "edge-tts>=6.1.9",
        "sounddevice>=0.4.6",
        "numpy>=1.24.0",
        "psutil>=5.9.0",
        "pyautogui>=0.9.54",
        "apscheduler>=3.10.4",
        "pytest>=7.4.0",
        "requests>=2.31.0",
        "pydantic>=2.5.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "jarvis=run:main",
        ],
    },
)
