from setuptools import setup

setup(name="adaptavist",
      description="python package providing functionality for Jira Test Management (tm4j)",
      long_description=open("README.md").read(),
      long_description_content_type="text/markdown",
      use_scm_version=True,
      url="https://github.com/devolo/adaptavist",
      author="Stephan Steinberg, Guido Schmitz, Markus Bong",
      author_email="guido.schmitz@devolo.de, markus.bong@devolo.de",
      license="MIT",
      packages=["adaptavist"],
      package_data={"adaptavist": ["py.typed"]},
      platforms="any",
      python_requires=">=3.6",
      install_requires=["importlib-metadata;python_version<'3.8'", "pbr", "requests_toolbelt", "requests"],
      extras_require={
          "test": ["pytest", "requests-mock"],
          "docs": ["m2r2", "pydata_sphinx_theme", "sphinx"],
      },
      setup_requires=["setuptools_scm"],
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
      ])
