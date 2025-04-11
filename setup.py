from setuptools import setup, find_packages

setup(
    name="keep2notion",
    version="0.0.6",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pendulum",
        "retrying",
        "notion-client",
        "github-heatmap",
        "python-dotenv",
        "emoji",
        "bson",
    ],
    entry_points={
        "console_scripts": [
            "keep2notion = keep2notion.keep:main",
            "update_heatmap = keep2notion.update_heatmap:main",
        ],
    },
    author="malinkang",
    author_email="linkang.ma@gmail.com",
    description="Keep同步到Notion",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/malinkang/habit2notion",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
