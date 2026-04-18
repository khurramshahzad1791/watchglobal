import streamlit as st
import requests
import re
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ipytv import playlist

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
st.set_page_config(page_title="Global FAST Stream Hub", page_icon="🌍", layout="wide")

# Custom CSS for a better visual experience
st.markdown("""
<style>
    .main { padding: 0rem 1rem; }
    .movie-card:hover { transform: scale(1.02); transition: transform 0.2s; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-radius: 10px; }
    h2 { margin-top: 1rem; margin-bottom: 1rem; }
    hr { margin-top: 1rem; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

st.title("🌍 Global FAST Stream Hub")
st.caption("Your passport to free, ad-supported movies & live TV from around the world. Find where to watch anything, instantly.")

# -------------------------------
# RAPIDAPI SETUP (Streaming Availability API)
# -------------------------------
RAPIDAPI_KEY = st.secrets.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "streaming-availability.p.rapidapi.com"

if not RAPIDAPI_KEY:
    st.error("⚠️ Missing RapidAPI key. Please add it to your Streamlit secrets (RAPIDAPI_KEY).")
    st.stop()

# -------------------------------
# USER CONFIGURATION
# -------------------------------
# Country codes for filtering
countries = {
    "United States": "us",
    "United Kingdom": "gb",
    "Canada": "ca",
    "Australia": "au",
    "Germany": "de",
    "France": "fr",
    "India": "in",
    "Pakistan": "pk",
    "China": "cn",
    "Russia": "ru",
    "Philippines": "ph",
    "South Korea": "kr",
    "Japan": "jp",
    "Turkey": "tr",
    "UAE": "ae",
    "Saudi Arabia": "sa",
    "Vietnam": "vn",
    "Thailand": "th",
    "Indonesia": "id",
    "Malaysia": "my"
}
selected_country = st.sidebar.selectbox("🌍 Select your country", list(countries.keys()), index=0)
country_code = countries[selected_country]

# -------------------------------
# COUNTRY-SPECIFIC M3U PLAYLISTS
# -------------------------------
COUNTRY_PLAYLISTS = {
    "India": "https://raw.githubusercontent.com/freearhey/iptv/master/channels/in.m3u",
    "Indonesia": "https://raw.githubusercontent.com/freearhey/iptv/master/channels/id.m3u",
    "China": "https://raw.githubusercontent.com/best-fan/iptv-sources/master/cn_all.m3u8",
    "Russia": "https://raw.githubusercontent.com/CrocoUser/zabava-project/refs/heads/main/zabava-ef.m3u",
    "Germany": "https://raw.githubusercontent.com/josxha/german-tv-m3u/main/german-tv.m3u",
    "Turkey": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "Pakistan": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "South Korea": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "Japan": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "Philippines": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "Vietnam": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "Thailand": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "Malaysia": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "UAE": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "Saudi Arabia": "https://iptv-org.github.io/iptv/index.m3u",  # Use global index, filter by language later
    "Default": "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_us.m3u"
}

# -------------------------------
# FREE STREAMING SERVICES (On-Demand)
# -------------------------------
FREE_SERVICES = {
    "Tubi": "https://tubitv.com",
    "Plex": "https://watch.plex.tv",
    "Pluto TV": "https://pluto.tv",
    "Crackle": "https://www.crackle.com",
    "Xumo Play": "https://play.xumo.com",
    "Popcornflix": "https://popcornflix.com",
    "Kanopy": "https://www.kanopy.com",
    "Roku Channel": "https://therokuchannel.roku.com"
}

# -------------------------------
# PERFORMANCE OPTIMIZATIONS
# -------------------------------
# Configure requests session with retries for better reliability
session = requests.Session()
retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

# Cache M3U parsing results (TTL 2 hours)
@st.cache_data(ttl=7200, show_spinner=False)
def fetch_m3u_playlist(url):
    """Fetch and parse M3U playlist for live TV channels with basic validation."""
    try:
        response = session.get(url, timeout=15)
        if response.status_code == 200:
            content = response.text
            channels = []
            lines = content.split('\n')
            current_channel = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('#EXTINF:'):
                    name_match = re.search(r'#EXTINF:-1.*?,(.*?)$', line)
                    if name_match:
                        current_channel['name'] = name_match.group(1).strip()
                    logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                    if logo_match:
                        current_channel['logo'] = logo_match.group(1)
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    if group_match:
                        current_channel['group'] = group_match.group(1)
                    # Extract language if available
                    lang_match = re.search(r'tvg-language="([^"]+)"', line)
                    if lang_match:
                        current_channel['language'] = lang_match.group(1).lower()
                elif line.startswith('http') and current_channel:
                    current_channel['stream_url'] = line
                    # Basic validation: only add if stream URL is not empty
                    if current_channel.get('stream_url') and current_channel.get('name'):
                        channels.append(current_channel.copy())
                    current_channel = {}
            
            # Return all channels, limit to 300 per service for performance
            return channels[:300]
        return []
    except Exception as e:
        st.error(f"Error fetching playlist: {e}")
        return []

def filter_channels_by_country(channels, country_code, selected_country):
    """Filter channels based on country/language keywords."""
    # Define language/country keywords for filtering
    country_keywords = {
        "us": ["us", "usa", "united states", "american", "english"],
        "gb": ["uk", "united kingdom", "british", "english"],
        "ca": ["canada", "canadian", "english", "french"],
        "au": ["australia", "australian", "english"],
        "de": ["germany", "german", "deutsch"],
        "fr": ["france", "french", "français"],
        "in": ["india", "indian", "hindi", "bollywood", "tamil", "telugu"],
        "pk": ["pakistan", "pakistani", "urdu", "geo", "ary", "hum"],
        "cn": ["china", "chinese", "cctv", "mandarin", "cantonese"],
        "ru": ["russia", "russian", "россия", "русский"],
        "ph": ["philippines", "filipino", "tagalog", "abs-cbn", "gma"],
        "kr": ["korea", "korean", "south korea", "한국", "kbs", "mbc", "sbs"],
        "jp": ["japan", "japanese", "nhk", "tokyo", "japanes"],
        "tr": ["turkey", "turkish", "türkiye", "trt", "kral"],
        "ae": ["uae", "united arab emirates", "dubai", "abu dhabi", "arabic"],
        "sa": ["saudi", "saudi arabia", "kacst", "arabic"],
        "vn": ["vietnam", "vietnamese", "viet nam", "vtv", "htv"],
        "th": ["thailand", "thai", "ประเทศไทย", "channel 3", "channel 7"],
        "id": ["indonesia", "indonesian", "indosiar", "sctv", "trans tv"],
        "my": ["malaysia", "malaysian", "malay", "rtm", "astro"]
    }
    
    keywords = country_keywords.get(country_code, [selected_country.lower()])
    filtered = []
    for channel in channels:
        channel_name = channel.get('name', '').lower()
        channel_group = channel.get('group', '').lower()
        channel_lang = channel.get('language', '').lower()
        
        # Check if any keyword matches
        if any(keyword in channel_name or keyword in channel_group or keyword in channel_lang for keyword in keywords):
            filtered.append(channel)
    
    return filtered

# Cache RapidAPI search results (TTL 24 hours)
@st.cache_data(ttl=86400, show_spinner=False)
def search_movies_rapidapi(query, country):
    """Search for movies using Streaming Availability API (RapidAPI) with country parameter."""
    if not RAPIDAPI_KEY:
        return []
    try:
        url = "https://streaming-availability.p.rapidapi.com/search/title"
        querystring = {
            "title": query,
            "country": country,
            "show_type": "movie",
            "output_language": "en"
        }
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        response = session.get(url, headers=headers, params=querystring, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'result' in data:
                return data['result']
            elif isinstance(data, list):
                return data
        return []
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def get_streaming_links(movie_data, service_name):
    """Extract streaming link for a specific service from the API response."""
    if not movie_data or 'streamingInfo' not in movie_data:
        return None
    
    service_map = {
        "tubi": "tubi",
        "plex": "plex",
        "pluto tv": "pluto",
        "crackle": "crackle",
        "xumo play": "xumo",
        "popcornflix": "popcornflix",
        "kanopy": "kanopy",
        "roku channel": "roku"
    }
    
    service_key = service_map.get(service_name.lower())
    if not service_key:
        return None
    
    streaming_info = movie_data.get('streamingInfo', {})
    # Use the user's selected country code
    country_info = streaming_info.get(country_code, {})
    
    if service_key in country_info:
        return country_info[service_key].get('link')
    return None

# -------------------------------
# MAIN UI - TABBED LAYOUT
# -------------------------------
# Use tabs to organize content
tab_live, tab_movies, tab_search = st.tabs(["📡 Live TV", "🎬 Free Movies", "🔍 Search"])

# ===================== TAB 1: LIVE TV =====================
with tab_live:
    st.subheader(f"📡 Live TV Channels - {selected_country}")
    st.caption(f"Watch live channels from around the world, filtered for {selected_country}. Click any channel to start streaming.")
    
    # Get playlist URL for selected country
    playlist_url = COUNTRY_PLAYLISTS.get(selected_country, COUNTRY_PLAYLISTS["Default"])
    
    # Add a refresh button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Refresh Channels", key="refresh_live"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        with st.spinner(f"Loading channels for {selected_country}..."):
            all_channels = fetch_m3u_playlist(playlist_url)
            # Filter channels by country
            channels = filter_channels_by_country(all_channels, country_code, selected_country)
    
    if channels:
        st.success(f"✅ Found {len(channels)} channels for {selected_country}")
        # Display channels in a responsive grid with 4 columns
        cols_per_row = 4
        for i in range(0, min(len(channels), 100), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx < len(channels):
                    channel = channels[idx]
                    with col:
                        with st.container():
                            # Use expander for channel details to save space
                            with st.expander(f"📺 {channel.get('name', 'Unknown')[:50]}", expanded=False):
                                if channel.get('logo'):
                                    st.image(channel['logo'], width=100)
                                if channel.get('group'):
                                    st.caption(f"📁 {channel['group']}")
                                if channel.get('language'):
                                    st.caption(f"🔤 Language: {channel['language']}")
                                stream_url = channel.get('stream_url', '#')
                                # Use st.link_button for better UX
                                st.link_button("▶️ Watch Now", stream_url, use_container_width=True)
    else:
        st.info(f"No channels found for {selected_country}. Try selecting a different country or use the global playlist below.")
        
        # Fallback: Show global playlist
        with st.expander("🌐 Show global channels (all countries)"):
            global_channels = fetch_m3u_playlist(COUNTRY_PLAYLISTS["Default"])
            if global_channels:
                cols_per_row = 4
                for i in range(0, min(len(global_channels), 100), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx < len(global_channels):
                            channel = global_channels[idx]
                            with col:
                                with st.container():
                                    with st.expander(f"📺 {channel.get('name', 'Unknown')[:50]}", expanded=False):
                                        if channel.get('logo'):
                                            st.image(channel['logo'], width=100)
                                        stream_url = channel.get('stream_url', '#')
                                        st.link_button("▶️ Watch Now", stream_url, use_container_width=True)

# ===================== TAB 2: FREE MOVIES =====================
with tab_movies:
    st.subheader("🎬 Browse Free Streaming Services")
    st.caption("Click any service to start watching thousands of free movies and shows.")
    
    # Display services as a grid of buttons
    service_names = list(FREE_SERVICES.keys())
    cols = st.columns(4)
    for idx, service in enumerate(service_names):
        with cols[idx % 4]:
            st.markdown(f"### {service}")
            st.link_button(f"Open {service} →", FREE_SERVICES[service], use_container_width=True)
            st.caption("Free, ad-supported")
    
    st.divider()
    st.markdown("**Tip:** Use the **Search** tab to find specific movies and get direct watch links based on your country.")

# ===================== TAB 3: SEARCH =====================
with tab_search:
    st.subheader("🔍 Search Movies & TV Shows")
    st.caption(f"Find where to watch any movie for free in **{selected_country}**. Results include direct links to Tubi, Plex, Pluto, and more.")
    
    # Search input with placeholder
    search_query = st.text_input("Enter movie title", placeholder="e.g., The Matrix, Inception, Parasite...")
    
    if search_query:
        # Show a spinner while searching
        with st.spinner(f"Searching for '{search_query}' in {selected_country}..."):
            results = search_movies_rapidapi(search_query, country_code)
        
        if results and len(results) > 0:
            st.success(f"✨ Found {len(results)} results for '{search_query}'")
            
            # Display results in a grid of cards (4 per row)
            for idx, movie in enumerate(results[:20]):  # Limit to 20 for performance
                title = movie.get('title', 'Unknown')
                year = movie.get('year', 'N/A')
                imdb_rating = movie.get('imdbRating', 'N/A')
                overview = movie.get('overview', 'No description available.')
                poster = movie.get('posterPath', '')
                poster_url = f"https://image.tmdb.org/t/p/w500{poster}" if poster else None
                
                # Create a card-like layout for each movie
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if poster_url:
                            st.image(poster_url, width=150)
                        else:
                            st.image("https://via.placeholder.com/150x225?text=No+Poster", width=150)
                    
                    with col2:
                        st.markdown(f"### {title} ({year})")
                        st.caption(f"⭐ IMDb: {imdb_rating}")
                        # Truncate long overviews
                        short_overview = (overview[:300] + '...') if len(overview) > 300 else overview
                        st.markdown(short_overview)
                        
                        # Find which free services have this movie in the selected country
                        available_services = []
                        for service_name in FREE_SERVICES.keys():
                            link = get_streaming_links(movie, service_name)
                            if link:
                                available_services.append((service_name, link))
                        
                        if available_services:
                            st.markdown("**🍿 Watch for free on:**")
                            # Display service links in a horizontal row
                            link_cols = st.columns(min(len(available_services), 4))
                            for i, (srv_name, srv_link) in enumerate(available_services[:4]):
                                with link_cols[i % 4]:
                                    st.link_button(srv_name, srv_link, use_container_width=True)
                        else:
                            st.markdown(f"*Not available on free services in {selected_country}. Try changing your country selection in the sidebar.*")
                    st.divider()
        else:
            st.info(f"No movies found for '{search_query}' in {selected_country}. Try a different title or change your country selection.")

# -------------------------------
# FOOTER
# -------------------------------
st.divider()
st.caption(f"Global FAST Stream Hub • Aggregates free ad-supported content from around the world • Updated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
