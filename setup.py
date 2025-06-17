#!/usr/bin/env python3
"""
Setup script for mkv2mp4ui
"""
from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "A PyQt6 GUI application for batch converting MKV files to MP4 format using FFmpeg."

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return ["PyQt6", "ffmpeg-python"]

setup(
    name="mkv2mp4ui",
    version="1.0.0",
    author="Scott Peterman",
    author_email="scottpeterman@gmail.com",  # Update with your email
    description="A PyQt6 GUI application for batch converting MKV files to MP4",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/scottpeterman/mkvtomp4ui",
    project_urls={
        "Bug Reports": "https://github.com/scottpeterman/mkvtomp4ui/issues",
        "Source": "https://github.com/scottpeterman/mkvtomp4ui",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "mkv2mp4ui=mkv2mp4ui.main:main",
        ],
        "gui_scripts": [
            "mkv2mp4ui-gui=mkv2mp4ui.main:main",
        ],
    },
    package_data={
        "mkv2mp4ui": [
            "*.py",
        ],
    },
    include_package_data=True,
    keywords=[
        "mkv", "mp4", "video", "conversion", "ffmpeg", "gui", "pyqt6",
        "batch", "converter", "multimedia", "video-processing"
    ],
    zip_safe=False,
)