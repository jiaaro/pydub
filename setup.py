__doc__ = """
Manipulate audio with an simple and easy high level interface.

See the README file for details, usage info, and a list of gotchas.
"""

from setuptools import setup

setup(
    name='pydub',
    version='0.7.1',
    author='James Robert',
    author_email='jiaaro@gmail.com',
    description='Manipulate audio with an simple and easy high level interface',
    license='MIT',
    keywords='audio sound high-level',
    url='http://pydub.com',
    packages=['pydub'],
    long_description=__doc__,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
        "Topic :: Multimedia :: Sound/Audio :: Editors",
        "Topic :: Multimedia :: Sound/Audio :: Mixers",
        "Topic :: Software Development :: Libraries",
        'Topic :: Utilities',
    ]
)
