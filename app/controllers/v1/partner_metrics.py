"""
H30 API Group - Partner Metrics HTTP Endpoints

This controller exposes HTTP REST API endpoints for the Partner Portal
to retrieve metrics data specific to the authenticated partner.
"""

from flask import request, jsonify
from ...utils.auth import require_auth
from datetime import datetime


# This will be set by the main application
_partner_metrics_service = None


def set_partner_metrics_service(service):
    """
    Set the PartnerMetricsService instance for this controller.
    This should be called during application initialization.
    """
    global _partner_metrics_service
    _partner_metrics_service = service


def get_partner_metrics_service():
    """Get the PartnerMetricsService instance."""
    if _partner_metrics_service is None:
        raise RuntimeError("PartnerMetricsService not initialized")
    return _partner_metrics_service


def validate_date_params():
    """
    Validate and extract date parameters from query string.
    Returns tuple: (from_date, to_date, error_response)
    """
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    # Validate date format if provided
    if from_date:
        try:
            datetime.fromisoformat(from_date.replace('Z', '+00:00'))
        except ValueError:
            return None, None, (jsonify({
                "status": "error",
                "error_code": "INVALID_PARAMETERS",
                "message": "Invalid query parameters",
                "details": "from_date must be in ISO 8601 format"
            }), 400)
    
    if to_date:
        try:
            datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        except ValueError:
            return None, None, (jsonify({
                "status": "error",
                "error_code": "INVALID_PARAMETERS",
                "message": "Invalid query parameters",
                "details": "to_date must be in ISO 8601 format"
            }), 400)
    
    # Validate that from_date is before to_date
    if from_date and to_date:
        from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
        to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        if from_dt >= to_dt:
            return None, None, (jsonify({
                "status": "error",
                "error_code": "INVALID_PARAMETERS",
                "message": "Invalid query parameters",
                "details": "from_date must be before to_date"
            }), 400)
    
    return from_date, to_date, None


def register_routes(app):
    """Register all partner metrics routes with the Flask app."""
    
    @app.route('/api/v1/partner/metrics/conversations', methods=['GET'])
    @require_auth()
    def get_conversations():
        """H30.1: GET /api/v1/partner/metrics/conversations"""
        try:
            from_date, to_date, error = validate_date_params()
            if error:
                return error
            
            service = get_partner_metrics_service()
            result = service.get_conversation_metrics(from_date, to_date)
            
            if result.get("status") == "error":
                error_msg = result.get("error", "Unknown error")
                
                if error_msg == "PARTNER_NOT_FOUND":
                    return jsonify({
                        "status": "error",
                        "error_code": "PARTNER_NOT_FOUND",
                        "message": "Partner not found"
                    }), 404
                elif error_msg == "DB_CONNECTION_ERROR" or "unavailable" in error_msg.lower():
                    return jsonify({
                        "status": "error",
                        "error_code": "SERVICE_UNAVAILABLE",
                        "message": "Core Metrics Service unavailable"
                    }), 500
                else:
                    return jsonify({
                        "status": "error",
                        "error_code": "INTERNAL_ERROR",
                        "message": "An internal server error occurred while retrieving metrics"
                    }), 500
            
            return jsonify({
                "status": "success",
                "total_conversations": result["total_conversations"],
                "texting_conversations": result["texting_conversations"],
                "calling_conversations": result["calling_conversations"],
                "from_date": result.get("from_date"),
                "to_date": result.get("to_date")
            }), 200
        
        except Exception as e:
            print(f"[H30.1] Error: {e}")
            return jsonify({
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": "An internal server error occurred while retrieving metrics"
            }), 500
    
    
    @app.route('/api/v1/partner/metrics/satisfaction-rate', methods=['GET'])
    @require_auth()
    def get_satisfaction_rate():
        """H30.2: GET /api/v1/partner/metrics/satisfaction-rate"""
        try:
            from_date, to_date, error = validate_date_params()
            if error:
                return error
            
            service = get_partner_metrics_service()
            result = service.get_satisfaction_metrics(from_date, to_date)
            
            if result.get("status") == "error":
                error_msg = result.get("error", "Unknown error")
                
                if error_msg == "NO_DATA_FOUND":
                    return jsonify({
                        "status": "success",
                        "total_conversations": 0,
                        "satisfaction_distribution": {
                            "satisfaction_1": 0,
                            "satisfaction_2": 0,
                            "satisfaction_3": 0,
                            "satisfaction_4": 0,
                            "satisfaction_5": 0
                        },
                        "average_rating": 0.0,
                        "from_date": from_date,
                        "to_date": to_date
                    }), 200
                elif error_msg == "PARTNER_NOT_FOUND":
                    return jsonify({
                        "status": "error",
                        "error_code": "PARTNER_NOT_FOUND",
                        "message": "Partner not found"
                    }), 404
                elif error_msg == "DB_CONNECTION_ERROR" or "unavailable" in error_msg.lower():
                    return jsonify({
                        "status": "error",
                        "error_code": "SERVICE_UNAVAILABLE",
                        "message": "Core Metrics Service unavailable"
                    }), 500
                else:
                    return jsonify({
                        "status": "error",
                        "error_code": "INTERNAL_ERROR",
                        "message": "An internal server error occurred while retrieving metrics"
                    }), 500
            
            return jsonify({
                "status": "success",
                "total_conversations": result["total_conversations"],
                "satisfaction_distribution": result["satisfaction_distribution"],
                "average_rating": result["average_rating"],
                "from_date": result.get("from_date"),
                "to_date": result.get("to_date")
            }), 200
        
        except Exception as e:
            print(f"[H30.2] Error: {e}")
            return jsonify({
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": "An internal server error occurred while retrieving metrics"
            }), 500
    
    
    @app.route('/api/v1/partner/metrics/offload-rate', methods=['GET'])
    @require_auth()
    def get_offload_rate():
        """H30.3: GET /api/v1/partner/metrics/offload-rate"""
        try:
            from_date, to_date, error = validate_date_params()
            if error:
                return error
            
            service = get_partner_metrics_service()
            result = service.get_offload_metrics(from_date, to_date)
            
            if result.get("status") == "error":
                error_msg = result.get("error", "Unknown error")
                
                if error_msg == "PARTNER_NOT_FOUND":
                    return jsonify({
                        "status": "error",
                        "error_code": "PARTNER_NOT_FOUND",
                        "message": "Partner not found"
                    }), 404
                elif error_msg == "DB_CONNECTION_ERROR" or "unavailable" in error_msg.lower():
                    return jsonify({
                        "status": "error",
                        "error_code": "SERVICE_UNAVAILABLE",
                        "message": "Core Metrics Service unavailable"
                    }), 500
                else:
                    return jsonify({
                        "status": "error",
                        "error_code": "INTERNAL_ERROR",
                        "message": "An internal server error occurred while retrieving metrics"
                    }), 500
            
            return jsonify({
                "status": "success",
                "total_conversations": result["total_conversations"],
                "ai_failed_conversation": result["ai_failed_conversation"],
                "offloaded_conversations": result["offloaded_conversations"],
                "offload_rate_percentage": result["offload_rate_percentage"],
                "from_date": result.get("from_date"),
                "to_date": result.get("to_date")
            }), 200
        
        except Exception as e:
            print(f"[H30.3] Error: {e}")
            return jsonify({
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": "An internal server error occurred while retrieving metrics"
            }), 500
    
    
    @app.route('/api/v1/partner/metrics/health', methods=['GET'])
    def get_health():
        """Health check endpoint for the Partner Metrics Service."""
        try:
            service = get_partner_metrics_service()
            health = service.get_health_status()
            
            if health["healthy"]:
                return jsonify({
                    "status": "healthy",
                    "partner_id": health["partner_id"],
                    "metrics": health["metrics"]
                }), 200
            else:
                return jsonify({
                    "status": "unhealthy",
                    "partner_id": health["partner_id"],
                    "last_error": health["last_error"]
                }), 503
        
        except Exception as e:
            print(f"[Health] Error: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 503
