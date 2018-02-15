from setuptools import setup, find_packages

def find_version():
    import os
    with open(os.path.join("opencrimedata", "__init__.py")) as file:
        for line in file:
            if line.startswith("__version__"):
                start = line.index('"')
                end = line[start+1:].index('"')
                return line[start+1:][:end]
            
long_description = ""

setup(
    name = 'opencrimedata',
    packages = find_packages(include=["opencrimedata*"]),
    version = find_version(),
    install_requires = [], # TODO
    python_requires = '>=3.5',
    description = 'Load, and impute spatial positions, of open source US crime data',
    long_description = long_description,
    author = 'Matthew Daws',
    author_email = 'matthew.daws@gogglemail.com',
    url = 'https://bitbucket.org/MatthewDaws/opencrimedata',
    license = '', # TODO
    keywords = [],
    classifiers = [
        "Development Status :: 3 - Alpha",
        # License
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering :: GIS"
        # Crime??
    ]
)