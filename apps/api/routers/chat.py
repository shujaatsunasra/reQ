"""
Simple chat endpoint for Explorer mode.
Direct LLM conversation without complex query processing.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time
import uuid

from core.logging import get_logger
from core.llm_service import get_llm_service

logger = get_logger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message", min_length=1, max_length=5000)
    conversation_history: Optional[List[ChatMessage]] = Field(default=None, description="Previous messages in conversation")
    api_key: Optional[str] = Field(default=None, description="Groq API key")
    model: Optional[str] = Field(default=None, description="Groq model to use")
    system_prompt: Optional[str] = Field(default=None, description="Custom system prompt")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    success: bool
    request_id: str
    message: str
    response: str
    model: str
    execution_time_ms: float
    error: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Simple chat endpoint for conversational interactions.
    
    This endpoint provides direct LLM access for Explorer mode,
    allowing natural conversations about oceanographic data without
    the complex query processing pipeline.
    
    Args:
        request: Chat request with message and optional history
    
    Returns:
        ChatResponse with LLM-generated response
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"Processing chat [{request_id}]: {request.message[:100]}...")
    
    try:
        # Get LLM service
        llm = get_llm_service(api_key=request.api_key, model=request.model)
        
        # Build conversation context with enhanced system prompt
        system_prompt = request.system_prompt or """You are FloatChat, a friendly AI assistant specialized in oceanographic data exploration.

## Key Behavior Rules
1. **Match the user's tone**: If they greet you casually, respond casually.
2. **ALWAYS follow formatting requests**: If user asks for tables, lists, comparisons - USE THAT FORMAT.
3. **Keep casual responses brief**: Just be friendly for greetings.
4. **NEVER mention technical tools**: No Matplotlib, Plotly, Python, libraries.

## FORMATTING INSTRUCTIONS (FOLLOW EXACTLY)
- **table** → Create a markdown table
- **compare** → Create a side-by-side comparison table  
- **list** → Use bullet points
- **summary** → Be brief and structured

## Example Comparison Table:
| Property | Arabian Sea | Indian Ocean |
|----------|-------------|--------------|
| Avg Temp | 26.5°C | 14.9°C |
| Temp Range | 20-29°C | 5-28°C |
| Profiles | 100 | 100 |

## When NOT to Discuss Data
- Casual greetings ("hi", "how are you", "what's up")
- Off-topic conversation

## Your Expertise (use when relevant)
- ARGO float data from global oceans
- Ocean temperatures, salinity, currents
- Data visualization and exploration

## FORBIDDEN Topics
- Library names (Matplotlib, Plotly, D3, etc.)
- Programming languages (Python, JavaScript, etc.)
- Technical tools or implementation details

## Response Style
- Be conversational and natural
- Show enthusiasm for ocean science
- If asked for specific format, USE IT"""

        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if request.conversation_history:
            for msg in request.conversation_history[-10:]:  # Keep last 10 messages for context
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Call Groq API directly
        response = await llm.chat_completion(messages)
        
        execution_time = (time.time() - start_time) * 1000
        logger.info(f"Chat [{request_id}] completed in {execution_time:.2f}ms")
        
        return ChatResponse(
            success=True,
            request_id=request_id,
            message=request.message,
            response=response["content"],
            model=response["model"],
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Chat [{request_id}] failed: {str(e)}")
        execution_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            success=False,
            request_id=request_id,
            message=request.message,
            response="I apologize, but I encountered an error processing your message. Please check your API key and try again.",
            model=request.model or "unknown",
            execution_time_ms=execution_time,
            error=str(e)
        )
