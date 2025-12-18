"""
H30 API Group - Partner Metrics HTTP Endpoints

This controller exposes HTTP REST API endpoints for the Partner Portal
to retrieve metrics data specific to the authenticated partner.
"""

from flask import request, jsonify, Blueprint
from ...utils.auth import require_auth
from datetime import datetime


# Create blueprint for partner metrics API
partner_metrics_bp = Blueprint('partner_metrics', __name__, url_prefix='/api/v1/partner/metrics')

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


@partner_metrics_bp.route('/conversations', methods=['GET'])
@require_auth()
def get_conversations():
    """
    H30.1: GET /api/v1/partner/metrics/conversations
    
    Retrieve conversation statistics for this partner, including total conversations,
    texting conversations, and calling conversations.
    
    Query Parameters:
        - from_date (optional): Start date for conversation statistics (ISO 8601 format)
        - to_date (optional): End date for conversation statistics (ISO 8601 format)
    
    Returns:
        200: Conversation statistics
        400: Invalid parameters
        401: Unauthorized
        500: Internal server error
    """
    try:
        # Validate date parameters
        from_date, to_date, error = validate_date_params()
        if error:
            return error
        
        # Get metrics from service
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
        
        # Return success response
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


@partner_metrics_bp.route('/satisfaction-rate', methods=['GET'])
@require_auth()
def get_satisfaction_rate():
    """
    H30.2: GET /api/v1/partner/metrics/satisfaction-rate
    
    Retrieve the distribution of consultation sessions by customer satisfaction rating (1-5 stars).
    
    Query Parameters:
        - from_date (optional): Start date for consultation statistics (ISO 8601 format)
        - to_date (optional): End date for consultation statistics (ISO 8601 format)
    
    Returns:
        200: Satisfaction statistics
        400: Invalid parameters
        401: Unauthorized
        500: Internal server error
    """
    try:
        # Validate date parameters
        from_date, to_date, error = validate_date_params()
        if error:
            return error
        
        # Get metrics from service
        service = get_partner_metrics_service()
        result = service.get_satisfaction_metrics(from_date, to_date)
        
        if result.get("status") == "error":
            error_msg = result.get("error", "Unknown error")
            
            # NO_DATA_FOUND is not an error, return empty distribution
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
        
        # Return success response
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


@partner_metrics_bp.route('/offload-rate', methods=['GET'])
@require_auth()
def get_offload_rate():
    """
    H30.3: GET /api/v1/partner/metrics/offload-rate
    
    Retrieve the consultation offload rate for this specific Partner
    (the rate at which consultations are forwarded from AI to Partner staff).
    
    Query Parameters:
        - from_date (optional): Start date for consultation statistics (ISO 8601 format)
        - to_date (optional): End date for consultation statistics (ISO 8601 format)
    
    Returns:
        200: Offload rate statistics
        400: Invalid parameters
        401: Unauthorized
        500: Internal server error
    """
    try:
        # Validate date parameters
        from_date, to_date, error = validate_date_params()
        if error:
            return error
        
        # Get metrics from service
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
        
        # Return success response
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


@partner_metrics_bp.route('/health', methods=['GET'])
def get_health():
    """
    Health check endpoint for the Partner Metrics Service.
    
    Returns:
        200: Service is healthy
        503: Service is unhealthy
    """
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
