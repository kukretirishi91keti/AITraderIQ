import os
from groq import Groq

class GenAIHandler:
    """
    Handles natural language queries about stocks using Groq API.
    Example: "Should I buy AAPL today?"
    """
    
    def __init__(self):
        api_key = os.getenv('GROQ_API_KEY', '')
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in .env")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    
    def query(self, question: str, context: dict) -> str:
        """
        Answer a stock question using current price data.
        
        Args:
            question: User's natural language question (e.g., "Should I buy TSLA?")
            context: Dict with keys like 'symbol' and 'price'
        
        Returns:
            Natural language answer from Groq
        """
        
        symbol = context.get('symbol', 'UNKNOWN')
        price = context.get('price', 0)
        
        prompt = f"""You are a financial advisor analyzing {symbol} (currently ${price}).

User Question: {question}

Provide a concise 2-3 sentence answer with:
1. Direct yes/no/maybe based on current price
2. Top 1 reason
3. Risk level (Low/Medium/High)

Be conversational and confident but realistic."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Groq API Error: {str(e)}")


# Global instance for reuse
genai_handler = None

def get_genai_handler():
    global genai_handler
    if genai_handler is None:
        genai_handler = GenAIHandler()
    return genai_handler
