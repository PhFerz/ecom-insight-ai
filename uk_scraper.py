import streamlit as st
import asyncio
import sys
import os
import pandas as pd
from playwright.async_api import async_playwright
import google.generativeai as genai

# Streamlit Cloud Deployment Fix: Install browser if it's missing
os.system("playwright install chromium")

# Windows specific event loop fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- PAGE CONFIG ---
st.set_page_config(page_title="E-Com Insight AI", page_icon="📈", layout="wide")

# --- API KEY CONFIGURATION ---
# It looks for GOOGLE_API_KEY in Streamlit Secrets first
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    # Hardcoded key as fallback for your initial testing
    GOOGLE_API_KEY = "AIzaSyAk8edisBQjw-5egn2seKJgf2OgknsaV1M"

# --- AI ENGINE ---
def analyze_market_intelligence(reviews_list):
    if not reviews_list:
        return "Error: No data available for AI analysis."
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Auto-detect available Gemini models
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        selected_model = None
        for m_name in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-2.0-flash-exp']:
            if m_name in available_models:
                selected_model = m_name
                break
        
        if not selected_model:
            selected_model = available_models[0] if available_models else None
        
        if not selected_model:
            return "Critical Error: No AI model access found for this key."

        model = genai.GenerativeModel(selected_model)
        
        reviews_summary = "\n".join([f"- {r}" for r in reviews_list])
        prompt = f"""
        Act as a Senior E-commerce Consultant. Analyze these Amazon UK customer reviews:
        
        REVIEWS:
        {reviews_summary}
        
        REPORT FORMAT:
        1. MARKET OPPORTUNITY SCORE (0-100)
        2. TOP 3 CUSTOMER PAIN POINTS
        3. STRATEGIC GROWTH SUGGESTION (Bundle ideas/Improvements)
        4. OVERALL SENTIMENT (Positive/Neutral/Negative)
        
        Response must be in English.
        """
        
        response = model.generate_content(prompt)
        return f"**Analysis Model:** {selected_model}\n\n{response.text}"
    except Exception as e:
        return f"AI System Error: {str(e)}"

# --- SCRAPER ENGINE ---
async def start_data_extraction(url):
    if not url.startswith("http"):
        url = "https://" + url

    extracted_reviews = []
    async with async_playwright() as p:
        # headless=True is mandatory for Cloud servers
        # We use headless=False for local debugging, but Cloud needs True
        is_cloud = "STREAMLIT_SERVER_PORT" in os.environ
        browser = await p.chromium.launch(headless=is_cloud)
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            st.info("🌐 Accessing Amazon UK...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 15s wait for Cloud stability or manual local CAPTCHA
            if not is_cloud:
                st.warning("⚠️ Local Mode: Solve CAPTCHA if it appears (15s)")
            await asyncio.sleep(15) 
            
            await page.wait_for_selector("[data-hook='review-body']", timeout=15000)
            elements = page.locator("[data-hook='review-body']")
            raw_data = await elements.all_inner_texts()
            extracted_reviews = [text.strip().replace('\n', ' ')[:400] for text in raw_data]
        except Exception as e:
            st.error(f"Scraper Error: {str(e)}")
        finally:
            await browser.close()
    return extracted_reviews

# --- STREAMLIT UI ---
st.title("🛡️ E-Com Insight AI: Global Intelligence")
st.markdown("### Business Strategy & Market Analysis for Amazon UK")

url_input = st.text_input("🔗 Paste Amazon UK Product URL:", placeholder="https://www.amazon.co.uk/dp/B09BZR9JFG")

if st.button("Generate Strategic Report"):
    if url_input:
        with st.status("🛸 SaaS Engine Working...", expanded=True) as status:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(start_data_extraction(url_input))
            loop.close()
            
            if results:
                status.update(label="Analysis Complete!", state="complete", expanded=False)
                st.balloons()
                
                report = analyze_market_intelligence(results)
                st.subheader("🤖 AI Strategic Report")
                st.markdown(report)
                
                with st.expander("View Source Data"):
                    st.table(pd.DataFrame(results, columns=["Captured Review Text"]))
            else:
                st.error("No reviews found. Try again or check the URL.")
    else:
        st.warning("Please enter a URL.")
