import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

# Setup tools
setuptools.setup(
     name='fgit',
     version='0.0.1b7',
     author="Truong-Phat Nguyen",
     author_email="me@patrickphat.com",
     description="FastGit: No longer wait for another git commit",
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/patrick/fgit",
     packages=setuptools.find_packages(exclude=['docs', 'tests', 'experiments']),
     entry_points ={ 
            'console_scripts': [ 
                'fgit = fgit_cli.main:main'
            ]
     },
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: MIT License",
         "Operating System :: OS Independent",
     ],
     python_requires='>3.6',
     install_requires =[
         "GitPython",
         ],
     extras_require={
         'dev': [
             'pytest',
             'coverage',
             ],
     }
 )