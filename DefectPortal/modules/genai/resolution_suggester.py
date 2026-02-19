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
        similar_defects: List[Dict[str, Any]],
        skip_llm: bool = False
    ) -> Dict[str, Any]:
        """
        Generate resolution suggestions for a defect.
        
        Args:
            defect: The current defect to suggest resolutions for.
            similar_defects: List of similar past defects.
            skip_llm: If True, return suggestions and root_causes only (no LLM call). Use for parallel flow.
            
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
        
        # Generate AI suggestions if available (skip when skip_llm for parallel execution)
        if not skip_llm and self.llm_service.is_available():
            try:
                ai_text = self.llm_service.generate_resolution_suggestions(defect, resolved)
                result['ai_suggestions'] = ai_text
            except Exception as e:
                logger.error(f"Failed to generate AI suggestions: {e}")
        
        return result

    def fill_ai_suggestions(
        self,
        result: Dict[str, Any],
        defect: Dict[str, Any],
        similar_defects: List[Dict[str, Any]]
    ) -> None:
        """Fill result['ai_suggestions'] via LLM. Updates result in place. For use in parallel with context summary."""
        resolved = [d for d in similar_defects if self._is_resolved(d)]
        if not resolved or not self.llm_service.is_available():
            return
        try:
            result['ai_suggestions'] = self.llm_service.generate_resolution_suggestions(defect, resolved)
        except Exception as e:
            logger.error(f"Failed to generate AI suggestions: {e}")
    
    def _is_resolved(self, defect: Dict[str, Any]) -> bool:
        """Check if a defect is resolved (Status or DB Resolution column)."""
        metadata = defect.get('metadata', {})
        status = str(metadata.get('status', '')).lower()
        resolution = str(metadata.get('resolution', '')).lower()
        fix_desc = str(metadata.get('fix_description', '')).lower()
        
        resolved_keywords = ['closed', 'resolved', 'done', 'fixed', 'verified', 'complete']
        
        return (
            any(kw in status for kw in resolved_keywords) or
            any(kw in resolution for kw in resolved_keywords) or
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
        Derive one common root cause from similar defects (from resolutions/fix text or keyword patterns).
        Returns a single best root cause when possible; avoids generic "Investigation needed" when
        matched defects have fix_description or resolution text.
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
            'permission': 'Permission/Authorization Issues',
            'memory': 'Memory/Resource Issues',
            'network': 'Network Connectivity Issues',
            'data': 'Data Transformation/Format Issues',
            'error': 'Error/Exception Handling',
            'integration': 'Integration/Service Issues',
        }
        
        cause_counts = Counter()
        
        for defect in resolved_defects:
            metadata = defect.get('metadata', {})
            content = f"{metadata.get('summary', '')} {metadata.get('fix_description', '')} {metadata.get('resolution', '')}".lower()
            
            for keyword, cause_name in cause_keywords.items():
                if keyword in content:
                    cause_counts[cause_name] += 1
        
        total = sum(cause_counts.values())
        if total > 0:
            # Return single most common root cause (one common root cause from matched defects)
            top_cause, top_count = cause_counts.most_common(1)[0]
            percentage = round((top_count / len(resolved_defects)) * 100)
            return [{'cause': top_cause, 'percentage': min(percentage, 100), 'count': top_count}]
        
        # No keyword match: derive one root cause from top similar defect's fix/resolution text
        for defect in resolved_defects:
            metadata = defect.get('metadata', {})
            fix_desc = (metadata.get('fix_description') or '').strip()
            resolution = (metadata.get('resolution') or '').strip()
            issue_key = metadata.get('issue_key', '')
            
            if fix_desc and str(fix_desc).lower() not in ('nan', 'none', '') and len(fix_desc) > 20:
                # Use first sentence or first 220 chars as the common root cause
                first_sentence = fix_desc.replace('\n', ' ').strip()
                for sep in ('. ', '; ', '\n'):
                    if sep in first_sentence:
                        first_sentence = first_sentence.split(sep)[0].strip() + ('.' if sep == '. ' else '')
                        break
                first_sentence = (first_sentence[:220] + '…') if len(first_sentence) > 220 else first_sentence
                if issue_key:
                    return [{'cause': f"From similar defect {issue_key}: {first_sentence}", 'percentage': 100, 'count': 1}]
                return [{'cause': first_sentence, 'percentage': 100, 'count': 1}]
            
            if resolution and str(resolution).lower() not in ('nan', 'none', 'unresolved', 'fixed', 'done', '') and len(resolution) > 15:
                cause_text = resolution[:200] + ('…' if len(resolution) > 200 else '')
                if issue_key:
                    return [{'cause': f"From similar defect {issue_key}: {cause_text}", 'percentage': 100, 'count': 1}]
                return [{'cause': cause_text, 'percentage': 100, 'count': 1}]
        
        # No usable fix/resolution text: single placeholder (UI may hide or soften this)
        return [{'cause': 'Investigation needed', 'percentage': 100, 'count': 0}]
    
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
            output_parts.append("\n### Common Root Cause\n")
            for rc in suggestions_data['root_causes']:
                output_parts.append(f"• {rc['cause']} ({rc['percentage']}%)")
        
        # AI suggestions
        if suggestions_data.get('ai_suggestions'):
            output_parts.append("\n### AI Analysis\n")
            output_parts.append(suggestions_data['ai_suggestions'])
        
        return "\n".join(output_parts)
