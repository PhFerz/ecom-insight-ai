import subprocess
import sys
import os
import asyncio

# --- CLOUD SELF-REPAIR: Installs missing libraries automatically ---
def install_dependencies():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Installing Playwright...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    
    # Ensure Chromium is installed for Playwright
    os.system("playwright install chromium")

install_dependencies()

import streamlit as st
import pandas as pd
import google.generativeai as genai
from playwright.async_api import async_playwright

# Windows event loop fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- PAGE CONFIG ---
st.set_page_config(page_title="E-Com Insight AI", page_icon="📈", layout="wide")

# --- SECURE API KEY ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    # Local fallback
    GOOGLE_API_KEY = "AIzaSyAk8edisBQjw-5egn2seKJgf2OgknsaV1M"

# --- AI ANALYSIS ENGINE ---
def analyze_market_intelligence(reviews_list):
    if not reviews_list:
        return "No data available."
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Auto-detect available models
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        selected_model = None
        for m_name in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro']:
            if m_name in available_models:
                selected_model = m_name
                break
        
        if not selected_model:
            selected_model = available_models[0] if available_models else None

        model = genai.GenerativeModel(selected_model)
        
        reviews_summary = "\n".join([f"- {r}" for r in reviews_list])
        prompt = f"""
        Act as a professional E-commerce Strategy Consultant. 
        Analyze these Amazon UK customer reviews and provide a strategic report in English:
        
        REVIEWS:
        {reviews_summary}
        
        REPORT FORMAT:
        1. MARKET OPPORTUNITY SCORE (0-100)
        2. TOP 3 CUSTOMER PAIN POINTS
        3. STRATEGIC GROWTH SUGGESTION
        4. OVERALL SENTIMENT
        """
        
        response = model.generate_content(prompt)
        return f"**Model Used:** {selected_model}\n\n{response.text}"
    except Exception as e:
        return f"AI System Error: {str(e)}"

# --- WEB SCRAPER ENGINE ---
async def start_data_extraction(url):
    if not url.startswith("http"):
        url = "https://" + url

    extracted_reviews = []
    async with async_playwright() as p:
        # headless=True is mandatory for Cloud
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            st.info("🌐 Accessing Amazon UK Server...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Static wait for page elements to settle
            await asyncio.sleep(10) 
            
            # Scrape reviews
            await page.wait_for_selector("[data-hook='review-body']", timeout=15000)
            elements = page.locator("[data-hook='review-body']")
            count = await elements.count()
            
            if count > 0:
                raw_data = await elements.all_inner_texts()
                extracted_reviews = [text.strip().replace('\n', ' ')[:400] for text in raw_data]
        except Exception as e:
            st.error(f"Scraper Error: {str(e)}")
        finally:
            await browser.close()
    return extracted_reviews

# --- USER INTERFACE ---
st.title("🛡️ E-Com Insight AI: Global Intelligence")
st.markdown("### Strategic Market Analysis for Amazon UK Products")

url_input = st.text_input("🔗 Paste Amazon UK Product URL:", placeholder="https://www.amazon.co.uk/dp/B09BZR9JFG")

if st.button("Generate Intelligence Report"):
    if url_input:
        with st.status("🛸 SaaS Engine: Processing Data...", expanded=True) as status:
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
                
                with st.expander("Show Captured Sources"):
                    st.table(pd.DataFrame(results, columns=["Review Snippet"]))
            else:
                st.error("No reviews found. Amazon may be temporarily blocking the request. Please try again.")
    else:
        st.warning("Please provide a product URL.")
