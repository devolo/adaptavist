from setuptools import setup

setup(
    name="adaptavist",
    description="python package providing functionality for Jira Test Management (tm4j)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    version="v1.0.0",
    url="https://github.com/devolo/adaptavist",
    author="Stephan Steinberg",
    author_email="stephan.steinberg@devolo.de",
    license="MIT",
    packages=["adaptavist"],
    platforms="any",
    python_requires=">=3.6",
    install_requires=["requests", "requests_toolbelt"],
    keywords="python adaptavist kanoah tm4j jira test testmanagement report",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Utilities",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ]
)
