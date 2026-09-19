"""
DynamoDB wrapper providing robust CRUD, GSI query, conditional write, and batch capabilities.
"""
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
import json
from boto3.dynamodb.conditions import Key, Attr
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_resource, get_boto_client
from src.utils.logger import logger

def _convert_floats_to_decimals(obj: Any) -> Any:
    """Recursively converts Python floats to Decimals for DynamoDB serialization."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats_to_decimals(v) for v in obj]
    return obj

def _convert_decimals_to_primitives(obj: Any) -> Any:
    """Recursively converts Decimals from DynamoDB into standard int/float primitives."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimals_to_primitives(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals_to_primitives(v) for v in obj]
    return obj

class DynamoDBWrapper(BaseAWSWrapper):
    """Encapsulates all DynamoDB operations with schema independence and robust error translation."""
    def __init__(self):
        super().__init__("DynamoDB")
        self.resource = get_boto_resource("dynamodb")
        self.client = get_boto_client("dynamodb")

    def _get_table(self, table_name: str):
        return self.resource.Table(table_name)

    @catch_aws_errors("GetItem")
    def get_item(self, table_name: str, pk: str, sk: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves a single item by primary key."""
        table = self._get_table(table_name)
        key = {"PK": pk}
        if sk is not None:
            key["SK"] = sk
        response = table.get_item(Key=key)
        item = response.get("Item")
        return _convert_decimals_to_primitives(item) if item else None

    @catch_aws_errors("PutItem")
    def put_item(
        self,
        table_name: str,
        item: Dict[str, Any],
        condition_expression: Optional[str] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Writes an item into DynamoDB with optional conditional check."""
        table = self._get_table(table_name)
        sanitized_item = _convert_floats_to_decimals(item)
        kwargs: Dict[str, Any] = {"Item": sanitized_item}

        if condition_expression:
            kwargs["ConditionExpression"] = condition_expression
        if expression_attribute_names:
            kwargs["ExpressionAttributeNames"] = expression_attribute_names
        if expression_attribute_values:
            kwargs["ExpressionAttributeValues"] = _convert_floats_to_decimals(expression_attribute_values)

        table.put_item(**kwargs)
        return True

    @catch_aws_errors("UpdateItem")
    def update_item(
        self,
        table_name: str,
        pk: str,
        sk: Optional[str],
        update_expression: str,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        condition_expression: Optional[str] = None,
        return_values: str = "ALL_NEW"
    ) -> Dict[str, Any]:
        """Updates attributes of an item."""
        table = self._get_table(table_name)
        key = {"PK": pk}
        if sk is not None:
            key["SK"] = sk

        kwargs: Dict[str, Any] = {
            "Key": key,
            "UpdateExpression": update_expression,
            "ReturnValues": return_values
        }
        if expression_attribute_names:
            kwargs["ExpressionAttributeNames"] = expression_attribute_names
        if expression_attribute_values:
            kwargs["ExpressionAttributeValues"] = _convert_floats_to_decimals(expression_attribute_values)
        if condition_expression:
            kwargs["ConditionExpression"] = condition_expression

        response = table.update_item(**kwargs)
        attributes = response.get("Attributes", {})
        return _convert_decimals_to_primitives(attributes)

    @catch_aws_errors("DeleteItem")
    def delete_item(self, table_name: str, pk: str, sk: Optional[str] = None) -> bool:
        """Deletes an item by primary key."""
        table = self._get_table(table_name)
        key = {"PK": pk}
        if sk is not None:
            key["SK"] = sk
        table.delete_item(Key=key)
        return True

    @catch_aws_errors("Query")
    def query(
        self,
        table_name: str,
        key_condition_expression: Any,
        index_name: Optional[str] = None,
        filter_expression: Optional[Any] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True,
        exclusive_start_key: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Executes a DynamoDB Query on the main table or a GSI."""
        table = self._get_table(table_name)
        kwargs: Dict[str, Any] = {
            "KeyConditionExpression": key_condition_expression,
            "ScanIndexForward": scan_index_forward
        }
        if index_name:
            kwargs["IndexName"] = index_name
        if filter_expression:
            kwargs["FilterExpression"] = filter_expression
        if limit:
            kwargs["Limit"] = limit
        if exclusive_start_key:
            kwargs["ExclusiveStartKey"] = exclusive_start_key

        response = table.query(**kwargs)
        items = [_convert_decimals_to_primitives(item) for item in response.get("Items", [])]
        last_key = response.get("LastEvaluatedKey")
        return items, last_key

    @catch_aws_errors("QueryGSI")
    def query_gsi(
        self,
        table_name: str,
        index_name: str,
        partition_key: str,
        partition_value: str,
        sort_key: Optional[str] = None,
        sort_value: Optional[str] = None,
        sort_begins_with: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True,
        exclusive_start_key: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Convenience method for querying Global Secondary Indexes (GSIs)."""
        key_condition = Key(partition_key).eq(partition_value)
        if sort_key and sort_value:
            key_condition = key_condition & Key(sort_key).eq(sort_value)
        elif sort_key and sort_begins_with:
            key_condition = key_condition & Key(sort_key).begins_with(sort_begins_with)

        return self.query(
            table_name=table_name,
            key_condition_expression=key_condition,
            index_name=index_name,
            limit=limit,
            scan_index_forward=scan_index_forward,
            exclusive_start_key=exclusive_start_key
        )

    @catch_aws_errors("BatchWrite")
    def batch_write_items(self, table_name: str, items: List[Dict[str, Any]]) -> int:
        """Batch writes multiple items using Table.batch_writer with automatic backoff."""
        table = self._get_table(table_name)
        written = 0
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=_convert_floats_to_decimals(item))
                written += 1
        return written
