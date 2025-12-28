import streamlit as st
import asyncio
import sys
import os
import pandas as pd
from playwright.async_api import async_playwright
import google.generativeai as genai

# Mandatory fix for Windows subprocesses and event loops
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- PAGE UI CONFIGURATION ---
st.set_page_config(page_title="E-Com Insight AI", page_icon="📈", layout="wide")

# --- SECURE API CONFIGURATION ---
# Note: When deploying, add GOOGLE_API_KEY to Streamlit's "Secrets" panel
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # Fallback for local testing (only if secrets are not set)
    GOOGLE_API_KEY = "AIzaSyAk8edisBQjw-5egn2seKJgf2OgknsaV1M"

# --- AI INTELLIGENCE ENGINE (Auto-Discovery) ---
def analyze_market_intelligence(reviews_list):
    if not reviews_list:
        return "Error: No customer feedback found to analyze."
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Discover available models to prevent 404 errors
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Preference Order: Flash 1.5 -> Pro 1.5 -> Any available
        selected_model = None
        for m_name in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-1.0-pro']:
            if m_name in available_models:
                selected_model = m_name
                break
        
        if not selected_model:
            selected_model = available_models[0] if available_models else None

        if not selected_model:
            return "Critical Error: No generative AI models found for this API key."

        model = genai.GenerativeModel(selected_model)
        
        # Prepare the data for the AI consultant
        reviews_summary = "\n".join([f"- {r}" for r in reviews_list])
        
        prompt = f"""
        Act as a professional E-commerce Strategy Consultant for the UK market. 
        Analyze the following Amazon customer reviews and provide a strategic report:
        
        REVIEWS:
        {reviews_summary}
        
        REPORT STRUCTURE:
        1. MARKET OPPORTUNITY SCORE (0-100)
        2. TOP 3 CUSTOMER PAIN POINTS (What specifically are they struggling with?)
        3. STRATEGIC GROWTH SUGGESTION (Bundle ideas, cross-sell items, or specific improvements)
        4. OVERALL SENTIMENT (Positive/Neutral/Negative)
        
        Tone: Professional, data-driven, and actionable for a business owner.
        """
        
        response = model.generate_content(prompt)
        return f"**Analysis Model:** {selected_model}\n\n{response.text}"
        
    except Exception as e:
        return f"AI System Error: {str(e)}. Please check your Google AI Studio permissions."

# --- DATA SCRAPER ENGINE (Playwright) ---
async def start_data_extraction(url):
    # Auto-fix missing protocol
    if not url.startswith("http"):
        url = "https://" + url

    extracted_reviews = []
    async with async_playwright() as p:
        # headless=False is safer for local bypass; Streamlit Cloud handles this automatically
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            st.info("🌐 Connecting to Amazon UK Server...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 15s window for manual CAPTCHA solving if it appears
            st.warning("⚠️ SECURITY CHECK: If a CAPTCHA appears, please solve it in the browser window (15s wait).")
            await asyncio.sleep(15) 
            
            # Detect and scrape review bodies
            await page.wait_for_selector("[data-hook='review-body']", timeout=12000)
            elements = page.locator("[data-hook='review-body']")
            count = await elements.count()
            
            if count > 0:
                raw_data = await elements.all_inner_texts()
                # Clean text and limit to 400 chars per review for AI prompt efficiency
                extracted_reviews = [text.strip().replace('\n', ' ')[:400] for text in raw_data]
        except Exception as e:
            st.error(f"Scraper Engine Error: {str(e)}")
            await page.screenshot(path="debug_screenshot.png")
        finally:
            await browser.close()
    return extracted_reviews

# --- STREAMLIT DASHBOARD UI ---
st.title("🛡️ E-Com Insight AI: Global Intelligence Portal")
st.markdown("### Helping Sheffield businesses dominate Amazon UK market through AI.")

st.sidebar.header("Platform Status")
st.sidebar.success("AI Engine: Google Gemini 1.5")
st.sidebar.info("Region: United Kingdom")

product_url = st.text_input("🔗 Paste Amazon UK Product URL:", placeholder="e.g., https://www.amazon.co.uk/dp/B09BZR9JFG")

if st.button("Generate Strategic Analysis Report"):
    if product_url:
        with st.status("🛸 SaaS Engine: Extracting Market Data & Consulting AI...", expanded=True) as status:
            # Execute the scraper
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(start_data_extraction(product_url))
            loop.close()
            
            if results:
                status.update(label="Data Captured! Synthesizing AI Report...", state="running")
                
                # Execute AI Consultation
                report = analyze_market_intelligence(results)
                
                status.update(label="Intelligence Report Complete!", state="complete", expanded=False)
                st.balloons()
                
                # Main Analysis Output
                st.subheader("🤖 AI Strategic Market Intelligence")
                st.markdown(report)
                
                # Source Data Expandable Section
                with st.expander("View Raw Intelligence Sources (Scraped Reviews)"):
                    st.table(pd.DataFrame(results, columns=["Review Data"]))
            else:
                status.update(label="Process Failed.", state="error")
                st.error("No reviews found. Please ensure the URL is correct and CAPTCHA was solved.")
    else:
        st.warning("Please enter a valid Amazon URL to begin.")