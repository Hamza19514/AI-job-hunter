import os

from flask import Flask

from config import Config
from app.models import db


def create_app(config_object=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["GENERATED_FILES_DIR"], exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    # Avoid starting the scheduler twice under the Flask debug reloader,
    # which forks a child process and re-runs create_app() in both.
    running_under_reloader = app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true"
    if not app.config["DISABLE_SCHEDULER"] and not running_under_reloader:
        from app.scheduler import start_scheduler
        start_scheduler(app)

    return app
