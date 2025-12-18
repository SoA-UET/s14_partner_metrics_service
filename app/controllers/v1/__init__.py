# NOTE: you can modify this file as appropriate.

from flask import Blueprint

v1 = Blueprint("v1", __name__, url_prefix="/api/v1")

# Import partner metrics blueprint
from .partner_metrics import partner_metrics_bp

# Register the partner metrics blueprint with v1
v1.register_blueprint(partner_metrics_bp, url_prefix='')
