"""
Amazon SNS wrapper for publishing critical quality and spurious medicine alerts.
"""
from typing import Dict, Any, Optional
import json
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_client
from src.config import settings
from src.utils.logger import logger

class SNSWrapper(BaseAWSWrapper):
    """Encapsulates Amazon SNS alert notifications (§5.2 step 8)."""
    def __init__(self):
        super().__init__("SNS")
        self.client = get_boto_client("sns")

    @catch_aws_errors("Publish")
    def publish_alert(
        self,
        subject: str,
        message: str,
        topic_arn: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publishes an alert notification to an SNS topic."""
        target_topic = topic_arn or settings.SNS_ALERTS_TOPIC_ARN
        kwargs: Dict[str, Any] = {
            "TopicArn": target_topic,
            "Subject": subject[:100],  # SNS subject max length 100
            "Message": message
        }

        if attributes:
            msg_attrs = {}
            for k, v in attributes.items():
                msg_attrs[k] = {
                    "DataType": "String",
                    "StringValue": str(v)
                }
            kwargs["MessageAttributes"] = msg_attrs

        response = self.client.publish(**kwargs)
        msg_id = response.get("MessageId")
        logger.info(f"Published SNS alert: {msg_id} -> {subject}")
        return msg_id

    def publish_spurious_medicine_alert(
        self,
        batch_no: str,
        drug_name: str,
        manufacturer: str,
        reason: Optional[str] = None
    ) -> str:
        """Convenience method for high-severity spurious medicine alerts."""
        subject = f"CRITICAL: Spurious Medicine Ingested - {drug_name} (Batch: {batch_no})"
        payload = {
            "severity": "CRITICAL",
            "type": "SPURIOUS_ALERT",
            "batch_no": batch_no,
            "drug_name": drug_name,
            "manufacturer": manufacturer,
            "reason": reason or "Flagged as spurious by CDSCO",
        }
        return self.publish_alert(
            subject=subject,
            message=json.dumps(payload, indent=2),
            attributes={"alert_type": "SPURIOUS"}
        )
