"""
Resolution Suggester Module
Generates AI-powered resolution suggestions based on similar defects.
"""

import logging
from typing import List, Dict, Any
from collections import Counter

logger = logging.getLogger(__name__)

class ResolutionSuggester:
    """
    Service for generating resolution suggestions based on similar resolved defects.
    Combines pattern analysis with LLM generation.
    """
    
    def __init__(self, llm_service):
        """
        Initialize the resolution suggester.
        
        Args:
            llm_service: LLMService instance.
        """
        self.llm_service = llm_service
    
    def suggest_resolutions(
        self,
        defect: Dict[str, Any],
        similar_defects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate resolution suggestions for a defect.
        
        Args:
            defect: The current defect to suggest resolutions for.
            similar_defects: List of similar past defects.
            
        Returns:
            Dictionary containing suggestions and analysis.
        """
        result = {
            'suggestions': [],
            'root_causes': [],
            'ai_suggestions': ''
        }
        
        # Filter for resolved defects
        resolved = [d for d in similar_defects if self._is_resolved(d)]
        
        if not resolved:
            result['suggestions'].append({
                'text': "No similar resolved defects found. Manual investigation required.",
                'source': 'system',
                'confidence': 'low'
            })
            return result
        
        # Extract resolutions from similar defects
        resolutions = self._extract_resolutions(resolved)
        result['suggestions'] = resolutions
        
        # Analyze root causes
        root_causes = self._analyze_root_causes(resolved)
        result['root_causes'] = root_causes
        
        # Generate AI suggestions if available
        if self.llm_service.is_available():
            try:
                ai_text = self.llm_service.generate_resolution_suggestions(defect, resolved)
                result['ai_suggestions'] = ai_text
            except Exception as e:
                logger.error(f"Failed to generate AI suggestions: {e}")
        
        return result
    
    def _is_resolved(self, defect: Dict[str, Any]) -> bool:
        """Check if a defect is resolved."""
        metadata = defect.get('metadata', {})
        status = str(metadata.get('status', '')).lower()
        resolution = str(metadata.get('resolution', '')).lower()
        fix_desc = str(metadata.get('fix_description', '')).lower()
        
        resolved_keywords = ['closed', 'resolved', 'done', 'fixed', 'verified', 'complete']
        
        return (
            any(kw in status for kw in resolved_keywords) or
            bool(resolution and resolution != 'nan') or
            bool(fix_desc and fix_desc != 'nan' and len(fix_desc) > 10)
        )
    
    def _extract_resolutions(self, resolved_defects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract resolution patterns from similar resolved defects.
        
        Args:
            resolved_defects: List of resolved defects.
            
        Returns:
            List of resolution suggestions.
        """
        suggestions = []
        
        for defect in resolved_defects[:5]:  # Top 5 similar
            metadata = defect.get('metadata', {})
            fix_desc = metadata.get('fix_description', '')
            issue_key = metadata.get('issue_key', 'Unknown')
            similarity = defect.get('similarity', 0)
            
            if fix_desc and str(fix_desc).lower() not in ['nan', 'none', '']:
                # Clean and truncate fix description
                fix_text = str(fix_desc).strip()[:500]
                
                suggestions.append({
                    'text': fix_text,
                    'source': issue_key,
                    'similarity': similarity,
                    'confidence': self._get_confidence(similarity)
                })
        
        # If no fix descriptions, use summary patterns
        if not suggestions:
            for defect in resolved_defects[:3]:
                metadata = defect.get('metadata', {})
                summary = metadata.get('summary', '')
                issue_key = metadata.get('issue_key', 'Unknown')
                similarity = defect.get('similarity', 0)
                
                if summary:
                    suggestions.append({
                        'text': f"Review resolution of similar issue: {summary[:200]}",
                        'source': issue_key,
                        'similarity': similarity,
                        'confidence': 'low'
                    })
        
        return suggestions
    
    def _analyze_root_causes(self, resolved_defects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze common root causes from similar defects.
        
        Args:
            resolved_defects: List of resolved defects.
            
        Returns:
            List of root cause patterns with frequencies.
        """
        # Keywords to look for in defect content
        cause_keywords = {
            'timeout': 'Timeout/Performance Issues',
            'validation': 'Validation Logic Errors',
            'null': 'Null Pointer/Empty Data',
            'database': 'Database Connection/Query Issues',
            'api': 'API Integration Issues',
            'configuration': 'Configuration Problems',
            'authentication': 'Authentication/Authorization Issues',
            'memory': 'Memory/Resource Issues',
            'network': 'Network Connectivity Issues',
            'data': 'Data Transformation/Format Issues'
        }
        
        cause_counts = Counter()
        
        for defect in resolved_defects:
            metadata = defect.get('metadata', {})
            content = f"{metadata.get('summary', '')} {metadata.get('fix_description', '')}".lower()
            
            for keyword, cause_name in cause_keywords.items():
                if keyword in content:
                    cause_counts[cause_name] += 1
        
        # Calculate percentages
        total = sum(cause_counts.values())
        if total == 0:
            return [{'cause': 'Investigation needed', 'percentage': 100, 'count': 0}]
        
        root_causes = []
        for cause, count in cause_counts.most_common(5):
            percentage = round((count / total) * 100)
            root_causes.append({
                'cause': cause,
                'percentage': percentage,
                'count': count
            })
        
        return root_causes
    
    def _get_confidence(self, similarity: float) -> str:
        """Get confidence level based on similarity score."""
        if similarity >= 90:
            return 'high'
        elif similarity >= 75:
            return 'medium'
        else:
            return 'low'
    
    def format_suggestions_for_display(self, suggestions_data: Dict[str, Any]) -> str:
        """
        Format suggestions for UI display.
        
        Args:
            suggestions_data: Output from suggest_resolutions().
            
        Returns:
            Formatted HTML/Markdown string.
        """
        output_parts = []
        
        # Resolution suggestions
        if suggestions_data.get('suggestions'):
            output_parts.append("### Suggested Resolutions\n")
            for i, sugg in enumerate(suggestions_data['suggestions'], 1):
                confidence_emoji = {'high': '🟢', 'medium': '🟡', 'low': '🟠'}.get(sugg.get('confidence', 'low'), '⚪')
                output_parts.append(f"{confidence_emoji} **Suggestion {i}** (from {sugg.get('source', 'Unknown')}, {sugg.get('similarity', 0)}% match)")
                output_parts.append(f"   {sugg.get('text', 'N/A')}\n")
        
        # Root causes
        if suggestions_data.get('root_causes'):
            output_parts.append("\n### Common Root Causes\n")
            for rc in suggestions_data['root_causes']:
                output_parts.append(f"• {rc['cause']} ({rc['percentage']}%)")
        
        # AI suggestions
        if suggestions_data.get('ai_suggestions'):
            output_parts.append("\n### AI Analysis\n")
            output_parts.append(suggestions_data['ai_suggestions'])
        
        return "\n".join(output_parts)
