import operator
from typing import TypedDict, List, Optional, Dict, Any, Annotated

class BotState(TypedDict):
    # Telegram User Context
    telegram_id: str
    user_name: Optional[str]
    phone: Optional[str]
    
    # Idioma y Conversación (Persistida con acumulador por Checkpointer / Time Travel)
    language: str # 'es' | 'en'
    user_message: str
    messages: Annotated[List[Dict[str, str]], operator.add]
    
    # Intención y Fases de Conversación (LangGraph Flows)
    intent: Optional[str] # 'advisory', 'booking_qualification', 'manage_appointments', 'change_language', 'upl_triggered', 'greeting'
    conversation_phase: Optional[str] # 'advisory' | 'booking_qualification' | 'interactive_booking' | 'upl_triggered' | 'greeting'
    service_topic: Optional[str] # 'ITIN' | 'IMMIGRATION' | 'NOTARY' | 'GENERAL'
    docs_status: Optional[str] # 'unknown' | 'missing_docs' | 'ready_to_book'
    upl_violation: bool
    
    # Booking Flow State
    selected_branch_code: Optional[str] # 'NY_QUEENS' | 'TX_DALLAS'
    selected_service_type: Optional[str] # 'ITIN' | 'IMMIGRATION' | 'NOTARY'
    selected_date: Optional[str] # 'YYYY-MM-DD'
    selected_slot: Optional[str] # ISO timestamp
    
    # UI Control (Telegram Inline Keyboards)
    show_buttons: bool
    response_text: str
    inline_keyboard_type: Optional[str] # 'main_menu', 'branches', 'services', 'dates', 'slots', 'none'
    inline_keyboard_options: Optional[List[Dict[str, str]]]
