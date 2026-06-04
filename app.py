import streamlit as st
import requests
import json
import os
from datetime import datetime
import random
import time
# ==================== 页面配置 ====================
st.set_page_config(
    page_title="旅游计划智能体 · PC专业版",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 样式美化 ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: bold;
        background: linear-gradient(135deg, #1e3c72, #2b4c7c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.3rem;
        font-weight: 500;
        color: #2c3e50;
        border-left: 4px solid #3498db;
        padding-left: 1rem;
        margin: 1rem 0;
    }
    .card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .stButton > button {
        background: linear-gradient(90deg, #3498db, #2980b9);
        color: white;
        border-radius: 30px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        border: none;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #2980b9, #1f618d);
        transform: scale(1.02);
    }
    div[data-testid="stExpander"] details {
        border-radius: 12px;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== DeepSeek API 调用 ====================
def get_deepseek_api_key():
    """安全读取API密钥，优先从环境变量，其次从streamlit secrets"""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        try:
            key = st.secrets["DEEPSEEK_API_KEY"]
        except:
            pass
    if not key:
        st.error("❌ 未找到 DeepSeek API Key。请设置环境变量 DEEPSEEK_API_KEY")
        st.stop()
    return key

def call_deepseek(prompt, temperature=0.7, max_tokens=2000):
    """调用DeepSeek API生成文本"""
    api_key = get_deepseek_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"⚠️ API调用失败（{response.status_code}）：{response.text}"
    except Exception as e:
        return f"⚠️ 请求异常：{str(e)}"

# ==================== 高德地图  API  调用 ======================
# 读取高德 API Key（从 Streamlit secrets）
def get_amap_key():
    try:
        return st.secrets["AMAP_API_KEY"]
    except:
        st.error("请在 Streamlit Secrets 中配置 AMAP_API_KEY")
        st.stop()
# ==================== 行程规划核心（支持出发地）====================
def generate_travel_plan(origin, destination, days, budget=None):
    """调用AI生成完整行程，包含从出发地到目的地的往返交通建议"""
    budget_text = f"，总预算约{budget}元" if budget else ""
    prompt = f"""你是一位资深旅行规划师。用户将从{origin}出发，前往{destination}游玩{days}天{budget_text}。

请生成一份完整的旅行计划，要求：
1. **往返交通**：推荐从{origin}到{destination}的合理交通方案（飞机/高铁/火车），注明预估时间、费用和班次建议。
2. **当地行程**：按天输出{destination}的详细行程，每天包含时间轴（从9:00到20:00）。
3. **景点细节**：每个景点注明建议游览时长和当地交通方式（点对点）。
4. **餐饮推荐**：推荐午餐和晚餐的特色餐厅。
5. **时间合理性**：考虑景点开放时间和地理位置，避免行程过赶。
6. **预算统计**：最后给出总预算估算（往返交通 + 当地门票 + 餐饮 + 住宿）。

输出格式使用Markdown，清晰易读。"""
    return call_deepseek(prompt)

# ==================== 模拟数据（实际可对接真实API）====================
def search_attractions(query, rating_filter="不限", distance_filter="不限"):
    """模拟景点搜索（可替换为真实数据源）"""
    all_spots = [
        {"name": "故宫博物院", "rating": 4.8, "distance": "2.3km", "intro": "明清两代皇家宫殿，世界五大宫之首", "open_time": "8:30-17:00", "ticket": "60元", "location": "北京"},
        {"name": "颐和园", "rating": 4.7, "distance": "5.1km", "intro": "皇家园林博物馆，山水画卷", "open_time": "6:30-20:00", "ticket": "30元", "location": "北京"},
        {"name": "天坛公园", "rating": 4.6, "distance": "3.2km", "intro": "古代祭天建筑群，祈年殿标志性", "open_time": "8:00-17:30", "ticket": "15元", "location": "北京"},
        {"name": "西湖", "rating": 4.9, "distance": "1.0km", "intro": "免费开放，十景闻名", "open_time": "全天", "ticket": "免费", "location": "杭州"},
        {"name": "外滩", "rating": 4.7, "distance": "0.8km", "intro": "万国建筑博览群，夜景璀璨", "open_time": "全天", "ticket": "免费", "location": "上海"},
        {"name": "成都大熊猫基地", "rating": 4.9, "distance": "12km", "intro": "看国宝的最佳去处", "open_time": "7:30-18:00", "ticket": "55元", "location": "成都"}
    ]
    if query:
        all_spots = [s for s in all_spots if query.lower() in s['name'].lower() or query.lower() in s['location'].lower()]
    if rating_filter == "4.5+":
        all_spots = [s for s in all_spots if s['rating'] >= 4.5]
    elif rating_filter == "4.0+":
        all_spots = [s for s in all_spots if s['rating'] >= 4.0]
    if distance_filter == "≤1km":
        all_spots = [s for s in all_spots if float(s['distance'].rstrip('km')) <= 1]
    elif distance_filter == "≤5km":
        all_spots = [s for s in all_spots if float(s['distance'].rstrip('km')) <= 5]
    return all_spots


def search_foods(city, cuisine="不限"):
    """
    使用高德地图 Web 服务 API 搜索真实餐厅
    """
    key = get_amap_key()
    if not key:
        return []
    
    # 1. 地理编码：城市名 → 经纬度
    geocode_url = "https://restapi.amap.com/v3/geocode/geo"
    geo_params = {
        "key": key,
        "address": city,
        "output": "JSON"
    }
    try:
        geo_resp = requests.get(geocode_url, params=geo_params, timeout=10)
        geo_data = geo_resp.json()
        if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
            st.warning(f"地理编码失败：{geo_data.get('info', '未知错误')}")
            return []
        
        location = geo_data["geocodes"][0]["location"]  # 格式 "经度,纬度"
        longitude, latitude = location.split(",")
        
        # 2. 周边搜索：关键词为美食或指定菜系
        keywords = cuisine if cuisine != "不限" else "美食"
        around_url = "https://restapi.amap.com/v3/place/around"
        around_params = {
            "key": key,
            "location": f"{longitude},{latitude}",
            "keywords": keywords,
            "types": "050000",          # 餐饮类别代码
            "radius": 5000,             # 半径5公里
            "offset": 20,               # 返回20条
            "page": 1,
            "extensions": "all",
            "output": "JSON"
        }
        resp = requests.get(around_url, params=around_params, timeout=10)
        data = resp.json()
        
        if data.get("status") == "1" and data.get("pois"):
            foods = []
            for poi in data["pois"][:15]:
                # 提取人均价格（可能没有，默认显示“暂无”）
                price = poi.get("biz_ext", {}).get("cost")
                price_str = f"{price}元/人" if price else "暂无"
                foods.append({
                    "name": poi["name"],
                    "rating": float(poi.get("biz_ext", {}).get("rating", 4.0)),
                    "price": price_str,
                    "cuisine": cuisine if cuisine != "不限" else keywords,
                    "address": poi.get("address", ""),
                    "specialty": poi.get("type", "").split(';')[-1] if poi.get("type") else "热门餐厅"
                })
            return foods
        else:
            st.warning(f"未找到相关美食，请尝试其他关键词或城市。API响应：{data.get('info')}")
            return []
    except Exception as e:
        st.error(f"美食搜索异常：{str(e)}")
        return []

def get_weather(city):
    """
    使用高德天气查询 API 获取实时天气
    """
    # 从 Streamlit secrets 读取高德 Key
    try:
        key = st.secrets["AMAP_API_KEY"]
    except:
        st.error("请在 Streamlit Secrets 中配置 AMAP_API_KEY")
        return None

    if not city:
        return None

    weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {
        "key": key,
        "city": city,
        "extensions": "base"   # base 返回实时天气
    }
    try:
        resp = requests.get(weather_url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "1" and data.get("lives"):
            live = data["lives"][0]
            temp = float(live["temperature"])
            condition = live["weather"]
            humidity = live["humidity"]
            wind = live["windpower"]
            # 生成穿衣建议
            if temp > 28:
                dress = "天气炎热，建议穿短袖、短裤，注意防晒。"
            elif temp > 20:
                dress = "天气温暖，适合穿短袖、薄外套。"
            elif temp > 10:
                dress = "天气凉爽，建议加一件外套。"
            else:
                dress = "天气寒冷，请注意保暖，穿羽绒服。"
            # 返回字典中包含 'dress' 键，与前端显示保持一致
            return {
                "temp": temp,
                "condition": condition,
                "humidity": humidity,
                "wind": f"{wind}级",
                "dress": dress,          # 注意这里是 'dress'
                "alert": None
            }
        else:
            st.warning(f"天气查询失败：{data.get('info', '未知错误')}")
            return None
    except Exception as e:
        st.error(f"天气查询异常：{str(e)}")
        return None
        
def calculate_budget(days, persons, level):
    level_rates = {
        "经济型": {"住宿": 200, "餐饮": 80, "交通": 50, "门票": 60},
        "舒适型": {"住宿": 400, "餐饮": 150, "交通": 100, "门票": 100},
        "豪华型": {"住宿": 900, "餐饮": 350, "交通": 200, "门票": 200}
    }
    rates = level_rates.get(level, level_rates["舒适型"])
    # 住宿按房间（假设2人一间）
    rooms = (persons + 1) // 2
    details = {
        "住宿": rates["住宿"] * days * rooms,
        "餐饮": rates["餐饮"] * days * persons,
        "交通": rates["交通"] * days * persons,
        "门票": rates["门票"] * days * persons
    }
    total = sum(details.values())
    return {"total": total, "details": details}


def get_driving_route(origin, destination, city=None):
    """
    调用高德驾车路径规划 API，返回路线信息
    """
    try:
        key = st.secrets["AMAP_API_KEY"]
    except:
        st.error("高德 API Key 未配置")
        return []

    # 地理编码：出发地和目的地转坐标
    def geocode(address):
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {"key": key, "address": address, "output": "JSON"}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "1" and data.get("geocodes"):
            return data["geocodes"][0]["location"]
        return None

    origin_loc = geocode(origin)
    dest_loc = geocode(destination)
    if not origin_loc or not dest_loc:
        st.warning("无法解析出发地或目的地坐标")
        return []

    # 驾车路径规划
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "key": key,
        "origin": origin_loc,
        "destination": dest_loc,
        "extensions": "all",
        "output": "JSON"
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "1" and data.get("route", {}).get("paths"):
            path = data["route"]["paths"][0]
            duration = int(path["duration"]) // 60  # 分钟
            distance = float(path["distance"]) / 1000  # 公里
            toll = float(path.get("tolls", 0))
            segments = path.get("steps", [])
            # 提取路况（拥堵、缓行等）
            traffic_info = "路线中可能经过拥堵路段，具体请查看导航"
            return [{
                "type": "驾车",
                "duration": f"{duration}分钟",
                "price": f"{toll:.0f}元（过路费）",
                "detail": f"全程{distance:.1f}公里，约{duration}分钟，{traffic_info}"
            }]
        else:
            st.warning("未找到驾车路线，请检查城市间是否有道路连接")
            return []
    except Exception as e:
        st.error(f"路线规划失败：{e}")
        return []
        

def get_traffic_condition(city):
    """
    基于高德交通态势 API，获取城市中心区域的实时路况
    注意：需要将 Streamlit Cloud 的出口 IP 添加到高德控制台 IP 白名单
    """
    try:
        key = st.secrets["AMAP_API_KEY"]
    except:
        st.error("高德 API Key 未配置")
        return "路况服务不可用"

    # 先获取城市中心坐标（以“城市+市政府”为例）
    geocode_url = "https://restapi.amap.com/v3/geocode/geo"
    geo_params = {"key": key, "address": f"{city}市政府", "output": "JSON"}
    try:
        geo_resp = requests.get(geocode_url, params=geo_params, timeout=10)
        geo_data = geo_resp.json()
        if not geo_data.get("geocodes"):
            return f"无法定位城市 {city}"
        location = geo_data["geocodes"][0]["location"]
        lon, lat = location.split(",")
        # 构造矩形区域（方圆3公里）
        delta = 0.03  # 约3km
        rectangle = f"{float(lon)-delta},{float(lat)-delta};{float(lon)+delta},{float(lat)+delta}"
        # 调用交通态势 API
        traffic_url = "https://restapi.amap.com/v3/traffic/status/rectangle"
        params = {
            "key": key,
            "rectangle": rectangle,
            "output": "JSON"
        }
        resp = requests.get(traffic_url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "1" and data.get("trafficinfo"):
            # 解析拥堵指数
            description = data["trafficinfo"]["description"]
            return description
        else:
            return f"无法获取实时路况：{data.get('info', '未知错误')}"
    except Exception as e:
        return f"路况查询异常：{e}"


def get_transport(origin, dest, mode="intercity"):
    if mode == "intercity":
        # 城际交通：优先显示驾车方案（也可再调用公交 API）
        routes = get_driving_route(origin, dest)
        if not routes:
            # 降级模拟数据（提醒用户）
            return [{
                "type": "暂无可规划路线",
                "duration": "未知",
                "price": "未知",
                "detail": "请检查出发地/目的地是否正确，或尝试其他交通方式"
            }]
        return routes
    else:
        # 市内交通：同样使用驾车路径规划（也可选择公交/步行）
        return get_driving_route(origin, dest)
   

def get_realtime(info_type):
    if info_type == "交通路况":
        # 假设用户已选择城市（可以从前端传入，这里简单固定为“成都”示例）
        city = st.session_state.get("traffic_city", "成都")
        return get_traffic_condition(city)
    elif info_type == "景区人流":
        # 景区人流需要景区提供接口，暂返回模拟数据
        return "当前景区人流数据暂未接入，建议出发前查询景区官网。"
    elif info_type == "官方公告":
        # 可从旅游官网 RSS 或官方 API 获取，此处返回模拟提示
        return "暂无最新官方公告，建议关注目的地文旅局公众号。"
    else:
        return "暂无数据"

# ==================== PC端主界面 ====================
def main():
    # 顶部标题
    st.markdown('<div class="main-header">✈️ 旅游计划智能体 · PC专业版</div>', unsafe_allow_html=True)
    st.caption("AI智能行程规划")

    # 侧边栏功能菜单
    with st.sidebar:
        st.markdown("### 🧭 导航")
        menu = st.radio(
            "选择功能",
            ["📅 行程规划", "🏞️ 景点查询", "🍜 美食推荐", "☀️ 天气查询", "💰 预算计算", "🚗 交通路线", "📢 实时信息"],
            label_visibility="collapsed"
        )
        st.markdown("---")
        st.caption("💡 提示：行程规划使用真实AI生成，其余功能为演示数据")
        if menu == "📅 行程规划":
            st.info("点击下方按钮后，AI将为您量身定制每日行程")

    # 主要内容区域
    if menu == "📅 行程规划":
        st.markdown('<div class="sub-header">🎯 一键生成智能行程</div>', unsafe_allow_html=True)
        
        # 三列布局：出发地、目的地、天数（紧凑显示）
        col1, col2, col3 = st.columns(3)
        with col1:
            origin = st.text_input("🚀 出发地", placeholder="例如：上海、广州...", key="origin")
        with col2:
            destination = st.text_input("🏙️ 目的地", placeholder="例如：北京、成都、东京...", key="dest")
        with col3:
            days = st.number_input("📆 游玩天数", min_value=1, max_value=14, value=3, step=1)
        
        # 预算和高级选项放在单独一行
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            budget = st.number_input("💰 总预算（可选，单位：元）", min_value=0, value=3000, step=500)
        with col_b2:
            with st.expander("⚙️ 高级选项"):
                ai_temp = st.slider("AI创造性 (越高越灵活)", 0.0, 1.0, 0.7)
        
        if st.button("✨ 一键生成行程", use_container_width=True):
            if not origin or not destination:
                st.error("请填写出发地和目的地")
            else:
                with st.spinner("AI正在为您规划最完美的路线，请稍候..."):
                    plan = generate_travel_plan(origin, destination, days, budget if budget > 0 else None)
                    st.session_state["generated_plan"] = plan
        if "generated_plan" in st.session_state:
            st.markdown("---")
            st.markdown("### 📌 生成的行程计划")
            st.markdown(st.session_state["generated_plan"])
            # 手动调整区域
            st.markdown("---")
            st.markdown("### ✏️ 手动调整行程")
            edited_plan = st.text_area("您可以修改上述行程内容，然后让AI重新优化剩余部分", 
                                       value=st.session_state["generated_plan"], height=300)
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("🔄 重新优化", use_container_width=True):
                    with st.spinner("AI根据您的修改意见重新优化中..."):
                        # 重新优化时保留出发地和目的地信息
                        new_prompt = f"请根据以下用户自定义的旅行计划草稿（出发地：{origin}，目的地：{destination}，天数：{days}天），优化并完善成一个合理的每日行程，包含往返交通建议，保持格式清晰:\n{edited_plan}"
                        new_plan = call_deepseek(new_prompt)
                        st.session_state["generated_plan"] = new_plan
                        st.rerun()
            with col_b:
                if st.button("💾 保存为文本", use_container_width=True):
                    st.download_button("点击下载行程.txt", edited_plan, file_name=f"{destination}_行程.txt", mime="text/plain")
            with col_c:
                if st.button("🗑️ 清空", use_container_width=True):
                    del st.session_state["generated_plan"]
                    st.rerun()

    elif menu == "🏞️ 景点查询":
        st.markdown('<div class="sub-header">🏛️ 景点搜索与筛选</div>', unsafe_allow_html=True)
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            query = st.text_input("🔍 输入景点名称或城市", placeholder="如：故宫、杭州...")
        with col_s2:
            rating_filter = st.selectbox("⭐ 评分筛选", ["不限", "4.5+", "4.0+"])
        distance_filter = st.selectbox("📏 距离筛选", ["不限", "≤1km", "≤5km"])
        if st.button("搜索景点", use_container_width=True):
            results = search_attractions(query, rating_filter, distance_filter)
            if not results:
                st.warning("未找到相关景点")
            else:
                for spot in results:
                    with st.expander(f"🏯 {spot['name']}  ⭐ {spot['rating']}  |  📍 {spot['distance']}"):
                        st.markdown(f"**简介**: {spot['intro']}")
                        st.markdown(f"**开放时间**: {spot['open_time']}  |  **门票**: {spot['ticket']}")
                        col_btn, _ = st.columns([1, 4])
                        with col_btn:
                            if st.button("➕ 加入行程草稿", key=f"add_{spot['name']}"):
                                st.info(f"已将 {spot['name']} 加入待选（可在行程规划中手动添加）")

    elif menu == "🍜 美食推荐":
        st.markdown('<div class="sub-header">🍽️ 地道美食探索</div>', unsafe_allow_html=True)
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            city_food = st.text_input("📍 城市/区域", placeholder="北京、成都...")
        with col_f2:
            cuisine = st.selectbox("🍲 菜系", ["不限", "北京菜", "川菜", "杭帮菜", "火锅"])
        if st.button("推荐餐厅", use_container_width=True):
            foods = search_foods(city_food, cuisine)
            if not foods:
                st.warning("暂未找到相关美食")
            else:
                for f in foods:
                    st.markdown(f"### {f['name']}  ⭐ {f['rating']}")
                    st.markdown(f"**人均**: {f['price']}  |  **菜系**: {f['cuisine']}")
                    st.markdown(f"**地址**: {f['address']}  |  **特色**: {f['specialty']}")
                    st.divider()

    elif menu == "☀️ 天气查询":
        st.markdown('<div class="sub-header">🌤️ 实时天气与出行建议</div>', unsafe_allow_html=True)
        city_weather = st.text_input("🌆 城市名称", placeholder="输入城市，如：北京")
        if st.button("查询天气", use_container_width=True):
            if not city_weather:
                st.error("请输入城市")
            else:
                weather = get_weather(city_weather)
                if weather:
                    col_w1, col_w2, col_w3 = st.columns(3)
                    col_w1.metric("🌡️ 温度", f"{weather['temp']}°C")
                    col_w2.metric("💧 湿度", f"{weather['humidity']}%")
                    col_w3.metric("💨 风力", weather['wind'])
                    st.markdown(f"**天气状况**: {weather['condition']}")
                    st.info(f"👕 **穿衣建议**: {weather['dress']}")
                else:
                    st.error("未获取到天气信息")

    elif menu == "💰 预算计算":
        st.markdown('<div class="sub-header">💰 智能预算估算器</div>', unsafe_allow_html=True)
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            days_b = st.number_input("天数", 1, 14, 3)
        with col_b2:
            persons = st.number_input("人数", 1, 10, 2)
        with col_b3:
            level = st.selectbox("消费档次", ["经济型", "舒适型", "豪华型"])
        if st.button("开始估算", use_container_width=True):
            budget_result = calculate_budget(days_b, persons, level)
            st.markdown("#### 📊 费用明细")
            for k, v in budget_result['details'].items():
                st.write(f"- {k}: ¥{v:,.0f}")
            st.success(f"**总计预算：¥{budget_result['total']:,.0f}**")
            st.caption("注：住宿按2人一间估算，交通含当地交通，门票为主要景点均价")

elif menu == "🚗 交通路线":
    st.markdown('<div class="sub-header">🚄 实时交通方案</div>', unsafe_allow_html=True)
    trans_type = st.radio("交通类型", ["城际交通", "市内交通"], horizontal=True)
    if trans_type == "城际交通":
        col1, col2 = st.columns(2)
        with col1:
            origin = st.text_input("出发城市", "上海")
        with col2:
            dest = st.text_input("到达城市", "北京")
        if st.button("查询实时路线"):
            with st.spinner("正在规划路线..."):
                routes = get_transport(origin, dest, "intercity")
                for r in routes:
                    st.markdown(f"**{r['type']}** | 耗时 {r['duration']} | 费用 {r['price']}")
                    st.caption(r['detail'])
                    st.divider()
    else:
        col1, col2 = st.columns(2)
        with col1:
            start = st.text_input("起点（精确到地点）", "天安门")
        with col2:
            end = st.text_input("终点", "颐和园")
        if st.button("查询市内路线"):
            with st.spinner("正在规划..."):
                routes = get_transport(start, end, "city")
                for r in routes:
                    st.markdown(f"**{r['type']}** | 耗时 {r['duration']} | {r['detail']}")
        else:
            col_s, col_e = st.columns(2)
            with col_s:
                start = st.text_input("起点", "天安门")
            with col_e:
                end = st.text_input("终点", "颐和园")
            if st.button("查询市内路线"):
                options = get_transport(start, end, "city")
                for opt in options:
                    st.write(f"🚌 {opt['type']}：约 {opt['duration']}，费用 ¥{opt['price']}，{opt['detail']}")

elif menu == "📢 实时信息":
    st.markdown('<div class="sub-header">📡 出行实时动态</div>', unsafe_allow_html=True)
    info_city = st.text_input("城市（用于路况查询）", "成都", key="traffic_city")
    info_type = st.selectbox("信息类别", ["交通路况", "景区人流", "官方公告"])
    if st.button("获取最新信息"):
        info = get_realtime(info_type)
        st.info(f"📢 {info}")

if __name__ == "__main__":
    main()
