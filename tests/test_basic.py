import unittest2 as unittest

import flask

from flaskext import celery


class test_Celery(unittest.TestCase):

    def setUp(self):
        self.app = flask.Flask(__name__)
        self.c = celery.Celery(self.app)

    def test_loader_is_configured(self):
        from celery.loaders import current_loader, load_settings
        loader = current_loader()
        self.assertIsInstance(loader, celery.FlaskLoader)
        settings = load_settings()
        self.assertTrue(loader.configured)

    def test_task_honors_app_settings(self):
        app = flask.Flask(__name__)
        app.config["CELERY_IGNORE_RESULT"] = True
        app.config["CELERY_TASK_SERIALIZER"] = "msgpack"
        c = celery.Celery(app)

        @c.task(foo=1)
        def add_task_args(x, y):
            return x + y

        @c.task
        def add_task_noargs(x, y):
            return x + y

        for task in add_task_args, add_task_noargs:
            self.assertTrue(any("BaseFlaskTask" in repr(cls)
                                for cls in task.__class__.mro()))
            self.assertEqual(task(2, 2), 4)
            self.assertEqual(task.serializer, "msgpack")
            self.assertTrue(task.ignore_result)
