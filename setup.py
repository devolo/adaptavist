from setuptools import setup

setup(
    name="adaptavist",
    description="python package providing functionality for Adaptavist Test Management with Jira server interaction",
    long_description=open("README.md").read(),
    version="1.0.0",
    url="https://gitlab.devolo.intern/python-packages/adaptavist",
    author="Stephan Steinberg",
    author_email="stephan.steinberg@devolo.de",
    license="proprietary",
    packages=["adaptavist"],
    platforms="any",
    install_requires=["requests", "requests_toolbelt"]
)
