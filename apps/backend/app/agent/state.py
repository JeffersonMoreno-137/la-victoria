from typing import TypedDict, List, Optional, Dict, Any

class BotState(TypedDict):
    # Telegram User Context
    telegram_id: str
    user_name: Optional[str]
    phone: Optional[str]
    
    # Idioma y Conversación
    language: str # 'es' | 'en'
    user_message: str
    messages: List[Dict[str, str]] # [{'role': 'user'|'assistant', 'content': '...'}]
    
    # Intención y Guardrails
    intent: Optional[str] # 'faq', 'booking', 'manage_appointments', 'change_language', 'upl_triggered', 'greeting'
    upl_violation: bool
    
    # Booking Flow State
    selected_branch_code: Optional[str] # 'NY_QUEENS' | 'TX_DALLAS'
    selected_service_type: Optional[str] # 'ITIN' | 'IMMIGRATION' | 'NOTARY'
    selected_date: Optional[str] # 'YYYY-MM-DD'
    selected_slot: Optional[str] # ISO timestamp
    
    # Final Response
    response_text: str
    inline_keyboard_type: Optional[str] # 'main_menu', 'branches', 'services', 'dates', 'slots', 'manage_appointment', 'none'
    inline_keyboard_options: Optional[List[Dict[str, str]]]
