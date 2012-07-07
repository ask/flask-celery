==============================
 Flask <-> Celery Integration
==============================
:Version: 2.4.3

**FROM CELERY 3.0 THIS LIBRARY IS NO LONGER NECESSARY, INSTEAD YOU SHOULD
USE THE STANDARD CELERY API**

.. _Celery: http://celeryproject.org

Using Flask with Celery
=======================

From Celery 3.0 the Flask-Celery integration package is no longer
recommended and you should use the standard Celery API instead.

Please read the Celery getting started tutorial::

    http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html


You can easily add Celery to your flask application like this::

``myapp.py``::

    from celery import Celery

    celery = Celery('myapp', broker='amqp://guest@localhost//')

    @celery.task
    def add(x, y):
        return x + y


To start the worker you can then launch the ``celery worker`` command
by pointing to your ``celery`` app instance::

    $ celery -A myapp worker -l info

(if the app argument (``-A|--app)`` is a module/package instead of an
attribute
it will automatically expand into ``myapp.celery``)


See the commands help screen for more information::

    $ celery help


If you want use the flask configuration as a source for the celery
configuration you can do that like this::

    celery = Celery('myapp')
    celery.config_from_object(flask_app.config)


If you need access to the request inside your task
then you can use the test context::

    from flask import Flask
    from celery import Celery

    app = Flask('myapp')
    celery = Celery('myapp')

    celery.config_from_object(app.config)

    @celery.task
    def hello():
        with app.test_request_context() as request:
            print('Hello {0!r}.format(request))
