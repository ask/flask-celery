"""
Flask-Celery
------------

Celery integration for Flask

"""
from setuptools import setup

setup(
    name='Flask-Celery',
    version='2.1',
    url='http://github.com/ask/flask-celery/',
    license='BSD',
    author='Ask Solem',
    author_email='ask@celeryproject.org',
    description='Celery integration for Flask',
    long_description=__doc__,
    packages=['flaskext'],
    namespace_packages=['flaskext'],
    zip_safe=False,
    platforms='any',
    test_suite="nose.collector",
    install_requires=[
        'Flask',
        'celery',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
