"""
S14 Partner Metrics Service - Main Application Entry Point

This is the main entry point for the Partner Metrics Service.
It initializes the Flask HTTP server and the background RabbitMQ event consumers.
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import service and controller
from .services.PartnerMetricsService import PartnerMetricsService
from .controllers.v1.partner_metrics import set_partner_metrics_service, register_routes


def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Flask app instance
    """
    app = Flask(__name__)
    
    # Configure CORS
    cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
    if cors_origins == "*":
        CORS(app)
    else:
        # Split by comma and strip whitespace
        origins_list = [origin.strip() for origin in cors_origins.split(",")]
        CORS(app, origins=origins_list)
    
    # Get partner ID from environment
    partner_id = os.getenv("PARTNER_ID")
    if not partner_id:
        raise ValueError("PARTNER_ID environment variable is required")
    
    print(f"[S14] Starting Partner Metrics Service for partner: {partner_id}")
    
    # Initialize Partner Metrics Service
    metrics_service = PartnerMetricsService(partner_id)
    
    # Set the service instance for the controller
    set_partner_metrics_service(metrics_service)
    
    # Register API routes
    register_routes(app)
    
    # Add root endpoint
    @app.route('/')
    def index():
        return jsonify({
            "service": "S14 Partner Metrics Service",
            "partner_id": partner_id,
            "version": "1.0.0",
            "endpoints": {
                "conversations": "/api/v1/partner/metrics/conversations",
                "satisfaction_rate": "/api/v1/partner/metrics/satisfaction-rate",
                "offload_rate": "/api/v1/partner/metrics/offload-rate",
                "health": "/api/v1/partner/metrics/health"
            }
        })
    
    # Initialize the service (load data and start event consumers)
    metrics_service.initialize()
    
    print("[S14] Partner Metrics Service initialized successfully")
    
    return app


def main():
    """
    Main function to run the service.
    """
    # Create Flask app
    app = create_app()
    
    # Get configuration from environment
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5014"))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    print(f"[S14] Starting HTTP server on {host}:{port}")
    
    # Run the Flask app
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    main()
