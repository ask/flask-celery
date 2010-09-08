import sys

from flask import Flask, request
from flaskext.celery import Celery

app = Flask(__name__)
celery = Celery(app)


@celery.task
def add(x, y):
    return x + y


@app.route("/")
def hello_world(x=16, y=16):
    x = int(request.args.get("x", x))
    y = int(request.args.get("y", y))
    res = add.apply_async((x, y))
    context = {"id": res.task_id, "x": x, "y": y}
    return """Hello world: \
                add(%(x)s, %(y)s) = \
                <a href="/result/%(id)s">%(id)s</a>""" % context


@app.route("/result/<task_id>")
def show_result(task_id):
    retval = add.AsyncResult(task_id).get(timeout=1.0)
    return repr(retval)


if __name__ == "__main__":
    if "-w" in sys.argv:
        celery.Worker().run()
    else:
        app.run(debug=True)
