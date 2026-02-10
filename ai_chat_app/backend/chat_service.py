import os
import uvicorn
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
from fastmcp import Client
from backend.mcp_server import mcp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


app = FastAPI()

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CURRENT_FILE = os.path.abspath(__file__)
BACKEND_DIR = os.path.dirname(CURRENT_FILE)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

# verify frontend dir exists, if not try relative to CWD
if not os.path.exists(FRONTEND_DIR):
    # Fallback: assume running from ai_chat_app root
    FRONTEND_DIR = os.path.abspath("frontend")

print(f"Serving frontend from: {FRONTEND_DIR}")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def read_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_path):
        return {"error": f"index.html not found at {index_path}"}
    return FileResponse(index_path)

# Initialize Gemini Client
MODEL_ID = "gemini-3-flash-preview"

api_key = os.environ.get("GEMINI_API_KEY")
client = None
if not api_key:
    logger.warning("GEMINI_API_KEY environment variable not set. Application may fail if not authenticated via other means.")
else:
    try:
        client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
    except Exception as e:
        logger.error(f"Failed to initialize Gemini Client: {e}")

class ChatRequest(BaseModel):
    message: str
    history: list = []

def convert_mcp_tool_to_gemini(mcp_tool):
    """Converts an MCP tool definition to a Gemini Tool object."""
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=mcp_tool.name,
                description=mcp_tool.description,
                parameters=mcp_tool.inputSchema
            )
        ]
    )

async def run_chat_turn(message: str, history: list):
    if not client:
        raise ValueError("Gemini Client not initialized. Please set GEMINI_API_KEY.")

    # List of events to return to the frontend
    # Events can be:
    # - {"type": "text", "content": "..."}
    # - {"type": "tool_call", "tool_name": "...", "args": {...}}
    # - {"type": "tool_result", "tool_name": "...", "result": "..."}
    events = []

    async with Client(mcp) as session:
        mcp_tools = await session.list_tools()
        gemini_tools = [convert_mcp_tool_to_gemini(t) for t in mcp_tools]
        
        # Log available tools
        logger.info("Available Tools:")
        for t in mcp_tools:
            logger.info(f"- Name: {t.name}")
            logger.info(f"  Description: {t.description}")
            
        contents = [types.Content(role="user", parts=[types.Part(text=message)])]
        logger.info(f"User Message: {message}")
        
        # Define system instruction
        system_instruction = """You are an expert Data Analyst Assistant for the Cortex Data Foundation.
Your goal is to help users understand their data by querying BigQuery.

Guidelines:
1. Always start by exploring available tables using `list_tables`.
2. Once you have the list of tables, identify the ones that seem relevant to the user's request.
3. Use `get_table_schema` to retrieve the schema (column names and types) ONLY for those specific relevant tables.
4. Construct a standard SQL query to retrieve the necessary data based on the discovered schema.
5. If a query fails, analyze the error and try to fix it.
6. Format your answers clearly, using Markdown tables for data where appropriate.
7. Be concise but helpful."""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                system_instruction=system_instruction
            )
        )
        
        while response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            
            # Log model response part
            logger.info(f"Model Response Part: {part}")

            if part.function_call:
                fc = part.function_call
                tool_name = fc.name
                tool_args = fc.args
                
                logger.info(f"Executing tool: {tool_name}")
                logger.info(f"Tool Arguments: {tool_args}")
                
                # Add tool call event
                events.append({
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "args": tool_args
                })
                
                result = await session.call_tool(tool_name, arguments=tool_args)
                logger.info(f"Tool Output: {result}")
                
                # Add tool result event
                events.append({
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": str(result)
                })
                
                func_response_part = types.Part(
                    function_response=types.FunctionResponse(
                        name=tool_name,
                        response={"result": str(result)} 
                    )
                )
                
                contents.append(response.candidates[0].content)
                contents.append(types.Content(role="user", parts=[func_response_part]))
                
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        tools=gemini_tools,
                        system_instruction=system_instruction
                    )
                )
            else:
                if part.text:
                    logger.info(f"Final Text Response: {part.text}")
                    # Add text response event
                    events.append({
                        "type": "text",
                        "content": part.text
                    })
                break
                
        return events

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        events = await run_chat_turn(request.message, request.history)
        return {"events": events}
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
