from __future__ import annotations

import re
from bs4 import BeautifulSoup


def parse_item(html: str, item_id: int) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    if not soup.select_one("main"):
        return None
    base = _parse_common(soup, item_id)
    if base["item_type"] == "equipment":
        return _parse_equipment(soup, base)
    return _parse_consumable_etc(soup, base)


def _strip(el) -> str:
    if el is None:
        return ""
    return el.get_text(strip=True) if hasattr(el, "get_text") else str(el).strip()


def _parse_stat_value(raw: str) -> dict | None:
    raw = raw.strip()
    m = re.search(r"[+\-]?\s*(\d+)\s*\((\d+)~(\d+)\)", raw)
    if m:
        return {"base": int(m.group(1)), "min": int(m.group(2)), "max": int(m.group(3))}
    m = re.search(r"[+\-]?\s*(\d+)", raw)
    if m:
        return {"base": int(m.group(1))}
    return None


def _parse_attack_speed(raw: str) -> dict | None:
    m = re.search(r"(\d+)\s*\((.+?)\)", raw)
    if m:
        return {"value": int(m.group(1)), "label": m.group(2).strip()}
    m = re.search(r"(\d+)", raw)
    if m:
        return {"value": int(m.group(1)), "label": None}
    return None


def _determine_item_type(item_id: int, category_major: str) -> str:
    major = category_major.lower()
    if major in ("방어구", "장비"):
        return "equipment"
    if major in ("소비", "consumable"):
        return "consumable"
    if major in ("etc", "기타"):
        return "etc"
    first = str(item_id)[0]
    if first == "1":
        return "equipment"
    if first == "2":
        return "consumable"
    return "etc"


def _parse_common(soup: BeautifulSoup, item_id: int) -> dict:
    main_info = soup.select_one(".main-info")

    item_name = _strip(main_info.select_one("h1")) if main_info else ""

    icon_img = main_info.select_one("img[alt$='이미지']") if main_info else None
    icon_url = icon_img["src"] if icon_img else None

    category_major = category_mid = category_sub = ""
    acc_box = main_info.select_one(".acc-box") if main_info else None
    if acc_box:
        for span in acc_box.select("span.acc"):
            text = _strip(span)
            if "대분류" in text:
                category_major = text.split(":")[-1].strip()
            elif "중분류" in text:
                category_mid = text.split(":")[-1].strip()
            elif "소분류" in text:
                category_sub = text.split(":")[-1].strip()

    return {
        "item_id": item_id,
        "item_name": item_name,
        "item_type": _determine_item_type(item_id, category_major),
        "category_major": category_major,
        "category_mid": category_mid,
        "category_sub": category_sub,
        "icon_url": icon_url,
    }


def _parse_equipment(soup: BeautifulSoup, base: dict) -> dict:
    main_info = soup.select_one(".main-info")
    effect_info = soup.select_one(".effect-info")

    equipped_img_url = None
    if main_info:
        all_imgs = main_info.select("div[style*='150px'] img")
        if len(all_imgs) >= 2:
            equipped_img_url = all_imgs[1].get("src")

    req = {
        "req_level": 0, "req_str": 0, "req_dex": 0,
        "req_int": 0, "req_luk": 0, "req_pop": None,
        "req_job": "공용", "gender": "공용",
    }
    req_div = main_info.select_one(".req") if main_info else None
    if req_div:
        for h3 in req_div.select("h3"):
            text = _strip(h3)
            if "REQ LEV" in text:
                m = re.search(r"(\d+)", text)
                req["req_level"] = int(m.group(1)) if m else 0
            elif "REQ STR" in text:
                m = re.search(r"(\d+)", text)
                req["req_str"] = int(m.group(1)) if m else 0
            elif "REQ DEX" in text:
                m = re.search(r"(\d+)", text)
                req["req_dex"] = int(m.group(1)) if m else 0
            elif "REQ INT" in text:
                m = re.search(r"(\d+)", text)
                req["req_int"] = int(m.group(1)) if m else 0
            elif "REQ LUK" in text:
                m = re.search(r"(\d+)", text)
                req["req_luk"] = int(m.group(1)) if m else 0
            elif "REQ POP" in text:
                m = re.search(r"(\d+)", text)
                req["req_pop"] = int(m.group(1)) if m else None
            elif "REQ JOB" in text:
                req["req_job"] = text.split(":")[-1].strip()
            elif "GENDER" in text:
                req["gender"] = text.split(":")[-1].strip()

    effects = {}
    upgrade_slots = None

    if effect_info:
        class_map = {
            "acc_hp": "max_hp",
            "acc_mp": "max_mp",
            "acc_physic_attack": "phys_attack",
            "acc_magic_attack": "mag_attack",
        }
        for css_class, field_name in class_map.items():
            el = effect_info.select_one(f".{css_class}")
            if el:
                text = _strip(el)
                val_part = text.split(":")[-1] if ":" in text else text
                effects[field_name] = _parse_stat_value(val_part)

        for span in effect_info.select("span.acc"):
            text = _strip(span)
            if "MAPLELAND" in text:
                continue
            if "물리방어력" in text:
                effects["phys_defense"] = _parse_stat_value(text.split(":")[-1])
            elif "마법방어력" in text:
                effects["mag_defense"] = _parse_stat_value(text.split(":")[-1])
            elif "공격속도" in text:
                effects["attack_speed"] = _parse_attack_speed(text.split(":")[-1])
            elif "업그레이드 가능 횟수" in text:
                m = re.search(r"(\d+)", text.split(":")[-1])
                upgrade_slots = int(m.group(1)) if m else None
            elif "STR" in text and "REQ" not in text:
                effects["str"] = _parse_stat_value(text.split(":")[-1])
            elif "DEX" in text and "REQ" not in text:
                effects["dex"] = _parse_stat_value(text.split(":")[-1])
            elif "INT" in text and "REQ" not in text:
                effects["int"] = _parse_stat_value(text.split(":")[-1])
            elif "LUK" in text and "REQ" not in text:
                effects["luk"] = _parse_stat_value(text.split(":")[-1])
            elif "명중률" in text:
                effects["accuracy"] = _parse_stat_value(text.split(":")[-1])
            elif "회피율" in text:
                effects["avoidability"] = _parse_stat_value(text.split(":")[-1])
            elif "이동속도" in text:
                effects["speed"] = _parse_stat_value(text.split(":")[-1])
            elif "점프력" in text:
                effects["jump"] = _parse_stat_value(text.split(":")[-1])
            elif "최대HP" in text:
                effects.setdefault("max_hp", _parse_stat_value(text.split(":")[-1]))
            elif "최대MP" in text:
                effects.setdefault("max_mp", _parse_stat_value(text.split(":")[-1]))

    base.update(req)
    base["equipped_img_url"] = equipped_img_url
    base["effects"] = effects
    base["upgrade_slots"] = upgrade_slots
    return base


def _parse_consumable_etc(soup: BeautifulSoup, base: dict) -> dict:
    main_info = soup.select_one(".main-info")
    description = ""
    req_div = main_info.select_one(".req") if main_info else None
    if req_div:
        desc_parts = [_strip(h3) for h3 in req_div.select("h3")]
        description = " ".join(desc_parts).strip()
    base["description"] = description
    return base
