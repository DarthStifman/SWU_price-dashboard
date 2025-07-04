import requests
from bs4 import BeautifulSoup
import json
import time
import undetected_chromedriver as uc 
from selenium import webdriver
from selenium_stealth import stealth
from fake_useragent import UserAgent
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import re
from datetime import datetime, timedelta
import os
from pathlib import Path


CACHE_FILE = Path("streamlit_session_cache.json")

with open('sources.json', 'r') as f:
        x = json.load(f)

data = x[0]
BUTTON_COOLDOWN = 10

def load_session_cache():
    """Load session state from file"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                return data
        except:
            return {}
    return {}

def save_session_cache(data):
    """Save session state to file"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass  # Ignore write errors

# Load cached state
cached_data = load_session_cache()

# Initialize session state with cached values
if 'last_scrape_time' not in st.session_state:
    st.session_state['last_scrape_time'] = cached_data.get('last_scrape_time', "Never")
    
if 'last_button_click_time' not in st.session_state:
    last_click_str = cached_data.get('last_button_click_time')
    if last_click_str:
        try:
            st.session_state['last_button_click_time'] = datetime.fromisoformat(last_click_str)
        except:
            st.session_state['last_button_click_time'] = None
    else:
        st.session_state['last_button_click_time'] = None
    
    
def setup_chrome():
    options = uc.ChromeOptions()
        
    # Basic options
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    
    # Anti-detection options
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins-discovery')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
       
    return uc.Chrome(options=options)

def get_price(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    price = soup.find('span', {'itemprop': 'price'})['content']
    result = float(price)
    return result

def get_price_jrc(url):    
    user_agent = UserAgent().random
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--log-level=3')
    options.add_argument(f"user-agent={user_agent}")
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("return navigator.language")
    driver.get(url)
    time.sleep(5)
    page_source = driver.page_source
    #print(driver.title)
    driver.quit()
  
    soup = BeautifulSoup(page_source, 'html.parser')
    price_meta = soup.find('meta', {'itemprop': 'price'})
    
    base_price = None
    discount_price = None
    
    if price_meta:
        price_content = price_meta.get('content')
        if price_content:
            try:
                base_price = float(price_content)
            except ValueError:
                print(f"Warning: Could not convert base price '{price_content}' to float.")
                base_price = None

    discount_div = soup.find('div', class_='pushBox black')
    if discount_div:
        b_tag = discount_div.find('b')
        if b_tag and b_tag.string:
            discount_text = b_tag.string.strip()
            match = re.search(r'(\d+)\s*Kč', discount_text)
            if match:
                try:
                    discount_price = float(match.group(1))
                except ValueError:
                    print(f"Warning: Could not convert discount price '{match.group(1)}' to float from text '{discount_text}'.")
            else:
                print(f"Warning: Could not find numerical price pattern in discount text: '{discount_text}'")

    if base_price is not None and discount_price is not None:
        return min(base_price, discount_price)
    elif base_price is not None:
        return base_price
    elif discount_price is not None:
        return discount_price
    else:
        print("No valid price (base or discount) found.")
        return None
   
   

def get_price_najada(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    price = soup.find('div', {'class': 'value font-encodeCond green'}).text
    formated_price = price.replace(" Kč", "").replace(" ", "")
    result = float(formated_price)
    return result

def create_json(list):
    with open('data.json', 'w') as output:
        json.dump(list, output)
    
def scrape_data():    
    collected_data = []
    
    # for store, section in data.items():
    #     #print(20 * '*')
    #     #print(f"Store: {store}")         
    #     #print(20 * '*')       
    #     for category, items in section.items():
    #         #print(f"Category: {category}")             
    #         #print(20 * '_')           
    #         for item in items:   
    #             name = item['Name']             
    #             #print(f"Name: {name}")
    #             if store == "Xzone":  
    #                 if item['URL']:                  
    #                     price = get_price(item['URL'])
    #                     #print(price)    
    #                     new_data = {'store': store, 'category': category, 'product': name, 'price': price}    
    #                     collected_data.append(new_data)               
    #                 else:
    #                     #print("Out of stock")
    #                     new_data = {'store': store, 'category': category, 'product': name, 'price': 'Out of stock'}
    #                     collected_data.append(new_data)
    #             elif store == "Najada":
    #                 if item['URL']:                  
    #                     price = get_price_najada(item['URL'])
    #                     #print(price) 
    #                     new_data = {'store': store, 'category': category, 'product': name, 'price': price}  
    #                     collected_data.append(new_data)                            
    #                 else:
    #                     #print("Out of stock")
    #                     new_data = {'store': store, 'category': category, 'product': name, 'price': 'Out of stock'}
    #                     collected_data.append(new_data)
    #             if store == "JRC":
    #                 if item['URL']:                  
    #                     price = get_price_jrc(item['URL'])
    #                     #print(price) 
    #                     new_data = {'store': store, 'category': category, 'product': name, 'price': price} 
    #                     collected_data.append(new_data)                     
    #                 else:
    #                     #print("Out of stock")
    #                     new_data = {'store': store, 'category': category, 'product': name, 'price': 'Out of stock'}
    #                     collected_data.append(new_data)
                        
    #             #print(20 * '-')
    # create_json(collected_data)
    st.session_state['last_scrape_time'] = datetime.now().strftime("%H:%M %d.%m.%Y")     
    st.session_state['last_button_click_time'] = datetime.now()
    print('Finished')              

with open('data.json', 'r') as f:
        table_data = json.load(f)
        
def sort_price_out(item):
    price = item["price"]   
    if price == "Out of stock":
        return float('inf')
    return price        
        
def filter_items(data, category):
    filtered_data = [item for item in data if item["category"] == category]           
    sorted_list = sorted(filtered_data, key=sort_price_out)    
    return sorted_list

def filter_stores(data, store):
    filtered_data = [item for item in data if item["store"] == store]           
    sorted_list = sorted(filtered_data, key=sort_price_out)    
    return sorted_list
 
 
##################################################################
##################### Streamlit ################################## 
 
booster_packs = filter_items(table_data, "Booster Packs") 
booster_boxes = filter_items(table_data, "Booster Boxes")
carbonites = filter_items(table_data, "Carbonites")

store_jrc = filter_stores(table_data, "JRC")
store_xzone = filter_stores(table_data, "Xzone")
store_najada = filter_stores(table_data, "Najada")

st.set_page_config(
    layout="wide",
    page_title="SWU Price Dashboard",
    page_icon=":japanese_goblin:"
    )

current_time = datetime.now()
button_disabled = False
remaining_time = 0
cooldown_message = ""

if st.session_state['last_button_click_time']:
    time_diff = (current_time - st.session_state['last_button_click_time']).total_seconds()   
    print("################# DEBUG INFO ###########################")    
    print(f"Time diff: {time_diff}, Cooldown: {BUTTON_COOLDOWN}")
    
    if time_diff < (BUTTON_COOLDOWN - 0.5) :        
        button_disabled = True
        remaining_time = int(BUTTON_COOLDOWN - time_diff)
        available_at_time = st.session_state['last_button_click_time'] + timedelta(seconds=BUTTON_COOLDOWN)
        cooldown_message = f"Next scrape available in {available_at_time.strftime('%H:%M:%S')}."
   
title_col, button_col_wrapper = st.columns([4, 1])

with title_col:
    st.title('Current SWU price overview')

with button_col_wrapper:
    st.write("<br>", unsafe_allow_html=True)
    
    if button_disabled:
        # JavaScript countdown button - file cache will persist
        countdown_html = f"""
        <div id="countdown-container">
            <button id="countdown-btn" 
                    style="
                        background-color: #ff6b6b;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-size: 14px;
                        cursor: not-allowed;
                        opacity: 0.6;
                    "
                    disabled>
                Wait {remaining_time}s
            </button>
        </div>
        
        <script>
        let remainingTime = {remaining_time};
        const button = document.getElementById('countdown-btn');
        
        const countdown = setInterval(() => {{
            remainingTime--;
            button.innerText = `Wait ${{remainingTime}}s`;
            
            // Add a small delay before refresh to ensure server cooldown has expired
            if (remainingTime <= 0) {{
                clearInterval(countdown);
                button.innerText = 'Refreshing...';
                setTimeout(() => {{
                    window.parent.location.reload();
                }}, 500); // 500ms delay to sync with server
            }}
        }}, 1000);
        </script>
        """
        components.html(countdown_html, height=50)
    else:
        # Regular Streamlit button
        if st.button("Get the prices!", type="primary"):
            print("BUTTON HANDLER EXECUTED!")             
            with st.spinner("Working on it..."):
                scrape_data()
                button_click_time = datetime.now()
                st.session_state['last_button_click_time'] = button_click_time
                st.session_state['last_scrape_time'] = button_click_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Save to file cache
                cache_data = {
                    'last_scrape_time': st.session_state['last_scrape_time'],
                    'last_button_click_time': button_click_time.isoformat()
                }
                save_session_cache(cache_data)
                
                st.rerun()

  
st.info(f"**Data last updated:** {st.session_state['last_scrape_time']}{' | ' + cooldown_message if cooldown_message else ''}")
                                      
items, stores = st.columns(2)
with items:    
    st.header("Booster Packs")
    if booster_packs:
        df1 = pd.DataFrame(booster_packs)
        df1['price'] = df1['price'].astype(str)
        st.dataframe(df1, use_container_width=True)
    else:
        st.info("No Booster Packs data yet. Click 'Get the prices!'")

    st.header("Booster Boxes")
    if booster_boxes:
        df2 = pd.DataFrame(booster_boxes)
        df2['price'] = df2['price'].astype(str)
        st.dataframe(df2, use_container_width=True)
    else:
        st.info("No Booster Boxes data yet. Click 'Get the prices!'")

    st.header("Carbonites")
    if carbonites:
        df3 = pd.DataFrame(carbonites)
        df3['price'] = df3['price'].astype(str)
        st.dataframe(df3, use_container_width=True)
    else:
        st.info("No Carbonites data yet. Click 'Get the prices!'")
    
with stores:    
    st.header("JRC")
    if store_jrc:
        df4 = pd.DataFrame(store_jrc)
        df4['price'] = df4['price'].astype(str)
        st.dataframe(df4, use_container_width=True)
    else:
        st.info("No JRC data yet. Click 'Get the prices!'")

    st.header("Xzone")
    if store_xzone:
        df5 = pd.DataFrame(store_xzone)
        df5['price'] = df5['price'].astype(str)
        st.dataframe(df5, use_container_width=True)
    else:
        st.info("No Xzone data yet. Click 'Get the prices!'")

    st.header("Najada")
    if store_najada:
        df6 = pd.DataFrame(store_najada)
        df6['price'] = df6['price'].astype(str)
        st.dataframe(df6, use_container_width=True)
    else:
        st.info("No Najada data yet. Click 'Get the prices!'")