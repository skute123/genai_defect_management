"""
Context Summarizer Module
Generates AI-powered context summaries for defects.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ContextSummarizer:
    """
    Service for generating comprehensive context summaries for defects.
    Combines defect analysis with similar defects and documentation.
    """
    
    def __init__(self, llm_service):
        """
        Initialize the context summarizer.
        
        Args:
            llm_service: LLMService instance.
        """
        self.llm_service = llm_service
    
    def generate_summary(
        self,
        defect: Dict[str, Any],
        similar_defects: List[Dict[str, Any]],
        related_docs: List[Dict[str, Any]],
        resolution_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive context summary.
        
        Args:
            defect: The current defect.
            similar_defects: List of similar defects found.
            related_docs: List of related knowledge documents.
            resolution_data: Optional resolution suggestion data.
            
        Returns:
            Dictionary containing the summary and insights.
        """
        summary = {
            'overview': '',
            'likely_cause': '',
            'recommended_action': '',
            'historical_insights': {},
            'document_insights': [],
            'full_summary': ''
        }
        
        # Generate overview
        summary['overview'] = self._generate_overview(defect)
        
        # Analyze likely cause from similar defects
        summary['likely_cause'] = self._analyze_likely_cause(defect, similar_defects, resolution_data)
        
        # Recommend action
        summary['recommended_action'] = self._recommend_action(defect, similar_defects, related_docs)
        
        # Historical insights
        summary['historical_insights'] = self._calculate_historical_insights(similar_defects)
        
        # Document insights
        summary['document_insights'] = self._extract_document_insights(related_docs)
        
        # Generate full AI summary if available
        if self.llm_service.is_available():
            try:
                summary['full_summary'] = self.llm_service.generate_context_summary(
                    defect, similar_defects, related_docs
                )
            except Exception as e:
                logger.error(f"Failed to generate AI summary: {e}")
                summary['full_summary'] = self._generate_fallback_summary(summary)
        else:
            summary['full_summary'] = self._generate_fallback_summary(summary)
        
        return summary
    
    def _generate_overview(self, defect: Dict[str, Any]) -> str:
        """Generate a brief overview of the defect."""
        summary_text = defect.get('Summary', 'No summary available')
        status = defect.get('Status', 'Unknown')
        priority = defect.get('Priority', 'Unknown')
        system = defect.get('OSF-System', 'Unknown')
        
        return f"This is a {priority} priority defect in {system} system, currently {status}. {summary_text[:200]}"
    
    def _analyze_likely_cause(
        self,
        defect: Dict[str, Any],
        similar_defects: List[Dict[str, Any]],
        resolution_data: Optional[Dict[str, Any]]
    ) -> str:
        """Analyze the most likely cause based on similar defects."""
        if resolution_data and resolution_data.get('root_causes'):
            top_cause = resolution_data['root_causes'][0]
            return f"{top_cause['cause']} (based on {top_cause['percentage']}% of similar issues)"
        
        if not similar_defects:
            return "Unable to determine - no similar defects found for analysis"
        
        # Analyze content of similar defects
        keywords_found = []
        for sd in similar_defects[:3]:
            metadata = sd.get('metadata', {})
            content = f"{metadata.get('summary', '')} {metadata.get('fix_description', '')}".lower()
            
            if 'timeout' in content:
                keywords_found.append('timeout issues')
            if 'validation' in content:
                keywords_found.append('validation errors')
            if 'configuration' in content or 'config' in content:
                keywords_found.append('configuration problems')
            if 'data' in content:
                keywords_found.append('data issues')
        
        if keywords_found:
            from collections import Counter
            most_common = Counter(keywords_found).most_common(1)[0][0]
            return f"Most likely: {most_common.title()} (based on pattern analysis)"
        
        return "Further investigation needed to determine root cause"
    
    def _recommend_action(
        self,
        defect: Dict[str, Any],
        similar_defects: List[Dict[str, Any]],
        related_docs: List[Dict[str, Any]]
    ) -> str:
        """Recommend the next action based on analysis."""
        actions = []
        
        # If we have related documents, recommend reviewing them
        if related_docs:
            top_doc = related_docs[0]
            doc_name = top_doc.get('metadata', {}).get('filename', 'documentation')
            actions.append(f"Review {doc_name} for detailed flow information")
        
        # If we have similar resolved defects
        resolved = [d for d in similar_defects if 
                   'closed' in str(d.get('metadata', {}).get('status', '')).lower() or
                   d.get('metadata', {}).get('fix_description')]
        
        if resolved:
            top_similar = resolved[0]
            issue_key = top_similar.get('metadata', {}).get('issue_key', 'similar issue')
            actions.append(f"Review resolution of {issue_key} ({top_similar.get('similarity', 0)}% similar)")
        
        if not actions:
            actions.append("Investigate error logs and stack traces")
            actions.append("Review recent changes in the affected module")
        
        return "; ".join(actions[:2])
    
    def _calculate_historical_insights(self, similar_defects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate historical insights from similar defects."""
        insights = {
            'total_similar': len(similar_defects),
            'resolved_count': 0,
            'resolution_rate': 0,
            'avg_similarity': 0
        }
        
        if not similar_defects:
            return insights
        
        # Count resolved
        resolved_count = 0
        for sd in similar_defects:
            metadata = sd.get('metadata', {})
            status = str(metadata.get('status', '')).lower()
            if 'closed' in status or 'resolved' in status or 'done' in status:
                resolved_count += 1
        
        insights['resolved_count'] = resolved_count
        insights['resolution_rate'] = round((resolved_count / len(similar_defects)) * 100) if similar_defects else 0
        
        # Average similarity
        similarities = [sd.get('similarity', 0) for sd in similar_defects]
        insights['avg_similarity'] = round(sum(similarities) / len(similarities)) if similarities else 0
        
        return insights
    
    def _extract_document_insights(self, related_docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract key insights from related documents."""
        insights = []
        
        for doc in related_docs[:3]:
            metadata = doc.get('metadata', {})
            content = doc.get('content', '')[:300]
            
            insights.append({
                'filename': metadata.get('filename', 'Unknown'),
                'section': metadata.get('section', ''),
                'relevance': f"{doc.get('similarity', 0)}%",
                'snippet': content
            })
        
        return insights
    
    def _generate_fallback_summary(self, summary_data: Dict[str, Any]) -> str:
        """Generate a fallback summary without LLM."""
        parts = []
        
        parts.append(f"📝 {summary_data.get('overview', 'Defect analysis in progress.')}")
        
        likely_cause = summary_data.get('likely_cause', '')
        if likely_cause:
            parts.append(f"\n• Most likely cause: {likely_cause}")
        
        recommended = summary_data.get('recommended_action', '')
        if recommended:
            parts.append(f"• Recommended action: {recommended}")
        
        insights = summary_data.get('historical_insights', {})
        if insights.get('total_similar', 0) > 0:
            parts.append(f"• Historical fix rate: {insights.get('resolution_rate', 0)}% of similar defects were resolved")
        
        return "\n".join(parts)
    
    def format_summary_for_display(self, summary_data: Dict[str, Any]) -> str:
        """
        Format summary for UI display.
        
        Args:
            summary_data: Output from generate_summary().
            
        Returns:
            Formatted text for display.
        """
        output = []
        
        output.append("### 📝 AI Context Summary\n")
        output.append(summary_data.get('full_summary', 'Summary not available.'))
        
        # Historical insights
        insights = summary_data.get('historical_insights', {})
        if insights.get('total_similar', 0) > 0:
            output.append("\n\n**Historical Data:**")
            output.append(f"• Similar defects found: {insights.get('total_similar', 0)}")
            output.append(f"• Resolution rate: {insights.get('resolution_rate', 0)}%")
            output.append(f"• Average similarity: {insights.get('avg_similarity', 0)}%")
        
        return "\n".join(output)
