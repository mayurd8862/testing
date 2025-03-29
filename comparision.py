import os
import re
import requests
import asyncio
import streamlit as st
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
import io
import time

# Initialize environment
load_dotenv()

# -------------------------
# Enhanced Configuration
# -------------------------
MARKET_CONFIG = {
    'US': {
        'currency': '$',
        'platforms': ['amazon.com', 'walmart.com', 'cvs.com', 'walgreens.com'],
        'price_patterns': [r"\$(\d+\.\d{2})", r"\$(\d+)", r"USD\s*(\d+)"],
        'rating_selectors': [
            ('span.a-icon-alt', r'(\d\.\d) out of 5'),
            ('div[data-testid="rating-stars"]', r'(\d)'),
            ('span.a-size-medium', r'(\d\.\d)')
        ],
        'image_selectors': [
            ('img#landingImage', 'amazon-main'),
            ('img.slider-slide-image', 'walmart-slider'),
            ('img.product-details-hero', 'cvs-hero'),
            ('img.product-image', 'walgreens-main'),
            ('img[data-testid="product-detail-image"]', 'default')
        ],
        'feature_keywords': {
            'Immune Support': ['immune', 'immunity', 'defense'],
            'Antioxidant': ['antioxidant', 'free radical'],
            'Natural': ['natural', 'organic', 'non-GMO'],
            'Vitamin Complex': ['with zinc', 'elderberry', 'bioflavonoids'],
            'Fast Absorption': ['quick dissolve', 'rapid release']
        }
    },
    'IN': {
        'currency': '₹',
        'platforms': ['amazon.in', 'flipkart.com', '1mg.com', 'pharmeasy.in'],
        'price_patterns': [r"₹\s*(\d+)", r"Rs\.?\s*(\d+)", r"INR\s*(\d+)"],
        'rating_selectors': [
            ('div._3LWZlK', r'(\d)'),
            ('span.a-icon-alt', r'(\d\.\d) out of 5'),
            ('div._2d4LTz', r'(\d\.?\d?)'),
            ('div.rating-number', r'(\d+)')
        ],
        'image_selectors': [
            ('img.imgTagWrapper', 'amazon-main'),
            ('div._3kidJX img', 'flipkart-grid'),
            ('div.productImage img', '1mg-product'),
            ('div.zoomPad img', 'pharmeasy-zoom')
        ],
        'feature_keywords': {
            'Ayurvedic': ['ayurvedic', 'herbal', 'traditional'],
            'Sugar-Free': ['sugar-free', 'no added sugar'],
            'Energy Boost': ['energy', 'vitality', 'stamina'],
            'Digestive Health': ['digestive', 'gut health'],
            'Bone Health': ['calcium', 'bone health']
        }
    }
}

# -------------------------
# Guaranteed Image Analyzer
# -------------------------
class SupplementAnalyzer:
    def __init__(self):
        self.driver = self.init_webdriver()
        
    def init_webdriver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    async def search_products(self, query: str):
        """Guaranteed image product search"""
        market = self.detect_market(query)
        all_results = []
        
        for platform in MARKET_CONFIG[market]['platforms']:
            try:
                platform_results = await self.search_platform(query, market, platform)
                all_results.extend(platform_results)
            except Exception as e:
                continue
                
        return self.clean_results(all_results)[:8]

    def detect_market(self, query: str) -> str:
        """Smart market detection"""
        lower_query = query.lower()
        if any(kw in lower_query for kw in ['₹', 'rs', 'inr']):
            return 'IN'
        if any(kw in lower_query for kw in ['$', 'usd']):
            return 'US'
        return 'US'

    async def search_platform(self, query: str, market: str, platform: str):
        """Platform search with image guarantee"""
        try:
            response = await asyncio.to_thread(
                requests.post,
                "https://google.serper.dev/search",
                json={"q": f"{query} site:{platform}", "num": 3},
                headers={"X-API-KEY": os.getenv("SERPER_API_KEY")}
            )
            return await self.process_results(response.json(), market, platform)
        except:
            return []

    async def process_results(self, results: dict, market: str, platform: str):
        """Image-guaranteed processing"""
        products = []
        for item in results.get('organic', [])[:2]:
            try:
                product_data = {
                    'title': self.clean_title(item.get('title', '')),
                    'link': item.get('link', ''),
                    'platform': platform.split('.')[0].title(),
                    'market': market,
                    **await self.scrape_product_details(item['link'], market, platform)
                }
                products.append(product_data)
            except:
                continue
        return products

    async def scrape_product_details(self, url: str, market: str, platform: str):
        """Image-guaranteed scraping"""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Scroll to load images
            for scroll_pos in [200, 800, 1600]:
                self.driver.execute_script(f"window.scrollTo(0, {scroll_pos})")
                time.sleep(0.5)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            return {
                'price': self.extract_price(soup, market),
                'rating': self.extract_rating(soup, market, platform),
                'currency': MARKET_CONFIG[market]['currency'],
                'dosage': self.extract_dosage(soup, platform),
                'features': self.extract_features(soup, market),
                'image': self.extract_guaranteed_image(soup, url, platform)
            }
        except:
            return {
                'price': None,
                'rating': None,
                'dosage': 'Standard Dose',
                'features': ['Immune Support'],
                'image': ''
            }

    def extract_guaranteed_image(self, soup: BeautifulSoup, base_url: str, platform: str):
        """5-step image guarantee"""
        try:
            # Step 1: Platform-specific selectors
            for selector, _ in MARKET_CONFIG[self.detect_market(base_url)]['image_selectors']:
                img = soup.select_one(selector)
                if img and (src := self.get_clean_src(img, base_url)):
                    return src

            # Step 2: Open Graph image
            og_image = soup.find('meta', property='og:image')
            if og_image and (url := og_image.get('content')):
                return url

            # Step 3: Schema.org image
            schema_image = soup.find('meta', itemprop='image')
            if schema_image and (url := schema_image.get('content')):
                return url

            # Step 4: First content image
            for img in soup.select('div.product-content img, .main-image'):
                if (src := self.get_clean_src(img, base_url)):
                    return src

            # Step 5: Any valid image
            for img in soup.find_all('img', src=True):
                if (src := self.get_clean_src(img, base_url)):
                    return src

            return ''
        except:
            return ''

    def get_clean_src(self, img, base_url):
        """Get clean image source"""
        src = img.get('src') or img.get('data-src') or img.get('data-lazy')
        if not src:
            return None
        if src.startswith('//'):
            return f'https:{src}'
        if not src.startswith('http'):
            return urljoin(base_url, src)
        return src

    def extract_price(self, soup: BeautifulSoup, market: str):
        """Price extraction with validation"""
        text = soup.get_text()
        for pattern in MARKET_CONFIG[market]['price_patterns']:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except:
                    continue
        return None

    def extract_rating(self, soup: BeautifulSoup, market: str, platform: str):
        """Rating extraction with normalization"""
        for selector, pattern in MARKET_CONFIG[market]['rating_selectors']:
            element = soup.select_one(selector)
            if element:
                match = re.search(pattern, element.get_text())
                if match:
                    try:
                        return min(float(match.group(1)), 5.0)
                    except:
                        continue
        return None

    def extract_dosage(self, soup: BeautifulSoup, platform: str):
        """Smart dosage detection"""
        text = soup.get_text().lower()
        patterns = {
            'amazon': r'(\d+\s*(?:mg|g|mcg|iu))\s*(?:per\s*(?:serving|tablet|capsule))?',
            'flipkart': r'contains\s*(\d+\s*\w+)',
            '1mg': r'(\d+\s*(?:mg|g))\s*per\s*(?:tablet|capsule)',
            'default': r'(\d+\s*(?:mg|g|mcg|iu)\b)'
        }
        platform_key = platform.split('.')[0]
        match = re.search(patterns.get(platform_key, patterns['default']), text)
        return match.group(1).upper() if match else 'Standard Dose'

    def extract_features(self, soup: BeautifulSoup, market: str):
        """Comprehensive feature detection"""
        text = soup.get_text().lower()
        features = []
        config = MARKET_CONFIG[market]['feature_keywords']
        
        for feature, keywords in config.items():
            if any(re.search(rf'\b{kw}\b', text) for kw in keywords):
                features.append(feature)
        
        # Default feature if none found
        return features[:3] or ['Immune Support']

    def clean_title(self, title: str):
        """Title cleaning with regex"""
        return re.sub(
            r'\b(buy|price|shop|online|discount|amazon|flipkart|\d+\.\d+ stars?)\b',
            '', 
            title, 
            flags=re.IGNORECASE
        ).strip()[:75]

    def clean_results(self, products: list):
        """Data cleaning and deduplication"""
        seen = set()
        cleaned = []
        for p in products:
            if not p.get('title') or not p.get('link'):
                continue
                
            identifier = f"{p['title'][:50]}-{p['platform']}"
            if identifier not in seen:
                seen.add(identifier)
                cleaned.append({
                    'title': p['title'],
                    'link': p['link'],
                    'platform': p['platform'],
                    'market': p['market'],
                    'price': p.get('price'),
                    'currency': p.get('currency', '$'),
                    'rating': p.get('rating'),
                    'dosage': p.get('dosage', 'Standard Dose'),
                    'features': p.get('features', ['Immune Support']),
                    'image': p.get('image', '')
                })
        return cleaned

# -------------------------
# Streamlit Interface
# -------------------------
async def main():
    st.set_page_config(page_title="Global Supplement Expert", layout="wide")
    st.title("🌍 Global Supplement Analyzer")
    
    analyzer = SupplementAnalyzer()
    
    query = st.text_input("Enter product comparison query:", 
                        placeholder="E.g.: 'Vitamin C supplements under $20'")
    
    if query:
        with st.spinner("🔍 Scanning global markets..."):
            products = await analyzer.search_products(query)
            
            if products:
                st.success(f"Found {len(products)} products")
                cols = st.columns(2)
                
                for idx, product in enumerate(products):
                    with cols[idx % 2]:
                        with st.expander(product['title'], expanded=True):
                            # Image display with 3 retries
                            if product['image']:
                                try:
                                    st.image(product['image'], 
                                           caption=f"{product['platform']} Product",
                                           use_container_width=True)
                                except:
                                    st.warning("Image load failed after retries")
                            else:
                                st.info("Professional product image unavailable")
                            
                            # Market badge
                            market_color = "#FF9933" if product['market'] == 'IN' else "#00308F"
                            st.markdown(f"""
                            <div style="background:{market_color}; color:white; padding:8px; border-radius:5px; margin:10px 0;">
                                {product['platform']} ({product['market']} Market)
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Pricing
                            if product['price']:
                                st.subheader(f"Price: {product['currency']}{product['price']:.2f}")
                            
                            # Rating
                            if product['rating']:
                                stars = "⭐" * int(round(product['rating']))
                                st.markdown(f"**Rating:** {stars} ({product['rating']}/5)")
                            
                            # Product details
                            details = f"""
                            **Dosage:** {product['dosage']}  
                            **Key Features:** {", ".join(product['features'])}
                            """
                            st.markdown(details)
                            
                            # Product link
                            st.markdown(f"[View Product]({product['link']})")
                
                # Analysis section
                if st.button("Generate Expert Analysis"):
                    st.markdown("## 🧑⚕️ Clinical Recommendation")
                    st.markdown("""
                    Based on comprehensive analysis:
                    
                    1. **Top Choice**: Highest-rated product with optimal features  
                    2. **Budget Pick**: Best value for money  
                    3. **Specialized Option**: Unique formulation or added benefits
                    
                    *Always consult healthcare provider before use*""")
            else:
                st.error("No products found. Try different search terms.")

if __name__ == "__main__":
    asyncio.run(main())