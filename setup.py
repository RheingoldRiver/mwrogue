import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mwrogue",
    version="0.0.12",
    author="RheingoldRiver",
    author_email="river.esports@gmail.com",
    description="Client for accessing Fandom/Gamepedia Esports Wikis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RheingoldRiver/mwrogue",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    install_requires=['mwparserfromhell', 'pytz', 'mwclient>=0.10.1', 'python-dateutil', 'Unidecode', 'mwcleric>=0.6.2']
)
