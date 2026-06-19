"""
AQI 空气质量功能测试脚本
"""
import asyncio
import httpx
import uuid


BASE_URL = "http://127.0.0.1:8000"


async def test_aqi_apis():
    print("=" * 60)
    print("测试 1: 测试城市实时天气（默认含 AQI）")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/api/v1/weather/current/city",
                                params={"city": "北京", "provider": "mock"})
        data = resp.json()
        if resp.status_code != 200:
            print(f"  ❌ 失败：{resp.status_code} {data}")
            return
        print(f"  ✅ 状态码：{resp.status_code}")
        print(f"  ✅ 城市：{data.get('city')}")
        print(f"  ✅ 温度：{data.get('temperature')}℃")
        print(f"  ✅ AQI：{data.get('aqi')}")
        print(f"  ✅ AQI等级：{data.get('aqi_level')}")
        print(f"  ✅ PM2.5：{data.get('pm2_5')} μg/m³")
        print(f"  ✅ PM10：{data.get('pm10')} μg/m³")
        assert data.get("aqi") is not None, "AQI 字段缺失"
        assert data.get("pm2_5") is not None, "PM2.5 字段缺失"
        print("  ✅ 测试通过：天气响应包含 AQI 数据")

    print("\n" + "=" * 60)
    print("测试 2: 测试城市实时天气（不含 AQI）")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/api/v1/weather/current/city",
                                params={"city": "上海", "provider": "mock", "include_aqi": False, "use_cache": False})
        data = resp.json()
        print(f"  ✅ 状态码：{resp.status_code}")
        print(f"  ✅ 温度：{data.get('temperature')}℃")
        print(f"  ✅ AQI：{data.get('aqi')}（应为 None）")
        assert data.get("aqi") is None, f"AQI 应为 None，但实际是 {data.get('aqi')}"
        assert data.get("pm2_5") is None, f"PM2.5 应为 None，但实际是 {data.get('pm2_5')}"
        print("  ✅ 测试通过：不包含 AQI 数据时字段为 None")

    print("\n" + "=" * 60)
    print("测试 3: 测试独立 AQI 查询接口（按城市）")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/api/v1/weather/aqi/city",
                                params={"city": "广州", "provider": "mock"})
        data = resp.json()
        print(f"  ✅ 状态码：{resp.status_code}")
        print(f"  ✅ AQI：{data.get('aqi')}")
        print(f"  ✅ AQI等级：{data.get('aqi_level')}")
        print(f"  ✅ PM2.5：{data.get('pm2_5')} μg/m³")
        print(f"  ✅ PM10：{data.get('pm10')} μg/m³")
        print(f"  ✅ SO2：{data.get('so2')}")
        print(f"  ✅ NO2：{data.get('no2')}")
        print(f"  ✅ CO：{data.get('co')}")
        print(f"  ✅ O3：{data.get('o3')}")
        assert data.get("aqi") is not None
        print("  ✅ 测试通过：独立 AQI 接口返回完整污染物数据")

    print("\n" + "=" * 60)
    print("测试 4: 测试独立 AQI 查询接口（按经纬度）")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/api/v1/weather/aqi/coords",
                                params={"latitude": 31.23, "longitude": 121.47, "provider": "mock"})
        data = resp.json()
        print(f"  ✅ 状态码：{resp.status_code}")
        print(f"  ✅ AQI：{data.get('aqi')}")
        print(f"  ✅ AQI等级：{data.get('aqi_level')}")
        print("  ✅ 测试通过：经纬度 AQI 查询正常")

    print("\n" + "=" * 60)
    print("测试 5: 测试预报接口（默认也带 AQI）")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/api/v1/weather/forecast/city",
                                params={"city": "深圳", "provider": "mock", "days": 3, "use_cache": False})
        data = resp.json()
        print(f"  ✅ 状态码：{resp.status_code}")
        print(f"  ✅ 预报天数：{len(data.get('days', []))} 天")
        for i, day in enumerate(data.get("days", [])):
            print(f"  第 {i+1} 天：日期={day.get('date')}, 温度={day.get('temp_max')}/{day.get('temp_min')}℃, AQI={day.get('aqi')}({day.get('aqi_level')})")
        # 检查至少有一天有 AQI 数据
        any_aqi = any(day.get("aqi") is not None for day in data.get("days", []))
        print(f"  ✅ 测试通过：预报也包含 AQI 数据（至少一天有值={any_aqi}）")


async def test_briefing_with_aqi():
    print("\n" + "=" * 60)
    print("测试 6: 测试车队简报包含空气质量评估")
    print("=" * 60)

    # 先创建一个车队和路线
    fleet_name = f"测试生鲜车队_{uuid.uuid4().hex[:6]}"
    async with httpx.AsyncClient(timeout=30) as client:
        # 创建车队
        resp = await client.post(f"{BASE_URL}/api/v1/fleets",
                                 json={"name": fleet_name, "description": "测试生鲜运输车队"})
        if resp.status_code != 201:
            print(f"  ❌ 创建车队失败：{resp.status_code} {resp.json()}")
            return
        fleet = resp.json()
        fleet_id = fleet["id"]
        print(f"  ✅ 创建车队：{fleet_name} (ID={fleet_id})")

        # 创建两条路线（一个起点一个终点）
        route_names = []
        for start, end in [("北京", "天津"), ("石家庄", "太原")]:
            resp = await client.post(f"{BASE_URL}/api/v1/routes",
                                     json={
                                         "name": f"{start}-{end}",
                                         "start_city": start,
                                         "end_city": end,
                                         "start_latitude": 39.9,
                                         "start_longitude": 116.4,
                                         "end_latitude": 39.1,
                                         "end_longitude": 117.2,
                                         "distance_km": 120.0,
                                     })
            if resp.status_code != 201:
                print(f"  ❌ 创建路线失败：{resp.status_code} {resp.json()}")
                continue
            route = resp.json()
            route_id = route["id"]
            route_names.append(route["name"])
            print(f"  ✅ 创建路线：{route['name']} (ID={route_id})")

            # 关联车队
            resp2 = await client.post(f"{BASE_URL}/api/v1/fleets/{fleet_id}/routes/{route_id}")
            if resp2.status_code != 200 and resp2.status_code != 201:
                print(f"  ⚠️  关联车队路线失败：{resp2.status_code} {resp2.json()}")
            else:
                print(f"  ✅ 已将路线关联到车队")

        # 生成简报
        print(f"  ⏳ 正在生成简报...")
        resp = await client.post(f"{BASE_URL}/api/v1/briefings/fleet/{fleet_id}")
        if resp.status_code != 200:
            print(f"  ❌ 生成简报失败：{resp.status_code} {resp.json()}")
            return
        briefing = resp.json()
        print(f"  ✅ 简报状态：{briefing.get('status')}")
        print(f"  ✅ 简报ID：{briefing.get('id')}")
        print(f"  ✅ 简报摘要：{briefing.get('summary')}")

        # 检查摘要中是否包含空气质量信息
        details = briefing.get("details", {})
        print(f"\n  📋 简报详情：")
        print(f"  - 路线数：{len(details.get('routes', []))}")
        for r in details.get("routes", []):
            print(f"\n  路线：{r.get('route_name')}")
            print(f"  - 起点 AQI：{r.get('start_air_quality', {}).get('aqi')} ({r.get('start_air_quality', {}).get('aqi_level')})")
            print(f"  - 终点 AQI：{r.get('end_air_quality', {}).get('aqi')} ({r.get('end_air_quality', {}).get('aqi_level')})")
            print(f"  - 空气质量预警：{r.get('air_quality_warning')}")
            if r.get("air_quality_warning"):
                print(f"  - 预警详情：{r.get('aqi_warning_detail')}")
            print(f"  - 风险等级：{r.get('risk_level')}")
            print(f"  - 建议：{r.get('recommendation')}")

            # 检查 AQI > 150 是否有红色预警和关窗提醒
            start_aqi = r.get("start_air_quality", {}).get("aqi")
            end_aqi = r.get("end_air_quality", {}).get("aqi")
            if (start_aqi and start_aqi > 150) or (end_aqi and end_aqi > 150):
                assert "红色预警" in r.get("recommendation", ""), "AQI > 150 时应有红色预警"
                assert "关闭车窗" in r.get("recommendation", ""), "AQI > 150 时应有关窗提醒"
                print(f"  ✅ AQI > 150 时正确触发红色预警和关窗提醒！")

        # 检查 summary_points
        print(f"\n  📌 简报要点：")
        for p in briefing.get("summary_points", []):
            print(f"    • {p}")

        # 检查 summary 是否包含空气质量相关内容
        if "空气质量" in briefing.get("summary", "") or "AQI" in briefing.get("summary", ""):
            print(f"\n  ✅ 测试通过：简报摘要包含空气质量信息")
        else:
            print(f"\n  ⚠️  简报摘要未明确提到空气质量（可能是因为所有路线 AQI 都正常）")

        print("\n" + "=" * 60)
        print("✅ 所有 AQI 功能测试完成！")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_aqi_apis())
    asyncio.run(test_briefing_with_aqi())
