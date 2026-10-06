# user_search/grpc_client.py
import grpc
import logging
from typing import List, Optional

# Import your generated gRPC modules (adjust names as per your proto)
try:
    from . import user_search_pb2
    from . import user_search_pb2_grpc
except ImportError:
    # Fallback if modules are in a different path
    import user_search_pb2
    import user_search_pb2_grpc

logger = logging.getLogger(__name__)

class UserSearchGrpcClient:
    def __init__(self, host: str = "localhost", port: int = 50051):
        self.host = host
        self.port = port
        self.channel = None
        self.stub = None

    def connect(self):
        """Establish a connection to the gRPC server."""
        if self.channel is None:
            target = f"{self.host}:{self.port}"
            self.channel = grpc.insecure_channel(target)
            self.stub = user_search_pb2_grpc.UserSearchServiceStub(self.channel)
            logger.info(f"gRPC client connected to {target}")

    def close(self):
        """Close the gRPC channel."""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.stub = None
            logger.info("gRPC client connection closed.")

    def search_users(self, query: str, limit: int = 10, offset: int = 0) -> List[dict]:
        """
        Call the gRPC SearchUsers method.
        Returns a list of dictionaries representing users.
        """
        if not self.stub:
            self.connect()

        try:
            request = user_search_pb2.UserSearchRequest(
                query=query,
                limit=limit,
                offset=offset
            )
            response = self.stub.SearchUsers(request)
            
            # Convert protobuf response to list of dicts
            results = []
            for user in response.users:
                results.append({
                    "user_id": user.user_id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "department": user.department
                })
            return results, response.total_count
        except grpc.RpcError as e:
            logger.error(f"gRPC call failed: {e.code()} - {e.details()}")
            raise

# Singleton instance for the app
_grpc_client: Optional[UserSearchGrpcClient] = None

def get_grpc_client() -> UserSearchGrpcClient:
    global _grpc_client
    if _grpc_client is None:
        _grpc_client = UserSearchGrpcClient()
        _grpc_client.connect()
    return _grpc_client