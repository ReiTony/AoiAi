import logging
import re 
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from utils.sessions import ChatSession, get_chat_session
from utils.llm_client import generate_response
from utils.instructor_templates import fitness_instructor_prompt

logger = logging.getLogger("instructor_chat")
router = APIRouter()

def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  
    text = re.sub(r'\*(.*?)\*', r'\1', text)      
    text = re.sub(r'_(.*?)_', r'\1', text)        
    return text

class ChatMessage(BaseModel):
    role: str
    content: str

class InstructorChatRequest(BaseModel):
    query: str
    history: Optional[List[ChatMessage]] = None

@router.post("/query_router")
async def instructor_chat(
    chat_req: InstructorChatRequest,
    request: Request,
    chat_session: ChatSession = Depends(get_chat_session)
):
    user_message = chat_req.query.strip()
    if not user_message:
        logger.warning("No message provided.")
        return JSONResponse(content={"error": "Message is required."}, status_code=422)

    try:
        history = await chat_session.get_history()
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        history = []

    prompt = fitness_instructor_prompt(user_message)
    logger.info(f"Prompt to LLM:\n{prompt}")

    try:
        ai_response = await generate_response(prompt)
        logger.info(f"Raw LLM Response:\n{ai_response}")
        ai_response = strip_markdown(ai_response)
        logger.info(f"Cleaned Response:\n{ai_response}")
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        ai_response = "Sorry, I couldn't process your request right now."

    try:
        await chat_session.add_message("user", user_message)
        await chat_session.add_message("assistant", ai_response)
    except Exception as e:
        logger.error(f"Failed to save chat messages: {e}")

    return JSONResponse(content={
        "answer": ai_response,
        "history": history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response}
        ]
    }, status_code=200)
