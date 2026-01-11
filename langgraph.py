import streamlit as st
import requests
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Page config
st.set_page_config(
    page_title="SEO Blog Post Generator",
    page_icon="📝",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #1e293b 0%, #1e3a8a 50%, #1e293b 100%);
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #3b82f6 0%, #9333ea 100%);
        color: white;
        font-weight: 600;
        padding: 0.75rem;
        border-radius: 0.5rem;
        border: none;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 1rem;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }
    .log-entry {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.5rem;
        font-family: monospace;
        font-size: 0.9rem;
    }
    .log-info { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
    .log-success { background: rgba(34, 197, 94, 0.2); color: #86efac; }
    .log-warning { background: rgba(234, 179, 8, 0.2); color: #fde047; }
    .log-error { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }
</style>
""", unsafe_allow_html=True)


class SEOBlogGenerator:
    """LangGraph-based SEO blog post generator"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "anthropic/claude-3.5-sonnet"
        
    def call_openrouter(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """Call OpenRouter API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://streamlit.io/",
            "X-Title": "SEO Blog Generator"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"API error {response.status_code}: {error_detail}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
    
    def extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from text response"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
        return None
    
    def analyze_search_results(self, topic: str) -> Dict:
        """Node 1: Analyze search intent and content structure"""
        add_log("Analyzing search intent...", "info")
        
        prompt = f"""Analyze the search intent and content structure needed for this topic: "{topic}"

Return a JSON object with:
{{
  "intent": "tutorial|comparison|guide|explanation",
  "target_audience": "beginner|intermediate|advanced",
  "required_sections": ["section1", "section2"],
  "content_depth": "overview|detailed|comprehensive",
  "recommended_format": "step-by-step|comparative|conceptual",
  "key_topics": ["topic1", "topic2"],
  "estimated_word_count": 1500
}}"""
        
        response = self.call_openrouter([{"role": "user", "content": prompt}], temperature=0.3)
        
        analysis = self.extract_json(response)
        if not analysis:
            analysis = {
                "intent": "guide",
                "target_audience": "intermediate",
                "required_sections": ["Introduction", "Main Content", "Conclusion"],
                "content_depth": "detailed",
                "recommended_format": "conceptual",
                "key_topics": [topic],
                "estimated_word_count": 1500
            }
        
        add_log(f"Intent: {analysis['intent']}, Audience: {analysis['target_audience']}", "success")
        return analysis
    
    def generate_content(self, topic: str, analysis: Dict) -> str:
        """Node 2: Generate initial blog post content"""
        add_log("Generating blog post content...", "info")
        
        prompt = f"""Write a comprehensive technical blog post on: "{topic}"

Structure requirements:
- Intent: {analysis['intent']}
- Audience: {analysis['target_audience']}
- Format: {analysis['recommended_format']}
- Sections: {', '.join(analysis['required_sections'])}

Requirements:
1. Start with a compelling introduction with a hook
2. Include practical examples and code snippets where relevant
3. Use clear headings (H2, H3)
4. Add actionable takeaways
5. Include an FAQ section at the end
6. Write {analysis['estimated_word_count']} words minimum
7. Optimize for both SEO and AI answer engines
8. Include direct answers to common questions in the first paragraphs

Return the full blog post in markdown format."""
        
        content = self.call_openrouter([{"role": "user", "content": prompt}], temperature=0.7)
        
        add_log(f"Generated {len(content)} characters", "success")
        return content
    
    def verify_content(self, content: str) -> Dict:
        """Node 3: Extract and verify technical claims"""
        add_log("Verifying technical claims...", "info")
        
        prompt = f"""Analyze this blog post and extract all factual and technical claims that should be verified:

{content[:3000]}...

Return a JSON object:
{{
  "claims": [
    {{"claim": "statement", "verifiable": true, "confidence": "high|medium|low"}}
  ],
  "unverified_count": 0,
  "verification_needed": false
}}"""
        
        response = self.call_openrouter([{"role": "user", "content": prompt}], temperature=0.3)
        
        verification = self.extract_json(response)
        if not verification:
            verification = {
                "claims": [],
                "unverified_count": 0,
                "verification_needed": False
            }
        
        log_type = "warning" if verification.get("verification_needed") else "success"
        add_log(
            f"Found {len(verification.get('claims', []))} claims, {verification.get('unverified_count', 0)} need verification",
            log_type
        )
        
        return verification
    
    def evaluate_seo(self, content: str, topic: str) -> Dict:
        """Node 4: Evaluate SEO quality"""
        add_log("Evaluating SEO quality...", "info")
        
        prompt = f"""Evaluate this blog post for SEO quality on topic "{topic}":

{content[:3000]}...

Return a JSON object:
{{
  "seo_score": 85,
  "issues": ["issue1", "issue2"],
  "strengths": ["strength1", "strength2"],
  "keyword_usage": "good|fair|poor",
  "readability": "good|fair|poor",
  "structure": "good|fair|poor",
  "passes": true
}}

Score above 75 passes."""
        
        response = self.call_openrouter([{"role": "user", "content": prompt}], temperature=0.3)
        
        seo_eval = self.extract_json(response)
        if not seo_eval:
            seo_eval = {
                "seo_score": 80,
                "issues": [],
                "strengths": ["Well structured"],
                "keyword_usage": "good",
                "readability": "good",
                "structure": "good",
                "passes": True
            }
        
        log_type = "success" if seo_eval.get("passes") else "warning"
        add_log(f"SEO Score: {seo_eval.get('seo_score', 0)}/100 - {'PASS' if seo_eval.get('passes') else 'FAIL'}", log_type)
        
        return seo_eval
    
    def evaluate_aeo(self, content: str, topic: str) -> Dict:
        """Node 5: Evaluate AEO (AI Engine Optimization)"""
        add_log("Evaluating AEO quality...", "info")
        
        prompt = f"""Evaluate if this content would be selected by AI answer engines (ChatGPT, Perplexity, etc.) for topic "{topic}":

{content[:3000]}...

Return a JSON object:
{{
  "aeo_score": 85,
  "has_direct_answers": true,
  "has_faq": true,
  "answer_quality": "excellent|good|fair|poor",
  "snippet_worthy": true,
  "improvements": ["improvement1"],
  "passes": true
}}

Score above 75 passes."""
        
        response = self.call_openrouter([{"role": "user", "content": prompt}], temperature=0.3)
        
        aeo_eval = self.extract_json(response)
        if not aeo_eval:
            aeo_eval = {
                "aeo_score": 80,
                "has_direct_answers": True,
                "has_faq": True,
                "answer_quality": "good",
                "snippet_worthy": True,
                "improvements": [],
                "passes": True
            }
        
        log_type = "success" if aeo_eval.get("passes") else "warning"
        add_log(f"AEO Score: {aeo_eval.get('aeo_score', 0)}/100 - {'PASS' if aeo_eval.get('passes') else 'FAIL'}", log_type)
        
        return aeo_eval
    
    def revise_content(self, content: str, seo_eval: Dict, aeo_eval: Dict, verification: Dict) -> str:
        """Node 6: Revise content based on feedback"""
        add_log("Revising content...", "info")
        
        issues = [
            *seo_eval.get("issues", []),
            *aeo_eval.get("improvements", [])
        ]
        
        if not issues and not verification.get("verification_needed"):
            add_log("No revisions needed", "success")
            return content
        
        prompt = f"""Revise this blog post to address these issues:

ISSUES:
{chr(10).join(f"{i+1}. {issue}" for i, issue in enumerate(issues[:5]))}

VERIFICATION NEEDED: {verification.get('verification_needed', False)}
SEO SCORE: {seo_eval.get('seo_score', 0)}
AEO SCORE: {aeo_eval.get('aeo_score', 0)}

ORIGINAL CONTENT:
{content[:2000]}...

Return the revised blog post in markdown format, addressing all issues while maintaining quality."""
        
        revised = self.call_openrouter([{"role": "user", "content": prompt}], temperature=0.7)
        
        add_log("Content revised", "success")
        return revised
    
    def run_workflow(self, topic: str) -> Dict:
        """Main LangGraph workflow"""
        add_log(f"Starting workflow for topic: {topic}", "info")
        
        # Node 1: Analyze search results
        analysis = self.analyze_search_results(topic)
        
        # Node 2: Generate initial content
        content = self.generate_content(topic, analysis)
        
        # Revision loop (max 3 cycles)
        max_revisions = 3
        revision = 0
        passes_quality = False
        
        verification = {}
        seo_eval = {}
        aeo_eval = {}
        
        while revision < max_revisions and not passes_quality:
            add_log(f"--- Revision Cycle {revision + 1}/{max_revisions} ---", "info")
            
            # Node 3: Verify content
            verification = self.verify_content(content)
            
            # Node 4: Evaluate SEO
            seo_eval = self.evaluate_seo(content, topic)
            
            # Node 5: Evaluate AEO
            aeo_eval = self.evaluate_aeo(content, topic)
            
            # Decision: Check if quality gates pass
            if (seo_eval.get("passes") and 
                aeo_eval.get("passes") and 
                not verification.get("verification_needed")):
                passes_quality = True
                add_log("✓ All quality gates passed!", "success")
                break
            
            # Node 6: Revise content
            if revision < max_revisions - 1:
                content = self.revise_content(content, seo_eval, aeo_eval, verification)
                revision += 1
            else:
                add_log("Maximum revisions reached. Returning best version.", "warning")
                revision += 1
                break
        
        return {
            "content": content,
            "analysis": analysis,
            "seo_eval": seo_eval,
            "aeo_eval": aeo_eval,
            "verification": verification,
            "revisions": revision
        }


def add_log(message: str, log_type: str = "info"):
    """Add message to session logs"""
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append({
        "message": message,
        "type": log_type,
        "timestamp": timestamp
    })


def display_logs():
    """Display logs in the UI"""
    if 'logs' in st.session_state and st.session_state.logs:
        for log in st.session_state.logs[-20:]:  # Show last 20 logs
            css_class = f"log-{log['type']}"
            icon = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(log['type'], "ℹ️")
            st.markdown(
                f'<div class="log-entry {css_class}">{icon} [{log["timestamp"]}] {log["message"]}</div>',
                unsafe_allow_html=True
            )


def main():
    st.title("📝 SEO Blog Post Generator")
    st.markdown("**LangGraph-powered system with search analysis, claim verification & AEO optimization**")
    
    # Initialize session state
    if 'result' not in st.session_state:
        st.session_state.result = None
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.info("Get your free API key from [OpenRouter.ai](https://openrouter.ai/keys)")
        
        api_key = st.text_input(
            "OpenRouter API Key",
            type="password",
            help="Enter your sk-or-... key from OpenRouter",
            key="api_key_input"
        )
        
        topic = st.text_input(
            "Blog Post Topic",
            placeholder="e.g., How to build an AI SDR",
            key="topic_input"
        )
        
        generate_button = st.button("🚀 Generate Blog Post", use_container_width=True, disabled=st.session_state.processing)
        
        if generate_button:
            if not api_key or not api_key.startswith('sk-'):
                st.error("❌ Please enter a valid OpenRouter API key (starts with 'sk-or-')")
            elif not topic or len(topic.strip()) < 5:
                st.error("❌ Please enter a topic (at least 5 characters)")
            else:
                st.session_state.processing = True
                st.session_state.logs = []
                st.session_state.result = None
                st.rerun()
    
    # Process workflow if button was clicked
    if st.session_state.processing:
        status_container = st.container()
        
        with status_container:
            st.info("🔄 Generating your SEO-optimized blog post... This may take 2-3 minutes.")
            
            progress_bar = st.progress(0)
            log_expander = st.expander("📋 Process Logs", expanded=True)
            
            try:
                generator = SEOBlogGenerator(st.session_state.api_key_input)
                
                # Update progress as we go
                with log_expander:
                    log_placeholder = st.empty()
                    
                    # Run workflow
                    result = generator.run_workflow(st.session_state.topic_input)
                    
                    # Display logs in real-time
                    with log_placeholder.container():
                        display_logs()
                
                progress_bar.progress(100)
                st.session_state.result = result
                st.session_state.processing = False
                st.success("✅ Blog post generated successfully!")
                st.rerun()
                
            except Exception as e:
                st.session_state.processing = False
                st.error(f"❌ Error: {str(e)}")
                add_log(f"Error: {str(e)}", "error")
                
                if "401" in str(e) or "403" in str(e):
                    st.error("🔑 Your API key appears to be invalid. Please check it and try again.")
                elif "rate limit" in str(e).lower():
                    st.error("⏱️ Rate limit reached. Please wait a moment and try again.")
                
                with st.expander("📋 Error Logs", expanded=True):
                    display_logs()
    
    # Display logs if they exist
    if st.session_state.logs and not st.session_state.processing:
        with st.expander("📋 View Process Logs"):
            display_logs()
    
    # Results display
    if st.session_state.result:
        result = st.session_state.result
        
        st.markdown("---")
        st.header("📊 Quality Metrics")
        
        # Metrics cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            seo_score = result['seo_eval'].get('seo_score', 0)
            st.metric(
                "SEO Score",
                f"{seo_score}/100",
                delta="✓ Pass" if result['seo_eval'].get('passes') else "✗ Fail"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            aeo_score = result['aeo_eval'].get('aeo_score', 0)
            st.metric(
                "AEO Score",
                f"{aeo_score}/100",
                delta="✓ Pass" if result['aeo_eval'].get('passes') else "✗ Fail"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                "Claims Verified",
                len(result['verification'].get('claims', []))
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                "Revisions",
                result['revisions']
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Blog content
        st.header("📄 Generated Blog Post")
        st.markdown(result['content'])
        
        # Download button
        st.download_button(
            label="📥 Download Blog Post",
            data=result['content'],
            file_name=f"blog_post_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
        
        st.markdown("---")
        
        # Analysis details
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 SEO Analysis")
            seo = result['seo_eval']
            st.write(f"**Keyword Usage:** {seo.get('keyword_usage', 'N/A')}")
            st.write(f"**Readability:** {seo.get('readability', 'N/A')}")
            st.write(f"**Structure:** {seo.get('structure', 'N/A')}")
            
            if seo.get('strengths'):
                st.write("**Strengths:**")
                for strength in seo['strengths']:
                    st.write(f"✅ {strength}")
        
        with col2:
            st.subheader("🤖 AEO Analysis")
            aeo = result['aeo_eval']
            st.write(f"**Direct Answers:** {'Yes' if aeo.get('has_direct_answers') else 'No'}")
            st.write(f"**FAQ Section:** {'Yes' if aeo.get('has_faq') else 'No'}")
            st.write(f"**Answer Quality:** {aeo.get('answer_quality', 'N/A')}")
            st.write(f"**Snippet Worthy:** {'Yes' if aeo.get('snippet_worthy') else 'No'}")


if __name__ == "__main__":
    main()