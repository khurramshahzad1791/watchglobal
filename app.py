import streamlit as st
import requests
import re
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
st.set_page_config(page_title="Global FAST Stream Hub", page_icon="🌍", layout="wide")

st.markdown("""
<style>
    .main { padding: 0rem 1rem; }
    .movie-card:hover { transform: scale(1.02); transition: transform 0.2s; }
    hr { margin-top: 1rem; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

st.title("🌍 Global FAST Stream Hub")
st.caption("Your passport to free, ad-supported movies & live TV from around the world.")

# -------------------------------
# RAPIDAPI SETUP
# -------------------------------
RAPIDAPI_KEY = st.secrets.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "streaming-availability.p.rapidapi.com"

if not RAPIDAPI_KEY:
    st.error("⚠️ Missing RapidAPI key. Please add it to your Streamlit secrets (RAPIDAPI_KEY).")
    st.stop()

# -------------------------------
# COUNTRY SELECTION
# -------------------------------
countries = {
    "United States": "us", "United Kingdom": "gb", "Canada": "ca", "Australia": "au",
    "Germany": "de", "France": "fr", "India": "in", "Pakistan": "pk", "China": "cn",
    "Russia": "ru", "Philippines": "ph", "South Korea": "kr", "Japan": "jp",
    "Turkey": "tr", "UAE": "ae", "Saudi Arabia": "sa", "Vietnam": "vn",
    "Thailand": "th", "Indonesia": "id", "Malaysia": "my"
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
    "Russia": "https://raw.githubusercontent.com/CrocoUser/zabava-project/main/zabava-ef.m3u",
    "Germany": "https://raw.githubusercontent.com/josxha/german-tv-m3u/main/german-tv.m3u",
    "Default": "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_us.m3u"
}

# -------------------------------
# FREE STREAMING SERVICES
# -------------------------------
FREE_SERVICES = {
    "Tubi": "https://tubitv.com", "Plex": "https://watch.plex.tv", "Pluto TV": "https://pluto.tv",
    "Crackle": "https://www.crackle.com", "Xumo Play": "https://play.xumo.com",
    "Popcornflix": "https://popcornflix.com", "Kanopy": "https://www.kanopy.com",
    "Roku Channel": "https://therokuchannel.roku.com"
}

# -------------------------------
# SESSION & CACHING
# -------------------------------
session = requests.Session()
retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

@st.cache_data(ttl=7200, show_spinner=False)
def fetch_m3u_playlist(url):
    """Fetch and parse M3U playlist using regex (no external libs)"""
    try:
        response = session.get(url, timeout=15)
        if response.status_code != 200:
            return []
        content = response.text
        channels = []
        lines = content.split('\n')
        current = {}
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                # Extract channel name
                name_match = re.search(r'#EXTINF:-1.*?,(.*?)$', line)
                if name_match:
                    current['name'] = name_match.group(1).strip()
                # Extract logo
                logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                if logo_match:
                    current['logo'] = logo_match.group(1)
                # Extract group
                group_match = re.search(r'group-title="([^"]+)"', line)
                if group_match:
                    current['group'] = group_match.group(1)
                # Extract language
                lang_match = re.search(r'tvg-language="([^"]+)"', line)
                if lang_match:
                    current['language'] = lang_match.group(1)
            elif line.startswith('http') and current:
                current['stream_url'] = line
                if current.get('stream_url') and current.get('name'):
                    channels.append(current.copy())
                current = {}
        return channels[:300]
    except Exception as e:
        st.error(f"Error fetching playlist: {e}")
        return []

def filter_by_country(channels, country_code, country_name):
    """Filter channels by country/language keywords"""
    keywords = {
        "us": ["us","usa","united states","american","english"],
        "gb": ["uk","united kingdom","british","english"],
        "in": ["india","indian","hindi","bollywood","tamil","telugu"],
        "pk": ["pakistan","pakistani","urdu","geo","ary","hum"],
        "cn": ["china","chinese","cctv","mandarin","cantonese"],
        "kr": ["korea","korean","south korea","kbs","mbc","sbs"],
        "jp": ["japan","japanese","nhk","tokyo"],
        "ru": ["russia","russian","россия","русский"],
        "ph": ["philippines","filipino","tagalog","abs-cbn","gma"],
        "tr": ["turkey","turkish","türkiye","trt"],
        "ae": ["uae","dubai","arabic"],
        "sa": ["saudi","arabic"],
        "vn": ["vietnam","vietnamese","vtv"],
        "th": ["thailand","thai"],
        "id": ["indonesia","indonesian"],
        "my": ["malaysia","malaysian","malay"]
    }
    kw = keywords.get(country_code, [country_name.lower()])
    filtered = []
    for ch in channels:
        name = ch.get('name','').lower()
        grp = ch.get('group','').lower()
        lang = ch.get('language','').lower()
        if any(k in name or k in grp or k in lang for k in kw):
            filtered.append(ch)
    return filtered

@st.cache_data(ttl=86400, show_spinner=False)
def search_movies_rapidapi(query, country):
    if not RAPIDAPI_KEY:
        return []
    try:
        url = "https://streaming-availability.p.rapidapi.com/search/title"
        params = {"title": query, "country": country, "show_type": "movie", "output_language": "en"}
        headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST}
        resp = session.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('result', []) if isinstance(data, dict) else data
        return []
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def get_streaming_link(movie_data, service_name):
    if not movie_data or 'streamingInfo' not in movie_data:
        return None
    mapping = {"tubi":"tubi","plex":"plex","pluto tv":"pluto","crackle":"crackle",
               "xumo play":"xumo","popcornflix":"popcornflix","kanopy":"kanopy","roku channel":"roku"}
    key = mapping.get(service_name.lower())
    if not key:
        return None
    info = movie_data.get('streamingInfo', {}).get(country_code, {})
    return info.get(key, {}).get('link')

# -------------------------------
# UI TABS
# -------------------------------
tab_live, tab_movies, tab_search = st.tabs(["📡 Live TV", "🎬 Free Services", "🔍 Search"])

# ========== LIVE TV ==========
with tab_live:
    st.subheader(f"📡 Live TV Channels - {selected_country}")
    playlist_url = COUNTRY_PLAYLISTS.get(selected_country, COUNTRY_PLAYLISTS["Default"])
    if st.button("🔄 Refresh Channels"):
        st.cache_data.clear()
        st.rerun()
    with st.spinner(f"Loading channels for {selected_country}..."):
        all_ch = fetch_m3u_playlist(playlist_url)
        channels = filter_by_country(all_ch, country_code, selected_country) if selected_country not in COUNTRY_PLAYLISTS else all_ch
    if channels:
        st.success(f"✅ {len(channels)} channels found")
        for i in range(0, min(len(channels), 100), 4):
            cols = st.columns(4)
            for j in range(4):
                idx = i+j
                if idx < len(channels):
                    ch = channels[idx]
                    with cols[j]:
                        with st.expander(f"📺 {ch.get('name','')[:50]}", expanded=False):
                            if ch.get('logo'):
                                st.image(ch['logo'], width=100)
                            if ch.get('group'):
                                st.caption(f"📁 {ch['group']}")
                            st.link_button("▶️ Watch", ch.get('stream_url','#'), use_container_width=True)
    else:
        st.info(f"No channels found for {selected_country}. Try another country.")

# ========== FREE SERVICES ==========
with tab_movies:
    st.subheader("🎬 Browse Free Streaming Services")
    cols = st.columns(4)
    for idx, (name, url) in enumerate(FREE_SERVICES.items()):
        with cols[idx % 4]:
            st.markdown(f"### {name}")
            st.link_button(f"Open {name} →", url, use_container_width=True)

# ========== SEARCH ==========
with tab_search:
    st.subheader(f"🔍 Search Movies in {selected_country}")
    query = st.text_input("Enter movie title", placeholder="e.g., The Matrix")
    if query:
        with st.spinner("Searching..."):
            results = search_movies_rapidapi(query, country_code)
        if results:
            for movie in results[:20]:
                title = movie.get('title','Unknown')
                year = movie.get('year','N/A')
                rating = movie.get('imdbRating','N/A')
                overview = movie.get('overview','')[:300]
                poster = movie.get('posterPath','')
                poster_url = f"https://image.tmdb.org/t/p/w500{poster}" if poster else None
                col1, col2 = st.columns([1,3])
                with col1:
                    st.image(poster_url or "https://via.placeholder.com/150x225?text=No+Poster", width=150)
                with col2:
                    st.markdown(f"### {title} ({year})")
                    st.caption(f"⭐ {rating}")
                    st.write(overview)
                    links = [(s, get_streaming_link(movie, s)) for s in FREE_SERVICES if get_streaming_link(movie, s)]
                    if links:
                        st.markdown("**Watch for free on:**")
                        for srv, link in links[:4]:
                            st.link_button(srv, link, use_container_width=True)
                    else:
                        st.caption(f"Not available on free services in {selected_country}.")
                st.divider()
        else:
            st.info("No movies found. Try different title or country.")

st.divider()
st.caption(f"Updated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
