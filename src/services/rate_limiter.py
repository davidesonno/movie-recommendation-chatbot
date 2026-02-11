import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import HTTPException, Request
import threading


class RateLimiter:
    """
    Token bucket rate limiter for API endpoints.
    Tracks requests per user (from JWT) and per IP address.
    """

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute per user
            requests_per_hour: Max requests per hour per user
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Store request timestamps: {user_id: [timestamp1, timestamp2, ...]}
        self.user_requests: Dict[int, List[float]] = defaultdict(list)
        # Store IP request timestamps: {ip: [timestamp1, timestamp2, ...]}
        self.ip_requests: Dict[str, List[float]] = defaultdict(list)
        
        self._lock = threading.Lock()

    def _cleanup_old_requests(self, timestamps: List[float], window_seconds: int) -> List[float]:
        """Remove timestamps older than the window."""
        current_time = time.time()
        return [ts for ts in timestamps if current_time - ts < window_seconds]

    def is_allowed(self, user_id: int, client_ip: str) -> Tuple[bool, str]:
        """
        Check if a request is allowed for the user.
        
        Args:
            user_id: The authenticated user ID
            client_ip: The client's IP address
            
        Returns:
            Tuple of (is_allowed: bool, message: str)
        """
        current_time = time.time()
        
        with self._lock:
            # Clean up old requests
            self.user_requests[user_id] = self._cleanup_old_requests(
                self.user_requests[user_id], 3600  # 1 hour window
            )
            self.ip_requests[client_ip] = self._cleanup_old_requests(
                self.ip_requests[client_ip], 3600  # 1 hour window
            )
            
            # Check minute limit
            minute_requests = [ts for ts in self.user_requests[user_id] if current_time - ts < 60]
            if len(minute_requests) >= self.requests_per_minute:
                return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
            
            # Check hour limit
            if len(self.user_requests[user_id]) >= self.requests_per_hour:
                return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
            
            # Check IP-based rate limit (anti-abuse)
            ip_hour_requests = len(self.ip_requests[client_ip])
            if ip_hour_requests >= self.requests_per_hour * 2:  # More lenient for IP
                return False, f"Rate limit exceeded from your IP address"
            
            # Request is allowed, record it
            self.user_requests[user_id].append(current_time)
            self.ip_requests[client_ip].append(current_time)
            
            return True, "OK"

    def get_stats(self, user_id: int) -> Dict:
        """Get rate limit stats for a user."""
        current_time = time.time()
        
        with self._lock:
            minute_requests = [ts for ts in self.user_requests[user_id] if current_time - ts < 60]
            hour_requests = self.user_requests[user_id]
            
            return {
                "requests_this_minute": len(minute_requests),
                "requests_this_hour": len(hour_requests),
                "minute_limit": self.requests_per_minute,
                "hour_limit": self.requests_per_hour,
            }


# Global rate limiter instance
_rate_limiter: RateLimiter = None


def init_rate_limiter(requests_per_minute: int = 60, requests_per_hour: int = 1000) -> RateLimiter:
    """Initialize the global rate limiter."""
    global _rate_limiter
    _rate_limiter = RateLimiter(requests_per_minute, requests_per_hour)
    return _rate_limiter


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def check_user_rate_limit(request: Request, user_id: int) -> None:
    """
    Check rate limit for the user. Raises HTTPException if limit exceeded.
    
    Args:
        request: FastAPI request object
        user_id: The authenticated user ID
        
    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter = get_rate_limiter()
    is_allowed, message = rate_limiter.is_allowed(user_id, client_ip)
    
    if not is_allowed:
        raise HTTPException(status_code=429, detail=message)
