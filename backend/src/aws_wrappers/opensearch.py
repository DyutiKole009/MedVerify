"""
OpenSearch wrapper for fuzzy drug and manufacturer name matching with AWS SigV4 authentication.
"""
from typing import Dict, Any, List, Optional
import json
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_session
from src.config import settings
from src.utils.logger import logger

class OpenSearchWrapper(BaseAWSWrapper):
    """
    Encapsulates Amazon OpenSearch Serverless fuzzy query operations (§4.6).
    Signs requests with SigV4 using ambient AWS credentials.
    """
    def __init__(self, endpoint: Optional[str] = None):
        super().__init__("OpenSearch")
        self.endpoint = (endpoint or settings.OPENSEARCH_ENDPOINT).rstrip("/")
        self.session = get_boto_session()
        self.credentials = self.session.get_credentials()
        self.region = settings.AWS_REGION
        self.service = "aoss"  # 'aoss' for OpenSearch Serverless, 'es' for managed OpenSearch

    def _send_signed_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Signs an HTTP request with AWS SigV4 and sends it to the OpenSearch endpoint."""
        url = f"{self.endpoint}/{path.lstrip('/')}"
        data = json.dumps(body) if body else None
        headers = {"Content-Type": "application/json"}

        # Sign request with SigV4
        if self.credentials:
            frozen_creds = self.credentials.get_frozen_credentials()
            if frozen_creds:
                request = AWSRequest(method=method, url=url, data=data, headers=headers)
                SigV4Auth(frozen_creds, self.service, self.region).add_auth(request)
                headers = dict(request.headers)

        response = requests.request(
            method=method,
            url=url,
            data=data,
            headers=headers,
            timeout=10
        )

        if not response.ok:
            logger.error(f"OpenSearch query failed [{response.status_code}]: {response.text}")
            response.raise_for_status()

        return response.json()

    @catch_aws_errors("FuzzySearch")
    def search_fuzzy(
        self,
        index_name: str,
        field_name: str,
        query_text: str,
        size: int = 5,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a fuzzy query with fuzziness=AUTO over a normalized text field (§4.6).
        """
        query = {
            "size": size,
            "query": {
                "fuzzy": {
                    field_name: {
                        "value": query_text,
                        "fuzziness": "AUTO",
                        "prefix_length": 1
                    }
                }
            }
        }

        response = self._send_signed_request(
            method="POST",
            path=f"{index_name}/_search",
            body=query
        )

        hits = response.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            score = hit.get("_score", 0.0)
            if min_score is not None and score < min_score:
                continue
            results.append({
                "id": hit.get("_id"),
                "score": score,
                "source": hit.get("_source", {})
            })

        return results

    @catch_aws_errors("IndexDocument")
    def index_document(
        self,
        index_name: str,
        doc_id: str,
        document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Indexes or updates a document in OpenSearch."""
        return self._send_signed_request(
            method="PUT",
            path=f"{index_name}/_doc/{doc_id}",
            body=document
        )
