# -*- coding: utf-8 -*-
"""
날씨 정보 조회 서비스

KMA(기상청) API와 Open-Meteo API를 사용하여 날씨 정보를 조회합니다.
"""
import os
import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone, timedelta

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# KMA 도시 그리드 좌표
KMA_CITY_GRID = {
    "서울": (60, 127),
    "Seoul": (60, 127),
    "부산": (98, 76),
    "Busan": (98, 76),
    "대구": (89, 90),
    "Daegu": (89, 90),
    "인천": (55, 124),
    "Incheon": (55, 124),
    "광주": (58, 74),
    "Gwangju": (58, 74),
    "대전": (67, 100),
    "Daejeon": (67, 100),
}

# KMA 도시 별칭
KMA_CITY_ALIAS = {
    "서울": "Seoul",
    "부산": "Busan",
    "대구": "Daegu",
    "인천": "Incheon",
    "광주": "Gwangju",
    "대전": "Daejeon",
}


class WeatherService:
    """날씨 정보 조회 서비스"""
    
    def __init__(self, kma_api_key: Optional[str] = None):
        """
        Args:
            kma_api_key: KMA API 키 (선택사항)
        """
        self.kma_api_key = kma_api_key
        self.http = self._make_http_session()
    
    def _make_http_session(self) -> requests.Session:
        """HTTP 세션 생성 (재시도 로직 포함)"""
        retry = Retry(
            total=3, connect=3, read=3,
            backoff_factor=0.6,
            status_forcelist=(502, 503, 504),
            allowed_methods=("GET", "POST"),
            raise_on_status=False,
        )
        s = requests.Session()
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        return s
    
    def fetch_weather(self, location: str) -> Dict[str, str]:
        """
        날씨 정보 조회
        
        Args:
            location: 도시 또는 지역명
            
        Returns:
            Dict[str, str]: 날씨 정보
                - status: 날씨 상태 텍스트
                - tip: 날씨 팁 텍스트
                - error: 에러 메시지 (에러 발생 시)
        """
        if not location:
            return {
                "status": "지역을 입력해주세요.",
                "tip": "날씨 팁을 불러오지 못했습니다.",
                "error": "empty_location"
            }
        
        # KMA API 시도
        if self.kma_api_key:
            try:
                result = self._fetch_weather_from_kma(location)
                if result:
                    return result
            except Exception as exc:
                logger.warning(f"[weather] KMA fetch error: {exc}")
        
        # Open-Meteo API 시도
        try:
            return self._fetch_weather_from_open_meteo(location)
        except requests.RequestException as exc:
            logger.warning(f"날씨 API 요청 오류: {exc}")
            return {
                "status": "날씨 정보를 가져오지 못했습니다.",
                "tip": "날씨 팁을 불러오지 못했습니다. 기본적으로 우산과 마스크를 준비해 주세요.",
                "error": str(exc)
            }
        except Exception as exc:
            logger.error(f"날씨 정보 처리 오류: {exc}")
            return {
                "status": "날씨 정보를 처리하는 중 오류가 발생했습니다.",
                "tip": "날씨 팁을 불러오지 못했습니다. 기본적으로 우산과 마스크를 준비해 주세요.",
                "error": str(exc)
            }
    
    def _fetch_weather_from_kma(self, location: str) -> Optional[Dict[str, str]]:
        """KMA API로 날씨 정보 조회"""
        grid = None
        resolved_name = location
        
        # 도시 그리드 좌표 찾기
        for name, coords in KMA_CITY_GRID.items():
            if name.lower() == location.lower():
                grid = coords
                resolved_name = name
                break
        
        if not grid:
            return None
        
        nx, ny = grid
        kst = datetime.now(timezone.utc) + timedelta(hours=9)
        base_date = kst.date()
        
        # 기준 시간 결정
        base_times = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]
        current_hm = kst.strftime("%H%M")
        base_time = None
        
        for bt in base_times:
            if current_hm >= bt:
                base_time = bt
                break
        
        if base_time is None:
            base_time = "2300"
            base_date = (kst - timedelta(days=1)).date()
        
        base_date_str = base_date.strftime("%Y%m%d")
        service_url = os.environ.get(
            "KMA_API_URL",
            "https://apihub.kma.go.kr/api/typ02/openapi/VilageFcstInfoService_2.0/getVilageFcst",
        )
        
        params = {
            "serviceKey": self.kma_api_key,
            "pageNo": 1,
            "numOfRows": 500,
            "dataType": "JSON",
            "base_date": base_date_str,
            "base_time": base_time,
            "nx": nx,
            "ny": ny,
        }
        
        resp = requests.get(service_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        items = (
            (((data.get("response") or {}).get("body") or {}).get("items") or {}).get("item")
            or []
        )
        
        if not items:
            return None
        
        def find_value(category: str, target_date: str, preferred_times: list[str]):
            for t in preferred_times:
                for item in items:
                    if (item.get("category") == category and 
                        item.get("fcstDate") == target_date and 
                        item.get("fcstTime") == t):
                        return item.get("fcstValue")
            return None
        
        # 오늘 날씨
        current_hour = int(kst.strftime("%H"))
        preferred_today = [f"{current_hour:02d}00"]
        for offset in range(1, 4):
            preferred_today.append(f"{(current_hour + offset) % 24:02d}00")
        today_date_str = kst.strftime("%Y%m%d")
        
        temp_today = find_value("TMP", today_date_str, preferred_today)
        sky_today = find_value("SKY", today_date_str, preferred_today)
        pty_today = find_value("PTY", today_date_str, preferred_today)
        
        # 내일 날씨
        tomorrow_date_str = (kst + timedelta(days=1)).strftime("%Y%m%d")
        preferred_morning = ["0600", "0900", "1200"]
        temp_tomorrow = find_value("TMP", tomorrow_date_str, preferred_morning)
        sky_tomorrow = find_value("SKY", tomorrow_date_str, preferred_morning)
        pty_tomorrow = find_value("PTY", tomorrow_date_str, preferred_morning)
        
        if temp_today is None and temp_tomorrow is None:
            return None
        
        def fmt_temp(value):
            if value is None:
                return "--°C"
            try:
                return f"{float(value):.1f}°C"
            except Exception:
                return f"{value}°C"
        
        today_desc = self._describe_kma_weather(sky_today, pty_today)
        tomorrow_desc = self._describe_kma_weather(sky_tomorrow, pty_tomorrow)
        
        status_text = (
            f"{resolved_name}\n현재 {fmt_temp(temp_today)} · {today_desc}\n"
            f"내일 오전 {fmt_temp(temp_tomorrow)} · {tomorrow_desc}"
        )
        tip_text = self._weather_tip(temp_tomorrow, pty_code=pty_tomorrow)
        
        return {
            "status": status_text,
            "tip": tip_text
        }
    
    def _fetch_weather_from_open_meteo(self, location: str) -> Dict[str, str]:
        """Open-Meteo API로 날씨 정보 조회"""
        results = []
        candidates = [location]
        
        # 별칭 추가
        alias = KMA_CITY_ALIAS.get(location)
        if alias and alias not in candidates:
            candidates.append(alias)
        
        # Geocoding
        for candidate in candidates:
            for lang in ("ko", "en"):
                geo_resp = requests.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": candidate, "count": 1, "language": lang, "format": "json"},
                    timeout=10,
                )
                geo_resp.raise_for_status()
                geo_json = geo_resp.json()
                results = geo_json.get("results") or []
                if results:
                    break
            if results:
                break
        
        if not results:
            return {
                "status": "해당 위치를 찾을 수 없습니다. 영어/한국어 표기로 다시 시도해 주세요.",
                "tip": "날씨 팁을 불러오지 못했습니다. 기본적으로 우산과 마스크를 준비해 주세요.",
                "error": "location_not_found"
            }
        
        top = results[0]
        lat = top.get("latitude")
        lon = top.get("longitude")
        resolved_name = ", ".join(filter(None, [top.get("name"), top.get("country")]))
        
        # 날씨 예보
        forecast_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,weathercode",
                "current_weather": True,
                "forecast_days": 2,
                "timezone": "auto",
            },
            timeout=10,
        )
        forecast_resp.raise_for_status()
        forecast_json = forecast_resp.json()
        
        current = forecast_json.get("current_weather") or {}
        hourly = forecast_json.get("hourly") or {}
        
        # 현재 날씨
        current_temp = current.get("temperature")
        current_temp_text = f"{current_temp}°C" if current_temp is not None else "--°C"
        current_desc = self._weather_description(current.get("weathercode"))
        
        # 내일 오전 날씨
        tomorrow_temp, tomorrow_code = self._extract_tomorrow_morning(hourly)
        tomorrow_temp_text = f"{tomorrow_temp}°C" if tomorrow_temp is not None else "--°C"
        tomorrow_desc = self._weather_description(tomorrow_code)
        
        status_text = (
            f"{resolved_name}\n현재 {current_temp_text} · {current_desc}\n"
            f"내일 오전 {tomorrow_temp_text} · {tomorrow_desc}"
        )
        tip_text = self._weather_tip(tomorrow_temp, weather_code=tomorrow_code)
        
        return {
            "status": status_text,
            "tip": tip_text
        }
    
    def _describe_kma_weather(self, sky: Optional[str], pty: Optional[str]) -> str:
        """KMA 날씨 코드를 설명 텍스트로 변환"""
        try:
            pty_val = int(pty) if pty is not None else 0
        except Exception:
            pty_val = 0
        
        if pty_val == 1:
            return "비"
        if pty_val == 2:
            return "비/눈"
        if pty_val == 3:
            return "눈"
        if pty_val == 5:
            return "빗방울"
        if pty_val == 6:
            return "빗방울/눈날림"
        if pty_val == 7:
            return "눈날림"
        
        try:
            sky_val = int(sky) if sky is not None else 0
        except Exception:
            sky_val = 0
        
        sky_map = {
            1: "맑음",
            3: "구름 많음",
            4: "흐림",
        }
        return sky_map.get(sky_val, "상세 정보 없음")
    
    def _weather_description(self, code: Optional[int]) -> str:
        """Open-Meteo 날씨 코드를 설명 텍스트로 변환"""
        mapping = {
            0: "맑음",
            1: "대체로 맑음",
            2: "부분적으로 흐림",
            3: "흐림",
            45: "안개",
            48: "서리 안개",
            51: "실비",
            53: "약한 이슬비",
            55: "강한 이슬비",
            61: "약한 비",
            63: "보통 비",
            65: "강한 비",
            71: "가벼운 눈",
            73: "보통 눈",
            75: "강한 눈",
            80: "약한 소나기",
            81: "보통 소나기",
            82: "강한 소나기",
            95: "천둥번개",
            96: "우박 가능",
            99: "강한 폭우/우박",
        }
        return mapping.get(code, "상세 정보 없음")
    
    def _weather_tip(
        self, 
        morning_temp: Optional[float], 
        pty_code: Optional[str] = None, 
        weather_code: Optional[int] = None
    ) -> str:
        """날씨에 따른 팁 생성"""
        tips: List[str] = []
        rain_expected = False
        
        # 비 예보 확인
        if pty_code is not None:
            try:
                p_val = int(pty_code)
                if p_val in {1, 2, 3, 5, 6, 7}:
                    rain_expected = True
            except Exception:
                pass
        elif weather_code is not None:
            rain_expected = weather_code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
        
        if rain_expected:
            tips.append("비 예보가 있으니 우산을 챙기세요.")
        
        # 기온에 따른 팁
        temp_tip_added = False
        if morning_temp is not None:
            try:
                temp = float(morning_temp)
                if temp <= 0:
                    tips.append("아침 기온이 영하권이라 두꺼운 외투와 장갑을 준비하세요.")
                    temp_tip_added = True
                elif temp <= 5:
                    tips.append("쌀쌀하니 코트나 패딩을 추천합니다.")
                    temp_tip_added = True
                elif temp >= 25:
                    tips.append("무더울 수 있으니 가볍고 통풍이 잘 되는 복장을 입으세요.")
                    temp_tip_added = True
            except Exception:
                pass
        
        if not temp_tip_added:
            tips.append("기온 변화에 대비해 겉옷을 하나 챙기면 좋습니다.")
        
        tips.append("미세먼지 정보가 없으나 기본적으로 마스크 착용을 권장합니다.")
        
        return " ".join(tips)
    
    def _extract_tomorrow_morning(self, hourly: dict) -> Tuple[Optional[float], Optional[int]]:
        """내일 오전 날씨 추출"""
        try:
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            codes = hourly.get("weathercode", [])
            
            target_date = (datetime.now() + timedelta(days=1)).date()
            candidate = None
            
            for t_str, temp, code in zip(times, temps, codes):
                dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                if dt.date() == target_date and 6 <= dt.hour <= 10:
                    candidate = (temp, code)
                    break
            
            if not candidate and temps:
                candidate = (temps[0], codes[0] if codes else None)
            
            return candidate or (None, None)
        except Exception:
            return (None, None)
