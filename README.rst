==============================
 Flask <-> Celery Integration
==============================
:Version: 2.2.5

Requires `Celery`_ 2.2.0 or later.

.. _Celery: http://celeryproject.org

Installation Celery
===================

You can install Celery either via the Python Package Index (PyPI) or from source.

To install using pip:

    $ pip install Celery

To install using easy_install:

    $ easy_install Celery

To install from source:
::
    $ tar xvfz celery-0.0.0.tar.gz
    $ cd celery-0.0.0
    $ python setup.py build
    # python setup.py install (root user)

Example
=======

You probably want to see some code by now, so you can see example/ for example usage (task
adding two numbers):
::
    python manage.py celeryd
    python myapp.py

Check http://127.0.0.1:5000/
