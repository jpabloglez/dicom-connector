# setup.py
from setuptools import setup, find_packages

setup(
    name="dicom_app",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pydicom==2.3.0",
        "pynetdicom==2.0.2",
        "psycopg2-binary==2.9.3",
        "requests==2.26.0",
    ],
)