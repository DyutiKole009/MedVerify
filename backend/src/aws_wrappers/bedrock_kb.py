"""
Bedrock Knowledge Base wrapper for vector retrieval, citations, and data source ingestion.
"""
from typing import Dict, Any, Optional, List
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_client
from src.utils.logger import logger

class BedrockKBWrapper(BaseAWSWrapper):
    """Encapsulates Bedrock Knowledge Base RAG retrieval and data source ingestion sync."""
    def __init__(self):
        super().__init__("BedrockKnowledgeBase")
        self.runtime_client = get_boto_client("bedrock-agent-runtime")
        self.agent_client = get_boto_client("bedrock-agent")

    @catch_aws_errors("Retrieve")
    def retrieve(
        self,
        kb_id: str,
        query_text: str,
        number_of_results: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries the Bedrock Knowledge Base vector store with optional metadata filtering (§6.3).
        Returns a list of structured citation results.
        """
        vector_config: Dict[str, Any] = {
            "numberOfResults": number_of_results
        }
        if metadata_filter:
            vector_config["filter"] = metadata_filter

        retrieval_configuration = {
            "vectorSearchConfiguration": vector_config
        }

        response = self.runtime_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query_text},
            retrievalConfiguration=retrieval_configuration
        )

        results = []
        for item in response.get("retrievalResults", []):
            content = item.get("content", {}).get("text", "")
            location_info = item.get("location", {})
            s3_uri = location_info.get("s3Location", {}).get("uri", "")
            score = item.get("score", 0.0)
            metadata = item.get("metadata", {})

            results.append({
                "content": content,
                "s3_uri": s3_uri,
                "score": score,
                "metadata": metadata
            })

        return results

    @catch_aws_errors("RetrieveAndGenerate")
    def retrieve_and_generate(
        self,
        kb_id: str,
        model_arn: str,
        query_text: str
    ) -> Dict[str, Any]:
        """
        Retrieves context from Knowledge Base and synthesizes a direct answer with citations.
        """
        response = self.runtime_client.retrieve_and_generate(
            input={"text": query_text},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": kb_id,
                    "modelArn": model_arn
                }
            }
        )
        output = response.get("output", {}).get("text", "")
        citations = response.get("citations", [])
        return {
            "output_text": output,
            "citations": citations
        }

    @catch_aws_errors("StartIngestionJob")
    def start_ingestion_job(
        self,
        kb_id: str,
        data_source_id: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Starts an asynchronous data ingestion job to sync documents into the vector index (§5.2 step 6).
        """
        kwargs: Dict[str, Any] = {
            "knowledgeBaseId": kb_id,
            "dataSourceId": data_source_id
        }
        if description:
            kwargs["description"] = description

        response = self.agent_client.start_ingestion_job(**kwargs)
        ingestion_job = response.get("ingestionJob", {})
        logger.info(
            f"Started KB ingestion job: {ingestion_job.get('ingestionJobId')} for data source: {data_source_id}"
        )
        return ingestion_job
