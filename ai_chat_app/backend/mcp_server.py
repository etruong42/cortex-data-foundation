from fastmcp import FastMCP
from google.cloud import bigquery
import pandas as pd
import json

# Initialize FastMCP
mcp = FastMCP("Cortex Data Foundation MCP")

# Initialize BigQuery Client
PROJECT_ID = "kittycorn-dev-five"
client = bigquery.Client(project=PROJECT_ID)

@mcp.tool()
def query_bigquery(sql: str) -> str:
    """
    Executes a SQL query against BigQuery and returns the results as a JSON string.
    Use this tool to answer questions about the data in the Cortex Data Foundation.

    To navigate the tables:
    1. Start by using `list_tables` to see all available tables in the project.
    2. Use `get_table_schema` to understand the columns and data types of specific tables that seem relevant.
    3. Construct a standard SQL query to retrieve the necessary data based on the schema information.
    4. The results are returned as a JSON string.
    
    Args:
        sql: The SQL query to execute.
    """
    try:
        # Run the query
        query_job = client.query(sql)
        results = query_job.result()
        
        # Convert to DataFrame
        df = results.to_dataframe()
        
        # Return as JSON (orient='records' is usually good for lists of objects)
        # Limit to a reasonable amount of data to avoid overwhelming the model context
        if len(df) > 100:
            return f"Query returned {len(df)} rows. Here are the first 100:\n" + df.head(100).to_json(orient='records')
        
        return df.to_json(orient='records')
    except Exception as e:
        return f"Error executing query: {str(e)}"

@mcp.tool()
def list_tables() -> str:
    """
    Retrieves a list of ALL available table IDs in the project.
    Returns a list of fully qualified table IDs (project.dataset.table).
    Use this tool to discover what tables are available before asking for their specific schemas.
    """
    try:
        table_ids = []
        # List all datasets
        datasets = list(client.list_datasets())
        
        for dataset in datasets:
            dataset_id = dataset.dataset_id
            # List all tables in dataset
            tables = list(client.list_tables(dataset_id))
            
            for table in tables:
                table_ids.append(f"{dataset_id}.{table.table_id}")
                
        return json.dumps(table_ids, indent=2)
    except Exception as e:
        return f"Error listing tables: {str(e)}"

@mcp.tool()
def get_table_schema(table_id: str) -> str:
    """
    Retrieves the schema for a specified BigQuery table.
    Use this tool to understand the column names, data types, and descriptions of a table
    before retrieving data with `query_bigquery`.

    Args:
        table_id: The fully qualified table ID (e.g., 'project.dataset.table' or 'dataset.table').
    """
    try:
        table = client.get_table(table_id)
        schema = []
        for field in table.schema:
            schema.append({
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,
                "description": field.description
            })
        return json.dumps(schema, indent=2)
    except Exception as e:
        return f"Error retrieving schema for {table_id}: {str(e)}"

if __name__ == "__main__":
    mcp.run()
