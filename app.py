import streamlit as st
import requests
import json
import os
from datetime import datetime
import random
import time
import subprocess

@st.cache_resource
def get_flyai_command():
    """
    安装 @fly-ai/cli 并返回 flyai 命令的完整路径
    """
    # 先尝试直接使用 'flyai' 命令
    try:
        subprocess.run(["flyai", "--version"], capture_output=True, check=True)
        return "flyai"
    except:
        pass

    # 未安装，执行全局安装
    try:
        subprocess.run(["npm", "install", "-g", "@fly-ai/cli"], check=True, timeout=120)
    except subprocess.CalledProcessError as e:
        st.error(f"安装 flyai 失败: {e}")
        raise

    # 获取 npm 全局 bin 目录
    result = subprocess.run(["npm", "bin", "-g"], capture_output=True, text=True, check=True)
    global_bin = result.stdout.strip()
    flyai_path = os.path.join(global_bin, "flyai")
    if os.path.exists(flyai_path):
        return flyai_path

    # 常见备选路径
    candidates = [
        "/usr/local/bin/flyai",
        "/home/adminuser/.npm-global/bin/flyai"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p

    raise FileNotFoundError("无法找到 flyai 命令，请检查安装过程")
    
# -------------------- 页面配置 --------------------
st.set_page_config(page_title="旅游计划智能体 · 专业版", page_icon="✈️", layout="wide")

# -------------------- 样式美化 --------------------
st.markdown("""
<style>
.main-header { font-size: 2.2rem; font-weight: bold; background: linear-gradient(135deg, #1e3c72, #2b4c7c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.sub-header { font-size: 1.3rem; font-weight: 500; color: #2c3e50; border-left: 4px solid #3498db; padding-left: 1rem; margin: 1rem 0; }
.stButton > button { background: linear-gradient(90deg, #3498db, #2980b9); color: white; border-radius: 30px; border: none; }
</style>
""", unsafe_allow_html=True)

# -------------------- 密钥读取 --------------------
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

def get_flyai_key():
    try:
        return st.secrets["FLYAI_API_KEY"]
    except:
        st.warning("⚠️ 未找到飞猪 FLYAI_API_KEY，将使用演示数据")
        return None

# -------------------- DeepSeek 行程规划 --------------------
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

# -------------------- 高德景点搜索（实时） --------------------
def search_attractions(city, keyword=""):
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
        search_keyword = keyword if keyword else "景点"
        around_url = "https://restapi.amap.com/v3/place/around"
        around_params = {
            "key": key, "location": location, "keywords": search_keyword,
            "types": "110000", "radius": 20000, "offset": 20, "page": 1, "output": "JSON"
        }
        resp = requests.get(around_url, params=around_params, timeout=10)
        data = resp.json()
        if data.get("status") == "1" and data.get("pois"):
            results = []
            for poi in data["pois"]:
                rating = poi.get("biz_ext", {}).get("rating")
                rating_val = float(rating) if rating else 4.0
                distance = int(poi.get("distance", 0)) / 1000
                results.append({
                    "name": poi["name"],
                    "rating": rating_val,
                    "distance": f"{distance:.1f}km",
                    "intro": poi.get("address", "")[:80],
                    "open_time": poi.get("biz_ext", {}).get("open_time", "暂无"),
                    "ticket": poi.get("biz_ext", {}).get("ticket", "暂无")
                })
            return results
        else:
            st.warning(f"未找到景点：{data.get('info')}")
            return []
    except Exception as e:
        st.error(f"景点搜索异常：{e}")
        return []

# -------------------- 高德美食搜索（实时） --------------------
def search_foods(city, cuisine="不限"):
    key = get_amap_key()
    if not city:
        return []
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
            "key": key, "location": location, "keywords": keywords,
            "types": "050000", "radius": 5000, "offset": 20, "page": 1, "output": "JSON"
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
                    "name": poi["name"],
                    "rating": rating,
                    "price": price_str,
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

# -------------------- 高德天气查询（实时） --------------------
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
                "wind": f"{wind}级", "dress": dress
            }
        else:
            st.warning(f"天气查询失败：{data.get('info')}")
            return None
    except Exception as e:
        st.error(f"天气查询异常：{e}")
        return None

# -------------------- 高德驾车路线（实时） --------------------
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
            return []
    except Exception as e:
        st.error(f"路线规划失败：{e}")
        return []

# -------------------- 飞猪实时交通查询（火车/飞机） --------------------
def search_transport(origin, destination, date, transport_type="train"):
    flyai_cmd = get_flyai_command()
    # 注意命令是 'search-train'（根据飞猪文档）
    cmd = [flyai_cmd, "search-train", "--from", origin, "--to", destination, "--date", date]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            st.error(f"查询失败: {result.stderr}")
            return []
        # 尝试解析 JSON 输出
        import json
        data = json.loads(result.stdout)
        routes = []
        for item in data.get("data", []):
            routes.append({
                "train_no": item.get("trainNumber") or item.get("trainNo") or "未知",
                "departure_time": item.get("departureTime", "未知"),
                "arrival_time": item.get("arrivalTime", "未知"),
                "duration": item.get("duration", "未知"),
                "price": item.get("price", "暂无"),
                "seats": item.get("remainingSeats", "未知")
            })
        return routes
    except subprocess.TimeoutExpired:
        st.error("查询超时，请稍后重试")
        return []
    except json.JSONDecodeError as e:
        st.error(f"解析数据失败: {e}\n原始输出: {result.stdout}")
        return []
    except Exception as e:
        st.error(f"查询出错: {e}")
        return []
        
# -------------------- PC端主界面 --------------------
def main():
    st.markdown('<div class="main-header">✈️ 旅游计划智能体 · 专业版</div>', unsafe_allow_html=True)
    st.caption("基于 DeepSeek AI + 高德地图实时数据 + 飞猪实时交通")

    with st.sidebar:
        menu = st.radio("导航", [
            "📅 行程规划", "🏞️ 景点查询", "🍜 美食推荐",
            "☀️ 天气查询", "💰 预算计算", "🚗 交通路线", "📢 实时信息"
        ])

    # ---------- 1. 行程规划 ----------
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

    # ---------- 2. 景点查询 ----------
    elif menu == "🏞️ 景点查询":
        st.markdown('<div class="sub-header">🏛️ 景点搜索（高德实时）</div>', unsafe_allow_html=True)
        city = st.text_input("📍 城市名称", placeholder="北京、成都...")
        keyword = st.text_input("🔍 景点关键词（可选）", placeholder="故宫、熊猫...")
        if st.button("搜索景点"):
            if not city:
                st.error("请输入城市名称")
            else:
                with st.spinner("搜索中..."):
                    spots = search_attractions(city, keyword)
                    if spots:
                        for spot in spots:
                            with st.expander(f"🏯 {spot['name']}  ⭐ {spot['rating']}  |  📍 {spot['distance']}"):
                                st.markdown(f"**简介**: {spot['intro']}")
                                st.markdown(f"**开放时间**: {spot['open_time']}  |  **门票**: {spot['ticket']}")
                    else:
                        st.info("未找到相关景点")

    # ---------- 3. 美食推荐 ----------
    elif menu == "🍜 美食推荐":
        st.markdown('<div class="sub-header">🍽️ 地道美食（高德实时）</div>', unsafe_allow_html=True)
        city_food = st.text_input("📍 城市/区域", placeholder="北京、成都...")
        cuisine = st.selectbox("🍲 菜系", ["不限", "北京菜", "川菜", "杭帮菜", "火锅"])
        if st.button("推荐餐厅"):
            if not city_food:
                st.error("请输入城市名称")
            else:
                with st.spinner("搜索中..."):
                    foods = search_foods(city_food, cuisine)
                    if foods:
                        for f in foods:
                            st.markdown(f"### {f['name']}  ⭐ {f['rating']}")
                            st.markdown(f"**人均**: {f['price']}  |  **菜系**: {f['cuisine']}")
                            st.markdown(f"**地址**: {f['address']}  |  **特色**: {f['specialty']}")
                            st.divider()
                    else:
                        st.info("未找到相关美食")

    # ---------- 4. 天气查询 ----------
    elif menu == "☀️ 天气查询":
        st.markdown('<div class="sub-header">🌤️ 实时天气（高德）</div>', unsafe_allow_html=True)
        city_weather = st.text_input("🌆 城市名称", placeholder="北京")
        if st.button("查询天气"):
            if not city_weather:
                st.error("请输入城市")
            else:
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

    # ---------- 5. 预算计算（模拟） ----------
    elif menu == "💰 预算计算":
        st.markdown('<div class="sub-header">💰 智能预算估算</div>', unsafe_allow_html=True)
        days = st.number_input("天数", 1, 14, 3)
        persons = st.number_input("人数", 1, 10, 2)
        level = st.selectbox("消费档次", ["经济型", "舒适型", "豪华型"])
        if st.button("开始估算"):
            level_rates = {
                "经济型": {"住宿":200, "餐饮":80, "交通":50, "门票":60},
                "舒适型": {"住宿":400, "餐饮":150, "交通":100, "门票":100},
                "豪华型": {"住宿":900, "餐饮":350, "交通":200, "门票":200}
            }
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

    # ---------- 6. 交通路线（城际：飞猪实时；市内：高德驾车） ----------
    elif menu == "🚗 交通路线":
        st.markdown('<div class="sub-header">🚄 实时出行方案（动车/飞机）</div>', unsafe_allow_html=True)
        trans_type = st.radio("交通类型", ["城际交通", "市内交通"], horizontal=True)

        if trans_type == "城际交通":
            col1, col2, col3 = st.columns(3)
            with col1:
                origin = st.text_input("出发城市", "上海")
            with col2:
                destination = st.text_input("到达城市", "北京")
            with col3:
                travel_date = st.date_input("出行日期", datetime.now())

            transport_type = st.radio("选择交通工具", ["火车（高铁/动车）", "飞机"], horizontal=True)

            if st.button("查询实时方案"):
                with st.spinner("正在获取实时车次/航班信息..."):
                    if transport_type == "火车（高铁/动车）":
                        routes = search_transport(origin, destination, travel_date.strftime("%Y-%m-%d"), "train")
                    else:
                        routes = search_transport(origin, destination, travel_date.strftime("%Y-%m-%d"), "flight")

                    if routes:
                        for route in routes:
                            with st.container():
                                train_no = route.get("train_no", route.get("flight_no", "未知班次"))
                                st.markdown(f"### {train_no}")
                                st.write(f"**出发**：{route.get('departure_time', '未知')}  →  **到达**：{route.get('arrival_time', '未知')}")
                                st.write(f"**耗时**：{route.get('duration', '未知')}  |  **票价**：{route.get('price', '暂无')}")
                                if route.get('seats'):
                                    st.write(f"**余票/舱位**：{route['seats']}")
                                st.divider()
                    else:
                        st.warning("未查询到相关方案，请尝试其他日期或城市")
        else:
            # 市内交通：高德驾车
            st.markdown("### 🚗 市内驾车路线规划")
            col1, col2 = st.columns(2)
            with col1:
                start = st.text_input("起点（详细地点）", "天安门")
            with col2:
                end = st.text_input("终点", "颐和园")
            if st.button("查询驾车路线"):
                with st.spinner("规划路线中..."):
                    routes = get_driving_route(start, end)
                    if routes:
                        for r in routes:
                            st.markdown(f"**{r['type']}** | 耗时 {r['duration']} | {r['price']}")
                            st.caption(r['detail'])
                    else:
                        st.warning("未找到驾车路线，请检查地点是否正确")

    # ---------- 7. 实时信息（演示） ----------
    elif menu == "📢 实时信息":
        st.markdown('<div class="sub-header">📡 出行实时动态</div>', unsafe_allow_html=True)
        info_city = st.text_input("城市（用于路况）", "成都")
        info_type = st.selectbox("信息类别", ["交通路况", "景区人流", "官方公告"])
        if st.button("获取最新信息"):
            # 这里可对接高德交通态势或官方公告，暂返回演示信息
            mock_info = {
                "交通路况": f"{info_city}市中心路况良好，部分路段轻度拥堵",
                "景区人流": "当前景区人流指数：中等，建议错峰出行",
                "官方公告": "今日无特殊公告，出行愉快"
            }
            st.info(f"📢 {mock_info.get(info_type, '暂无数据')}")

if __name__ == "__main__":
    main()
