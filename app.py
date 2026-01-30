import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import io
import time

# Page setup
st.set_page_config(page_title="Article to Excel Extractor", layout="centered", page_icon="📄")

# Custom CSS to make it look nice
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stTextInput > div > input {
        font-size: 16px;
    }
    .success-text {
        color: #4CAF50;
        font-weight: bold;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("📄 Article to Excel Extractor")
st.markdown("**Paste any article URL and download the content as an Excel file in one click**")

# Create tabs for Single vs Batch
tab1, tab2 = st.tabs(["📝 Single Article", "📚 Batch Download (Multiple URLs)"])

def extract_article(url):
    """Extract article data from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        with st.spinner(f'Loading {url[:50]}...'):
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "advertisement"]):
                element.decompose()
            
            # Extract title
            title = "No title found"
            if soup.title:
                title = soup.title.string
            elif soup.find('h1'):
                title = soup.find('h1').get_text(strip=True)
            
            # Extract main content
            article_body = soup.find('article') or soup.find('main') or soup.find('div', class_='content') or soup.find('div', class_='post')
            
            if article_body:
                text = article_body.get_text(separator='\n', strip=True)
            else:
                # Fallback to body text
                text = soup.get_text(separator='\n', strip=True)
            
            # Clean up text
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = '\n'.join(lines)
            
            # Get domain
            domain = url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'
            
            return {
                'title': title,
                'url': url,
                'domain': domain,
                'text': clean_text,
                'word_count': len(clean_text.split()),
                'date_extracted': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'success'
            }
            
    except Exception as e:
        return {
            'title': 'Error',
            'url': url,
            'domain': 'error',
            'text': str(e),
            'word_count': 0,
            'date_extracted': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': f'failed: {str(e)}'
        }

def create_excel_download(data, filename_prefix="Article"):
    """Create Excel file for download"""
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame([data])
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Extracted Content')
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Extracted Content']
        for i, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + i)].width = min(max_length, 50)
    
    return output.getvalue()

# TAB 1: Single Article
with tab1:
    st.subheader("Extract Single Article")
    
    url_input = st.text_input(
        "Paste article URL here:", 
        placeholder="https://www.example.com/article",
        key="single_url"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        extract_btn = st.button("🔍 Extract Article", type="primary", use_container_width=True)
    
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.single_result = None
            st.rerun()
    
    if extract_btn and url_input:
        if not url_input.startswith(('http://', 'https://')):
            st.error("⚠️ Please include http:// or https:// in the URL")
        else:
            result = extract_article(url_input)
            st.session_state.single_result = result
            
            if result['status'] == 'success':
                st.success(f"✅ Successfully extracted: {result['title'][:60]}...")
                
                # Show info box
                st.markdown(f"""
                <div class="info-box">
                    <strong>Title:</strong> {result['title']}<br>
                    <strong>Domain:</strong> {result['domain']}<br>
                    <strong>Word Count:</strong> {result['word_count']} words<br>
                    <strong>Extracted:</strong> {result['date_extracted']}
                </div>
                """, unsafe_allow_html=True)
                
                # Preview expander
                with st.expander("👁️ Preview Content (first 1000 characters)"):
                    st.write(result['text'][:1000] + "..." if len(result['text']) > 1000 else result['text'])
                
                # Download button
                safe_title = "".join([c for c in result['title'][:20] if c.isalnum() or c in (' ', '-', '_')]).rstrip().replace(' ', '_')
                filename_prefix = "Article"
                
            filename = f"{filename_prefix}_{safe_title}.xlsx"
                
            excel_data = create_excel_download(result)
                
            st.download_button(
                    label=f"📥 Download Excel ({len(result['text'])} characters)",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.error(f"❌ Failed to extract: {result['text']}")

# TAB 2: Batch Processing
with tab2:
    st.subheader("Extract Multiple Articles")
    st.caption("Enter one URL per line (up to 20 URLs recommended)")
    
    batch_urls = st.text_area(
        "Paste URLs here (one per line):",
        height=150,
        placeholder="https://example.com/article1\nhttps://example.com/article2",
        key="batch_urls"
    )
    
    if st.button("🚀 Process All URLs", type="primary", use_container_width=True):
        urls = [url.strip() for url in batch_urls.split('\n') if url.strip()]
        
        if not urls:
            st.warning("Please enter at least one URL")
        elif len(urls) > 20:
            st.warning("For best performance, please process max 20 URLs at a time")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            results = []
            
            for i, url in enumerate(urls):
                status_text.text(f"Processing {i+1} of {len(urls)}: {url[:50]}...")
                
                if not url.startswith(('http://', 'https://')):
                    results.append({
                        'url': url,
                        'title': 'Invalid URL',
                        'status': 'failed: Missing http:// or https://',
                        'text': ''
                    })
                else:
                    result = extract_article(url)
                    results.append(result)
                    time.sleep(0.5)  # Be nice to servers
                
                progress_bar.progress((i + 1) / len(urls))
            
            status_text.empty()
            progress_bar.empty()
            
            # Summary
            successful = len([r for r in results if r['status'] == 'success'])
            failed = len(results) - successful
            
            if successful == len(results):
                st.success(f"✅ All {len(results)} articles extracted successfully!")
            else:
                st.warning(f"⚠️ Completed: {successful} successful, {failed} failed")
            
            # Show results table
            with st.expander("View Results Summary"):
                summary_df = pd.DataFrame([
                    {'URL': r['url'][:50] + '...', 'Title': r['title'][:40], 'Status': r['status'], 'Words': r['word_count']} 
                    for r in results
                ])
                st.dataframe(summary_df, use_container_width=True)
            
            # Download all
            excel_data = create_excel_download(results, "Batch_Articles")
            st.download_button(
                label=f"📥 Download All Articles Excel ({len(results)} rows)",
                data=excel_data,
                file_name=f"Batch_Articles_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# Footer
st.divider()
st.caption("""
💡 **Tips:** 
- Make sure URLs start with http:// or https://
- Some websites block scrapers (try adding www. or removing it)
- For paywalled content, this won't work unless you have access

""")


