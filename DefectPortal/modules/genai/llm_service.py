"""
LLM Service using Ollama (free, runs locally)
Provides text generation capabilities for summaries and suggestions.
"""

import logging
import requests
import json
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class LLMService:
    """
    LLM service using Ollama for local inference.
    Falls back to rule-based generation if Ollama is not available.
    """
    
    def __init__(
        self,
        model_name: str = "mistral",
        ollama_url: str = "http://localhost:11434",
        timeout: int = 60
    ):
        """
        Initialize the LLM service.
        
        Args:
            model_name: Ollama model to use (mistral, llama2, etc.)
            ollama_url: URL of the Ollama server.
            timeout: Request timeout in seconds.
        """
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.timeout = timeout
        self.ollama_available = False
        self._check_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is running and available."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '').split(':')[0] for m in models]
                
                if self.model_name in model_names or any(self.model_name in n for n in model_names):
                    self.ollama_available = True
                    logger.info(f"Ollama available with model: {self.model_name}")
                else:
                    logger.warning(f"Ollama running but model '{self.model_name}' not found. Available: {model_names}")
                    logger.info("Using rule-based generation as fallback")
            else:
                logger.warning("Ollama not responding properly")
        except requests.exceptions.RequestException:
            logger.warning("Ollama not available. Using rule-based generation as fallback.")
            logger.info("To enable AI generation, install Ollama and run: ollama pull mistral")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        timeout: Optional[int] = None
    ) -> str:
        """
        Generate text using the LLM.
        
        Args:
            prompt: The prompt to send to the LLM.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature (0-1).
            timeout: Request timeout in seconds. If None, uses instance default.
            
        Returns:
            Generated text.
        """
        if self.ollama_available:
            return self._generate_ollama(prompt, max_tokens, temperature, timeout)
        else:
            return self._generate_fallback(prompt)
    
    def _generate_ollama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        timeout: Optional[int] = None
    ) -> str:
        """Generate using Ollama API."""
        req_timeout = timeout if timeout is not None else self.timeout
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                },
                timeout=req_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return self._generate_fallback(prompt)
                
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return self._generate_fallback(prompt)
    
    def _generate_fallback(self, prompt: str) -> str:
        """
        Fallback rule-based generation when Ollama is not available.
        Provides basic responses based on pattern matching.
        """
        prompt_lower = prompt.lower()
        
        # Resolution suggestions
        if 'suggest' in prompt_lower and 'resolution' in prompt_lower:
            return self._generate_resolution_suggestions(prompt)
        
        # Context summary
        if 'summar' in prompt_lower:
            return self._generate_summary(prompt)
        
        # Root cause analysis
        if 'root cause' in prompt_lower or 'cause' in prompt_lower:
            return self._generate_root_cause(prompt)
        
        return "AI analysis not available. Please install Ollama for full AI capabilities."
    
    def _generate_resolution_suggestions(self, prompt: str) -> str:
        """Generate resolution suggestions based on similar defects info."""
        suggestions = []
        
        # Extract patterns from prompt
        if 'timeout' in prompt.lower():
            suggestions.append("Review and adjust timeout configurations in the affected service")
        if 'validation' in prompt.lower():
            suggestions.append("Check input validation logic and add proper error handling")
        if 'payment' in prompt.lower():
            suggestions.append("Verify payment gateway integration and retry mechanisms")
        if 'database' in prompt.lower() or 'db' in prompt.lower():
            suggestions.append("Check database connection pool and query optimization")
        if 'api' in prompt.lower():
            suggestions.append("Review API endpoint configuration and authentication")
        if 'null' in prompt.lower() or 'empty' in prompt.lower():
            suggestions.append("Add null checks and input validation")
        
        if not suggestions:
            suggestions = [
                "Review the error logs for detailed stack traces",
                "Check recent code changes in the affected module",
                "Verify configuration settings match expected values"
            ]
        
        return "\n".join([f"• {s}" for s in suggestions[:3]])
    
    def _generate_summary(self, prompt: str) -> str:
        """Generate a basic summary."""
        # Extract key information from prompt
        lines = prompt.split('\n')
        summary_parts = []
        
        for line in lines:
            if 'summary:' in line.lower():
                summary_parts.append(line.split(':', 1)[-1].strip())
            elif 'defect' in line.lower() and ':' in line:
                summary_parts.append(line.split(':', 1)[-1].strip()[:100])
        
        if summary_parts:
            return f"This defect involves {summary_parts[0][:200]}. Based on similar past issues, investigation should focus on common failure points in this area."
        
        return "Analysis of the defect indicates potential issues in the affected system component. Review similar resolved defects for resolution patterns."
    
    def _generate_root_cause(self, prompt: str) -> str:
        """Generate root cause analysis."""
        causes = []
        prompt_lower = prompt.lower()
        
        if 'error' in prompt_lower:
            causes.append("Error handling gaps in the application logic")
        if 'timeout' in prompt_lower:
            causes.append("Network latency or service response time issues")
        if 'null' in prompt_lower:
            causes.append("Missing null pointer checks")
        if 'data' in prompt_lower:
            causes.append("Data validation or transformation issues")
        
        if not causes:
            causes = ["Further investigation needed to determine root cause"]
        
        return "Potential root causes:\n" + "\n".join([f"• {c}" for c in causes])
    
    def generate_resolution_suggestions(
        self,
        defect: Dict[str, Any],
        similar_defects: List[Dict[str, Any]]
    ) -> str:
        """
        Generate resolution suggestions based on defect and similar resolved defects.
        
        Args:
            defect: Current defect dictionary.
            similar_defects: List of similar resolved defects.
            
        Returns:
            Generated suggestions text.
        """
        # Build prompt
        prompt = f"""Based on the following defect and similar resolved defects, suggest possible resolutions.

Current Defect:
- Summary: {defect.get('Summary', 'N/A')}
- Description: {str(defect.get('Description', 'N/A'))[:500]}
- System: {defect.get('OSF-System', 'N/A')}

Similar Resolved Defects:
"""
        
        for i, sd in enumerate(similar_defects[:3], 1):
            metadata = sd.get('metadata', {})
            prompt += f"""
{i}. {metadata.get('issue_key', 'Unknown')} ({sd.get('similarity', 0)}% match)
   Summary: {metadata.get('summary', 'N/A')}
   Resolution: {metadata.get('fix_description', 'N/A')}
"""
        
        prompt += "\nSuggest 3 specific resolution steps based on these similar defects:"
        
        return self.generate(prompt, max_tokens=200, timeout=30)
    
    def generate_context_summary(
        self,
        defect: Dict[str, Any],
        similar_defects: List[Dict[str, Any]],
        related_docs: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a context summary for the defect.
        
        Args:
            defect: Current defect dictionary.
            similar_defects: List of similar defects.
            related_docs: List of related documents.
            
        Returns:
            Generated summary text.
        """
        prompt = f"""Provide a brief analysis summary for this defect:

Defect: {defect.get('Summary', 'N/A')}
Status: {defect.get('Status', 'N/A')}
Priority: {defect.get('Priority', 'N/A')}

Found {len(similar_defects)} similar past defects.
Found {len(related_docs)} related knowledge documents.

Provide a 2-3 sentence summary including:
1. What this defect is about
2. Most likely cause based on similar defects
3. Recommended next step
"""
        
        return self.generate(prompt, max_tokens=200, timeout=30)
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.ollama_available
