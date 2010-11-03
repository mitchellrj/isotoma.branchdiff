from setuptools import setup

version = '0.0.1'

setup(
    name='isotoma.branchdiff',
    version=version,
    description="A tool for showing diffs of a particular Python code block across several subversion branches at once.",
    url='http://github.com/mitchellrj/isotoma.branchdiff',
    keywords="svn subversion diff python function class branch branch git",
    author="Richard Mitchell",
    author_email="richard.mitchell@isotoma.com",
    license="Apache Software License",
    packages=['isotoma.branchdiff'],
    include_package_data=True,
    zip_safe=False,

    entry_points={
        'console_scripts': [
            'branchdiff = isotoma.branchdiff:main',
            ]
    }
)

