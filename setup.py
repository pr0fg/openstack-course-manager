import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="openstack-course-manager-pr0fg",
    version="0.1",
    author="Garrett Hayes",
    author_email="",
    description="A cloud-adjacent academic course manager for OpenStack",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pr0fg/openstack-course-manager",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
