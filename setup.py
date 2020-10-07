import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='dt8852',
    version='1.0.0',
    author="Randy Simons",
    description='Cross-platform Python package and module for reading and controlling CEM DT-8852 and equivalent Sound Level Meter and Data Logger devices.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=['pyserial >= 3.4'],
    python_requires='>=3.8',
    url='https://codeberg.org/randysimons/dt8852',
    classifiers=['Operating System :: OS Independent',
                 'Programming Language :: Python :: 3.8',
                 'Topic :: System :: Hardware',
                 'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)']
)
