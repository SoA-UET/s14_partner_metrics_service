"""
Partner Metrics Service (S14)

This service aggregates and provides metrics for the Partner Portal.
It operates in two modes:
1. Real-time metrics collection via events from Core (background processing)
2. Responding to HTTP requests (on-demand queries)
"""

import threading
import time
import os
import json
from typing import Optional, Dict, Any
from .MessageQueueService import MessageQueueService


class PartnerMetricsService:
    """
    Main service class for Partner Metrics (S14).
    Handles real-time event processing and provides metrics data.
    """

    def __init__(self, partner_id: str):
        """
        Initialize the Partner Metrics Service.
        
        Args:
            partner_id: The ID of this partner
        """
        self.partner_id = partner_id
        
        # Message Queue Service for RabbitMQ communication
        self.mq_service = MessageQueueService()
        self.mq_lock = threading.Lock()
        
        # Queue names from environment variables
        self.s08_events_queue = os.getenv("S08_EVENTS_QUEUE", "s08_events_queue")
        self.s14_s08_requests_queue = os.getenv("S14_S08_REQUESTS_QUEUE", "s14_s08_requests_queue")
        self.s14_s08_responses_queue = os.getenv("S14_S08_RESPONSES_QUEUE", "s14_s08_responses_queue")
        
        # Metrics counters (Flow 1: Conversations)
        self.total_conversations = 0
        self.forwarding_conversations = 0
        self.texting_conversations = 0
        self.calling_conversations = 0
        
        # Metrics counters (Flow 2: Satisfaction)
        self.satisfaction_1 = 0
        self.satisfaction_2 = 0
        self.satisfaction_3 = 0
        self.satisfaction_4 = 0
        self.satisfaction_5 = 0
        self.total_ratings = 0
        self.average_rating = 0.0
        
        # Metrics counters (Flow 3: Offload Rate)
        self.ai_failed_conversations = 0
        self.offloaded_conversations = 0
        
        # Service health status
        self.is_healthy = False
        self.last_error = None
        
        # Response tracking for method calls
        self.pending_responses: Dict[str, Any] = {}
        self.response_lock = threading.Lock()
        self.response_counter = 0
        
        # Background threads
        self.event_consumer_thread: Optional[threading.Thread] = None
        self.response_consumer_thread: Optional[threading.Thread] = None
        
        print(f"[PartnerMetricsService] Initialized for partner_id: {partner_id}")

    def initialize(self):
        """
        Initialize the service by loading initial data from S08 and starting event consumers.
        This should be called once during service startup.
        """
        print("[PartnerMetricsService] Starting initialization...")
        
        # Declare queues
        with self.mq_lock:
            mq = self.mq_service.clone()
        mq.declare_queue(self.s08_events_queue)
        mq.declare_queue(self.s14_s08_requests_queue)
        mq.declare_queue(self.s14_s08_responses_queue)
        
        # Start response consumer thread first
        self._start_response_consumer()
        
        # Load initial data from S08
        success = self._load_initial_data()
        
        if not success:
            print("[PartnerMetricsService] WARNING: Failed to load initial data, starting with zero counters")
        
        # Start event consumer thread
        self._start_event_consumer()
        
        self.is_healthy = True
        print("[PartnerMetricsService] Initialization complete")

    def _load_initial_data(self) -> bool:
        """
        Load initial metrics data from S08 Core Metrics Service.
        Returns True if successful, False otherwise.
        """
        print("[PartnerMetricsService] Loading initial data from S08...")
        
        # Load conversation statistics
        conv_stats = self._call_s08_method("get_partner_conversation_statistics", {
            "partner_id": self.partner_id
        }, max_retries=3)
        
        if conv_stats and conv_stats.get("status") == "success":
            content = conv_stats.get("content", {})
            self.total_conversations = content.get("total_conversations", 0)
            self.forwarding_conversations = content.get("forwarding_conversations", 0)
            self.texting_conversations = content.get("texting_conversations", 0)
            self.calling_conversations = content.get("calling_conversations", 0)
            self.ai_failed_conversations = content.get("ai_failed_conversations", 0)
            self.offloaded_conversations = content.get("offloaded_conversations", 0)
            print(f"[PartnerMetricsService] Loaded conversation stats: total={self.total_conversations}")
        elif conv_stats and conv_stats.get("status") == "error":
            content = conv_stats.get("content", "")
            if content == "PARTNER_NOT_FOUND":
                print(f"[PartnerMetricsService] Partner not found, initializing with zero counters")
                # Keep all counters at 0
            elif content == "DB_CONNECTION_ERROR":
                print(f"[PartnerMetricsService] Database connection error from S08")
                return False
            else:
                print(f"[PartnerMetricsService] Error loading conversation stats: {content}")
                return False
        else:
            print("[PartnerMetricsService] Failed to load conversation statistics")
            return False
        
        # Load satisfaction distribution
        sat_dist = self._call_s08_method("get_partner_satisfaction_distribution", {
            "partner_id": self.partner_id
        }, max_retries=3)
        
        if sat_dist and sat_dist.get("status") == "success":
            content = sat_dist.get("content", {})
            self.satisfaction_1 = content.get("satisfaction_1", 0)
            self.satisfaction_2 = content.get("satisfaction_2", 0)
            self.satisfaction_3 = content.get("satisfaction_3", 0)
            self.satisfaction_4 = content.get("satisfaction_4", 0)
            self.satisfaction_5 = content.get("satisfaction_5", 0)
            self._recalculate_satisfaction_metrics()
            print(f"[PartnerMetricsService] Loaded satisfaction stats: total_ratings={self.total_ratings}")
        elif sat_dist and sat_dist.get("status") == "error":
            content = sat_dist.get("content", "")
            if content in ["PARTNER_NOT_FOUND", "NO_DATA_FOUND"]:
                print(f"[PartnerMetricsService] No satisfaction data found, initializing with zero counters")
                # Keep all counters at 0
            elif content == "DB_CONNECTION_ERROR":
                print(f"[PartnerMetricsService] Database connection error from S08")
                return False
            else:
                print(f"[PartnerMetricsService] Error loading satisfaction stats: {content}")
                return False
        else:
            print("[PartnerMetricsService] Failed to load satisfaction distribution")
            return False
        
        return True

    def _call_s08_method(self, method: str, params: dict, max_retries: int = 1) -> Optional[dict]:
        """
        Call an S08 method via RabbitMQ request/response pattern.
        
        Args:
            method: The method name to call
            params: The parameters for the method
            max_retries: Maximum number of retry attempts
            
        Returns:
            The response result dict, or None if failed
        """
        for attempt in range(max_retries):
            try:
                # Generate unique request ID
                with self.response_lock:
                    self.response_counter += 1
                    request_id = f"{self.partner_id}_{self.response_counter}_{int(time.time() * 1000)}"
                
                # Prepare request
                request = {
                    "method": method,
                    "params": params,
                    "id": request_id
                }
                
                # Register pending response with event
                response_event = threading.Event()
                with self.response_lock:
                    self.pending_responses[request_id] = {
                        "event": response_event,
                        "result": None
                    }
                
                # Send request
                with self.mq_lock:
                    mq = self.mq_service.clone()
                mq.publish_message(self.s14_s08_requests_queue, request)
                print(f"[PartnerMetricsService] Sent request to S08: {method} (id={request_id})")
                
                # Wait for response (timeout 10 seconds)
                if response_event.wait(timeout=10.0):
                    with self.response_lock:
                        if request_id in self.pending_responses:
                            result = self.pending_responses[request_id]["result"]
                            del self.pending_responses[request_id]
                            return result
                else:
                    print(f"[PartnerMetricsService] Timeout waiting for response from S08: {method}")
                    with self.response_lock:
                        if request_id in self.pending_responses:
                            del self.pending_responses[request_id]
                
                if attempt < max_retries - 1:
                    print(f"[PartnerMetricsService] Retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
            except Exception as e:
                print(f"[PartnerMetricsService] Error calling S08 method {method}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return None

    def _start_response_consumer(self):
        """Start the background thread for consuming S08 method responses."""
        def consume_responses():
            print("[PartnerMetricsService] Starting response consumer thread...")
            try:
                with self.mq_lock:
                    mq = self.mq_service.clone()
                mq.register_callback(self.s14_s08_responses_queue, self._handle_response)
                mq.start_consuming()
            except Exception as e:
                print(f"[PartnerMetricsService] Response consumer thread error: {e}")
                self.is_healthy = False
                self.last_error = str(e)
        
        self.response_consumer_thread = threading.Thread(target=consume_responses, daemon=True)
        self.response_consumer_thread.start()

    def _handle_response(self, message: dict):
        """
        Handle a response message from S08.
        
        Args:
            message: The response message
        """
        request_id = message.get("id")
        if not request_id:
            print("[PartnerMetricsService] Received response without id, ignoring")
            return
        
        result = message.get("result")
        
        with self.response_lock:
            if request_id in self.pending_responses:
                self.pending_responses[request_id]["result"] = result
                self.pending_responses[request_id]["event"].set()
            else:
                print(f"[PartnerMetricsService] Received response for unknown request id: {request_id}")

    def _start_event_consumer(self):
        """Start the background thread for consuming S08 events."""
        def consume_events():
            print("[PartnerMetricsService] Starting event consumer thread...")
            try:
                with self.mq_lock:
                    mq = self.mq_service.clone()
                mq.register_callback(self.s08_events_queue, self._handle_event)
                mq.start_consuming()
            except Exception as e:
                print(f"[PartnerMetricsService] Event consumer thread error: {e}")
                self.is_healthy = False
                self.last_error = str(e)
        
        self.event_consumer_thread = threading.Thread(target=consume_events, daemon=True)
        self.event_consumer_thread.start()

    def _handle_event(self, message: dict):
        """
        Handle an event message from S08.
        
        Args:
            message: The event message
        """
        try:
            event_type = message.get("event_type")
            params = message.get("params", {})
            event_id = message.get("id")
            
            # Validate partner_id matches
            partner_id = params.get("partner_id")
            if partner_id != self.partner_id:
                # Ignore events for other partners
                return
            
            if event_type == "conversation_start_by_partner":
                self._handle_conversation_start(params)
            elif event_type == "conversation_changed_status_by_partner":
                self._handle_conversation_status_change(params)
            elif event_type == "conversation_satisfaction_change_by_partner":
                self._handle_satisfaction_change(params)
            else:
                print(f"[PartnerMetricsService] Unknown event type: {event_type}")
        
        except Exception as e:
            print(f"[PartnerMetricsService] Error handling event: {e}")
            # Continue processing other events

    def _handle_conversation_start(self, params: dict):
        """
        Handle conversation_start_by_partner event.
        
        Args:
            params: Event parameters
        """
        conversation_id = params.get("conversation_id")
        started_at = params.get("started_at")
        
        print(f"[PartnerMetricsService] Conversation started: {conversation_id}")
        
        # Increment total conversations
        self.total_conversations += 1
        
        # New conversations start in FORWARDING status
        self.forwarding_conversations += 1
        
        # This also indicates AI failed (conversation forwarded to partner)
        self.ai_failed_conversations += 1

    def _handle_conversation_status_change(self, params: dict):
        """
        Handle conversation_changed_status_by_partner event.
        
        Args:
            params: Event parameters
        """
        conversation_id = params.get("conversation_id")
        old_status = params.get("old_status")
        new_status = params.get("new_status")
        updated_at = params.get("updated_at")
        
        print(f"[PartnerMetricsService] Conversation {conversation_id} status changed: {old_status} -> {new_status}")
        
        # Decrement counter for old status category
        if old_status == "FORWARDING":
            self.forwarding_conversations -= 1
        elif old_status == "HUMAN_AGENT_TEXTING":
            self.texting_conversations -= 1
        elif old_status == "HUMAN_AGENT_CALLING":
            self.calling_conversations -= 1
        
        # Increment counter for new status category
        if new_status == "FORWARDING":
            self.forwarding_conversations += 1
        elif new_status == "HUMAN_AGENT_TEXTING":
            self.texting_conversations += 1
        elif new_status == "HUMAN_AGENT_CALLING":
            self.calling_conversations += 1

    def _handle_satisfaction_change(self, params: dict):
        """
        Handle conversation_satisfaction_change_by_partner event.
        
        Args:
            params: Event parameters
        """
        conversation_id = params.get("conversation_id")
        old_satisfaction = params.get("old_satisfaction")
        new_satisfaction = params.get("new_satisfaction")
        updated_at = params.get("updated_at")
        
        print(f"[PartnerMetricsService] Satisfaction changed for {conversation_id}: {old_satisfaction} -> {new_satisfaction}")
        
        # Decrement old satisfaction counter if it exists
        if old_satisfaction:
            if old_satisfaction == 1:
                self.satisfaction_1 -= 1
            elif old_satisfaction == 2:
                self.satisfaction_2 -= 1
            elif old_satisfaction == 3:
                self.satisfaction_3 -= 1
            elif old_satisfaction == 4:
                self.satisfaction_4 -= 1
            elif old_satisfaction == 5:
                self.satisfaction_5 -= 1
        
        # Increment new satisfaction counter
        if new_satisfaction == 1:
            self.satisfaction_1 += 1
        elif new_satisfaction == 2:
            self.satisfaction_2 += 1
        elif new_satisfaction == 3:
            self.satisfaction_3 += 1
        elif new_satisfaction == 4:
            self.satisfaction_4 += 1
        elif new_satisfaction == 5:
            self.satisfaction_5 += 1
        
        # Recalculate metrics
        self._recalculate_satisfaction_metrics()

    def _recalculate_satisfaction_metrics(self):
        """Recalculate total_ratings and average_rating from satisfaction counters."""
        self.total_ratings = (
            self.satisfaction_1 +
            self.satisfaction_2 +
            self.satisfaction_3 +
            self.satisfaction_4 +
            self.satisfaction_5
        )
        
        if self.total_ratings > 0:
            self.average_rating = (
                1 * self.satisfaction_1 +
                2 * self.satisfaction_2 +
                3 * self.satisfaction_3 +
                4 * self.satisfaction_4 +
                5 * self.satisfaction_5
            ) / self.total_ratings
        else:
            self.average_rating = 0.0

    def get_conversation_metrics(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> dict:
        """
        Get conversation metrics (Flow 1).
        
        Args:
            from_date: Optional start date filter (ISO 8601 format)
            to_date: Optional end date filter (ISO 8601 format)
            
        Returns:
            Dictionary with conversation metrics
        """
        # If date filters are specified, query S08 instead of using cached counters
        if from_date or to_date:
            result = self._call_s08_method("get_partner_conversation_statistics", {
                "partner_id": self.partner_id,
                "from_date": from_date,
                "to_date": to_date
            })
            
            if result and result.get("status") == "success":
                content = result.get("content", {})
                return {
                    "status": "success",
                    "total_conversations": content.get("total_conversations", 0),
                    "texting_conversations": content.get("texting_conversations", 0),
                    "calling_conversations": content.get("calling_conversations", 0),
                    "from_date": from_date,
                    "to_date": to_date
                }
            else:
                # Handle error
                return {
                    "status": "error",
                    "error": result.get("content", "Unknown error") if result else "S08 unavailable"
                }
        
        # Return cached counters (real-time)
        return {
            "status": "success",
            "total_conversations": self.total_conversations,
            "texting_conversations": self.texting_conversations,
            "calling_conversations": self.calling_conversations,
            "from_date": from_date,
            "to_date": to_date
        }

    def get_satisfaction_metrics(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> dict:
        """
        Get satisfaction metrics (Flow 2).
        
        Args:
            from_date: Optional start date filter (ISO 8601 format)
            to_date: Optional end date filter (ISO 8601 format)
            
        Returns:
            Dictionary with satisfaction metrics
        """
        # If date filters are specified, query S08
        if from_date or to_date:
            result = self._call_s08_method("get_partner_satisfaction_distribution", {
                "partner_id": self.partner_id,
                "from_date": from_date,
                "to_date": to_date
            })
            
            if result and result.get("status") == "success":
                content = result.get("content", {})
                sat_1 = content.get("satisfaction_1", 0)
                sat_2 = content.get("satisfaction_2", 0)
                sat_3 = content.get("satisfaction_3", 0)
                sat_4 = content.get("satisfaction_4", 0)
                sat_5 = content.get("satisfaction_5", 0)
                total = sat_1 + sat_2 + sat_3 + sat_4 + sat_5
                avg = ((1 * sat_1 + 2 * sat_2 + 3 * sat_3 + 4 * sat_4 + 5 * sat_5) / total) if total > 0 else 0.0
                
                return {
                    "status": "success",
                    "total_conversations": total,
                    "satisfaction_distribution": {
                        "satisfaction_1": sat_1,
                        "satisfaction_2": sat_2,
                        "satisfaction_3": sat_3,
                        "satisfaction_4": sat_4,
                        "satisfaction_5": sat_5
                    },
                    "average_rating": round(avg, 2),
                    "from_date": from_date,
                    "to_date": to_date
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("content", "Unknown error") if result else "S08 unavailable"
                }
        
        # Return cached counters
        return {
            "status": "success",
            "total_conversations": self.total_ratings,
            "satisfaction_distribution": {
                "satisfaction_1": self.satisfaction_1,
                "satisfaction_2": self.satisfaction_2,
                "satisfaction_3": self.satisfaction_3,
                "satisfaction_4": self.satisfaction_4,
                "satisfaction_5": self.satisfaction_5
            },
            "average_rating": round(self.average_rating, 2),
            "from_date": from_date,
            "to_date": to_date
        }

    def get_offload_metrics(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> dict:
        """
        Get offload rate metrics (Flow 3).
        
        Args:
            from_date: Optional start date filter (ISO 8601 format)
            to_date: Optional end date filter (ISO 8601 format)
            
        Returns:
            Dictionary with offload rate metrics
        """
        # If date filters are specified, query S08
        if from_date or to_date:
            result = self._call_s08_method("get_partner_conversation_statistics", {
                "partner_id": self.partner_id,
                "from_date": from_date,
                "to_date": to_date
            })
            
            if result and result.get("status") == "success":
                content = result.get("content", {})
                total = content.get("total_conversations", 0)
                ai_failed = content.get("ai_failed_conversations", 0)
                offloaded = content.get("offloaded_conversations", 0)
                offload_rate = (offloaded / total * 100) if total > 0 else 0.0
                
                return {
                    "status": "success",
                    "total_conversations": total,
                    "ai_failed_conversation": ai_failed,
                    "offloaded_conversations": offloaded,
                    "offload_rate_percentage": round(offload_rate, 2),
                    "from_date": from_date,
                    "to_date": to_date
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("content", "Unknown error") if result else "S08 unavailable"
                }
        
        # Return cached counters
        offload_rate = (self.offloaded_conversations / self.total_conversations * 100) if self.total_conversations > 0 else 0.0
        
        return {
            "status": "success",
            "total_conversations": self.total_conversations,
            "ai_failed_conversation": self.ai_failed_conversations,
            "offloaded_conversations": self.offloaded_conversations,
            "offload_rate_percentage": round(offload_rate, 2),
            "from_date": from_date,
            "to_date": to_date
        }

    def get_health_status(self) -> dict:
        """
        Get the health status of the service.
        
        Returns:
            Dictionary with health information
        """
        return {
            "healthy": self.is_healthy,
            "last_error": self.last_error,
            "partner_id": self.partner_id,
            "metrics": {
                "total_conversations": self.total_conversations,
                "total_ratings": self.total_ratings,
                "offload_rate": round((self.offloaded_conversations / self.total_conversations * 100) if self.total_conversations > 0 else 0.0, 2)
            }
        }
