from setuptools import setup, find_packages

setup(
    name="openaisummarizer",
    version="1.0",
    url="https://github.com/VonAlphaBisZulu/OpenAI_Summarizer.git",
    description="Summarize voice recordings",
    long_description=
    "Use OpenAI API to summarize voice recordings (OpenAI API key required)",
    long_description_content_type="text/plain",
    author="Philipp Schneider",
    author_email="zgddtgt@gmail.com",
    license="GNU v3.0",
    python_requires=">=3.7",
    package_data={"straindesign": ["efmtool.jar"]},
    packages=find_packages(),
    install_requires=[],
    project_urls={
        "Bug Reports": "https://github.com/VonAlphaBisZulu/OpenAI_Summarizer/issues",
        "Source": "https://github.com/VonAlphaBisZulu/OpenAI_Summarizer/",
        "Documentation": "https://github.com/VonAlphaBisZulu/OpenAI_Summarizer/README.md"
    },
    classifiers=[
        "Intended Audience :: Productivity", "Development Status :: 3 - Alpha", "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8", "Programming Language :: Python :: 3.9", "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11", "Natural Language :: English", "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Productivity"
    ],
    keywords=["OpenAI","Productivity"],
    zip_safe=False,
)
