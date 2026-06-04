import streamlit as st
import requests
import json
import os
from datetime import datetime
import random
import time

st.set_page_config(page_title="旅游计划智能体 · PC专业版", page_icon="✈️", layout="wide")

st.markdown("""
<style>
.main-header { font-size: 2.2rem; font-weight: bold; background: linear-gradient(135deg, #1e3c72, #2b4c7c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.sub-header { font-size: 1.3rem; font-weight: 500; color: #2c3e50; border-left: 4px solid #3498db; padding-left: 1rem; margin: 1rem 0; }
.stButton > button { background: linear-gradient(90deg, #3498db, #2980b9); color: white; border-radius: 30px; border: none; }
</style>
""", unsafe_allow_html=True)

# ---------- 密钥读取 ----------
def get_deepseek_key():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        try:
            key = st.secrets["DEEPSEEK_API_KEY"]
        except:
            pass
    if not key:
        st.error("❌ 未找到 DeepSeek API Key，请在 secrets 中设置 DEEPSEEK_API_KEY")
        st.stop()
    return key

def get_amap_key():
    try:
        return st.secrets["AMAP_API_KEY"]
    except:
        st.error("❌ 未找到高德 API Key，请在 secrets 中设置 AMAP_API_KEY")
        st.stop()

# ---------- DeepSeek 调用 ----------
def call_deepseek(prompt):
    api_key = get_deepseek_key()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
    try:
        resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"API错误: {resp.text}"
    except Exception as e:
        return f"请求异常: {e}"

def generate_travel_plan(origin, destination, days, budget=None):
    budget_text = f"，总预算约{budget}元" if budget else ""
    prompt = f"""你是一位资深旅行规划师。用户将从{origin}出发，前往{destination}游玩{days}天{budget_text}。
请生成完整旅行计划，包含：
1. 从{origin}到{destination}的往返交通建议（时间、费用）
2. 每日行程（时间轴9:00-20:00，景点、时长、当地交通）
3. 餐饮推荐
4. 总预算（往返交通+当地门票+餐饮+住宿）
输出Markdown格式。"""
    return call_deepseek(prompt)

# ---------- 高德美食搜索（实时） ----------
def search_foods(city, cuisine="不限"):
    key = get_amap_key()
    if not city:
        return []
    # 地理编码
    geo_url = "https://restapi.amap.com/v3/geocode/geo"
    geo_params = {"key": key, "address": city, "output": "JSON"}
    try:
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_data = geo_resp.json()
        if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
            st.warning(f"无法获取城市 '{city}' 坐标")
            return []
        location = geo_data["geocodes"][0]["location"]
        keywords = cuisine if cuisine != "不限" else "美食"
        around_url = "https://restapi.amap.com/v3/place/around"
        around_params = {
            "key": key, "location": location, "keywords": keywords, "types": "050000",
            "radius": 5000, "offset": 20, "page": 1, "output": "JSON"
        }
        resp = requests.get(around_url, params=around_params, timeout=10)
        data = resp.json()
        if data.get("status") == "1" and data.get("pois"):
            foods = []
            for poi in data["pois"][:15]:
                price = poi.get("biz_ext", {}).get("cost")
                price_str = f"{price}元/人" if price else "暂无"
                rating = float(poi.get("biz_ext", {}).get("rating", 4.0))
                foods.append({
                    "name": poi["name"], "rating": rating, "price": price_str,
                    "cuisine": cuisine if cuisine != "不限" else keywords,
                    "address": poi.get("address", ""),
                    "specialty": poi.get("type", "").split(';')[-1] if poi.get("type") else "热门餐厅"
                })
            return foods
        else:
            st.warning(f"未找到美食：{data.get('info')}")
            return []
    except Exception as e:
        st.error(f"美食搜索异常：{e}")
        return []

# ---------- 高德天气查询（实时） ----------
def get_weather(city):
    key = get_amap_key()
    if not city:
        return None
    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {"key": key, "city": city, "extensions": "base"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "1" and data.get("lives"):
            live = data["lives"][0]
            temp = float(live["temperature"])
            condition = live["weather"]
            humidity = live["humidity"]
            wind = live["windpower"]
            if temp > 28:
                dress = "天气炎热，建议穿短袖、短裤，注意防晒。"
            elif temp > 20:
                dress = "天气温暖，适合穿短袖、薄外套。"
            elif temp > 10:
                dress = "天气凉爽，建议加一件外套。"
            else:
                dress = "天气寒冷，请注意保暖，穿羽绒服。"
            return {
                "temp": temp, "condition": condition, "humidity": humidity,
                "wind": f"{wind}级", "dress": dress, "alert": None
            }
        else:
            st.warning(f"天气查询失败：{data.get('info')}")
            return None
    except Exception as e:
        st.error(f"天气查询异常：{e}")
        return None

# ---------- 实时驾车路线（高德） ----------
def get_driving_route(origin, destination):
    key = get_amap_key()
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
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "key": key, "origin": origin_loc, "destination": dest_loc,
        "extensions": "all", "output": "JSON"
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "1" and data.get("route", {}).get("paths"):
            path = data["route"]["paths"][0]
            duration = int(path["duration"]) // 60
            distance = float(path["distance"]) / 1000
            toll = float(path.get("tolls", 0))
            return [{
                "type": "驾车",
                "duration": f"{duration}分钟",
                "price": f"{toll:.0f}元（过路费）" if toll > 0 else "无过路费",
                "detail": f"全程{distance:.1f}公里，约{duration}分钟"
            }]
        else:
            st.warning("未找到驾车路线")
            return []
    except Exception as e:
        st.error(f"路线规划失败：{e}")
        return []

def get_transport(origin, dest, mode="intercity"):
    if mode == "intercity":
        return get_driving_route(origin, dest)
    else:
        return get_driving_route(origin, dest)

# ---------- 实时路况（高德交通态势，可能需要IP白名单） ----------
def get_traffic_condition(city):
    key = get_amap_key()
    geo_url = "https://restapi.amap.com/v3/geocode/geo"
    geo_params = {"key": key, "address": f"{city}市政府", "output": "JSON"}
    try:
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_data = geo_resp.json()
        if not geo_data.get("geocodes"):
            return f"无法定位城市 {city}"
        location = geo_data["geocodes"][0]["location"]
        lon, lat = location.split(",")
        delta = 0.03
        rectangle = f"{float(lon)-delta},{float(lat)-delta};{float(lon)+delta},{float(lat)+delta}"
        traffic_url = "https://restapi.amap.com/v3/traffic/status/rectangle"
        params = {"key": key, "rectangle": rectangle, "output": "JSON"}
        resp = requests.get(traffic_url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "1" and data.get("trafficinfo"):
            return data["trafficinfo"]["description"]
        else:
            return f"路况信息暂时无法获取：{data.get('info')}"
    except Exception as e:
        return f"路况查询异常：{e}"

def get_realtime(info_type, city="成都"):
    if info_type == "交通路况":
        return get_traffic_condition(city)
    elif info_type == "景区人流":
        return "景区人流数据暂未接入，建议出发前查询景区官网。"
    elif info_type == "官方公告":
        return "暂无最新官方公告，建议关注目的地文旅局公众号。"
    else:
        return "暂无数据"

# ---------- PC端主界面 ----------
def main():
    st.markdown('<div class="main-header">✈️ 旅游计划智能体 · PC专业版</div>', unsafe_allow_html=True)
    st.caption("基于DeepSeek AI + 高德地图实时数据")

    with st.sidebar:
        menu = st.radio("导航", ["📅 行程规划", "🏞️ 景点查询", "🍜 美食推荐", "☀️ 天气查询", "💰 预算计算", "🚗 交通路线", "📢 实时信息"])

    # ---------- 行程规划 ----------
    if menu == "📅 行程规划":
        st.markdown('<div class="sub-header">🎯 一键生成智能行程</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            origin = st.text_input("🚀 出发地", placeholder="上海、广州...")
        with col2:
            destination = st.text_input("🏙️ 目的地", placeholder="北京、成都...")
        with col3:
            days = st.number_input("📆 游玩天数", 1, 14, 3)
        budget = st.number_input("💰 总预算（可选，元）", 0, 50000, 3000)
        if st.button("✨ 一键生成行程", use_container_width=True):
            if not origin or not destination:
                st.error("请填写出发地和目的地")
            else:
                with st.spinner("AI规划中..."):
                    plan = generate_travel_plan(origin, destination, days, budget if budget>0 else None)
                    st.session_state["plan"] = plan
        if "plan" in st.session_state:
            st.markdown(st.session_state["plan"])
            if st.button("清空行程"):
                del st.session_state["plan"]
                st.rerun()

    # ---------- 景点查询（模拟数据） ----------
    elif menu == "🏞️ 景点查询":
        st.markdown('<div class="sub-header">🏛️ 景点搜索（模拟数据）</div>', unsafe_allow_html=True)
        query = st.text_input("🔍 输入景点名称或城市")
        if st.button("搜索景点"):
            all_spots = [
                {"name": "故宫博物院", "rating": 4.8, "intro": "明清皇宫", "open_time": "8:30-17:00", "ticket": "60元"},
                {"name": "颐和园", "rating": 4.7, "intro": "皇家园林", "open_time": "6:30-20:00", "ticket": "30元"},
                {"name": "西湖", "rating": 4.9, "intro": "免费开放", "open_time": "全天", "ticket": "免费"}
            ]
            if query:
                all_spots = [s for s in all_spots if query.lower() in s['name'].lower()]
            for spot in all_spots:
                with st.expander(f"{spot['name']} ⭐{spot['rating']}"):
                    st.write(spot['intro'])
                    st.write(f"开放: {spot['open_time']}  门票: {spot['ticket']}")

    # ---------- 美食推荐 ----------
    elif menu == "🍜 美食推荐":
        st.markdown('<div class="sub-header">🍽️ 地道美食（高德实时）</div>', unsafe_allow_html=True)
        city_food = st.text_input("📍 城市/区域", placeholder="北京、成都...")
        cuisine = st.selectbox("🍲 菜系", ["不限", "北京菜", "川菜", "杭帮菜", "火锅"])
        if st.button("推荐餐厅"):
            foods = search_foods(city_food, cuisine)
            for f in foods:
                st.markdown(f"### {f['name']}  ⭐ {f['rating']}")
                st.markdown(f"**人均**: {f['price']}  |  **菜系**: {f['cuisine']}")
                st.markdown(f"**地址**: {f['address']}  |  **特色**: {f['specialty']}")
                st.divider()

    # ---------- 天气查询 ----------
    elif menu == "☀️ 天气查询":
        st.markdown('<div class="sub-header">🌤️ 实时天气（高德）</div>', unsafe_allow_html=True)
        city_weather = st.text_input("🌆 城市名称", placeholder="北京")
        if st.button("查询天气"):
            weather = get_weather(city_weather)
            if weather:
                col1, col2, col3 = st.columns(3)
                col1.metric("🌡️ 温度", f"{weather['temp']}°C")
                col2.metric("💧 湿度", f"{weather['humidity']}%")
                col3.metric("💨 风力", weather['wind'])
                st.markdown(f"**天气**: {weather['condition']}")
                st.info(f"👕 **穿衣建议**: {weather['dress']}")
            else:
                st.error("未获取到天气")

    # ---------- 预算计算 ----------
    elif menu == "💰 预算计算":
        st.markdown('<div class="sub-header">💰 智能预算估算</div>', unsafe_allow_html=True)
        days = st.number_input("天数", 1, 14, 3)
        persons = st.number_input("人数", 1, 10, 2)
        level = st.selectbox("消费档次", ["经济型", "舒适型", "豪华型"])
        if st.button("开始估算"):
            level_rates = {"经济型": {"住宿":200, "餐饮":80, "交通":50, "门票":60},
                           "舒适型": {"住宿":400, "餐饮":150, "交通":100, "门票":100},
                           "豪华型": {"住宿":900, "餐饮":350, "交通":200, "门票":200}}
            rates = level_rates[level]
            rooms = (persons + 1) // 2
            details = {
                "住宿": rates["住宿"] * days * rooms,
                "餐饮": rates["餐饮"] * days * persons,
                "交通": rates["交通"] * days * persons,
                "门票": rates["门票"] * days * persons
            }
            total = sum(details.values())
            st.write("费用明细：")
            for k, v in details.items():
                st.write(f"- {k}: ¥{v:,.0f}")
            st.success(f"总计：¥{total:,.0f}")

    # ---------- 交通路线（实时高德驾车） ----------
    elif menu == "🚗 交通路线":
        st.markdown('<div class="sub-header">🚄 实时驾车路线（高德）</div>', unsafe_allow_html=True)
        trans_type = st.radio("交通类型", ["城际交通", "市内交通"], horizontal=True)
        if trans_type == "城际交通":
            col1, col2 = st.columns(2)
            with col1:
                origin = st.text_input("出发城市", "上海")
            with col2:
                dest = st.text_input("到达城市", "北京")
            if st.button("查询城际路线"):
                routes = get_transport(origin, dest, "intercity")
                for r in routes:
                    st.markdown(f"**{r['type']}** | 耗时 {r['duration']} | {r['price']}")
                    st.caption(r['detail'])
                    st.divider()
        else:
            col1, col2 = st.columns(2)
            with col1:
                start = st.text_input("起点（详细地点）", "天安门")
            with col2:
                end = st.text_input("终点", "颐和园")
            if st.button("查询市内路线"):
                routes = get_transport(start, end, "city")
                for r in routes:
                    st.markdown(f"**{r['type']}** | 耗时 {r['duration']} | {r['detail']}")

    # ---------- 实时信息 ----------
    elif menu == "📢 实时信息":
        st.markdown('<div class="sub-header">📡 出行实时动态</div>', unsafe_allow_html=True)
        info_city = st.text_input("城市（用于路况）", "成都", key="traffic_city")
        info_type = st.selectbox("信息类别", ["交通路况", "景区人流", "官方公告"])
        if st.button("获取最新信息"):
            info = get_realtime(info_type, info_city)
            st.info(f"📢 {info}")

if __name__ == "__main__":
    main()
