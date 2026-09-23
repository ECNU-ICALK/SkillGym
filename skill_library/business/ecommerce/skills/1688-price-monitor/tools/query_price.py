#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1688 价格查询工具
支持批发价格、厂家信息、一件代发价格查询
"""

import requests
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs

# 1688 API 端点
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://s.1688.com/",
}

def extract_item_id(url: str) -> Optional[str]:
    """从 URL 中提取商品 ID"""
    patterns = [
        r'offer/(\d+)\.html',
        r'offerId=(\d+)',
        r'id=(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def query_1688_price(url: str) -> Dict[str, Any]:
    """
    查询 1688 商品价格
    
    Args:
        url: 商品 URL
    
    Returns:
        商品信息字典
    """
    item_id = extract_item_id(url)
    if not item_id:
        return {"error": "无法从 URL 中提取商品 ID", "success": False}
    
    # 尝试通过移动端页面获取
    mobile_url = f"https://m.1688.com/offer/{item_id}.html"
    
    try:
        response = requests.get(mobile_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        html = response.text
        
        result = parse_1688_html(html, item_id, url)
        return result
        
    except requests.RequestException as e:
        return {
            "item_id": item_id,
            "error": f"请求失败：{str(e)}",
            "success": False,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

def parse_1688_html(html: str, item_id: str, url: str) -> Dict[str, Any]:
    """解析 1688 页面 HTML"""
    result = {
        "item_id": item_id,
        "url": url,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "success": True,
    }
    
    # 尝试从 JSON 数据中提取
    try:
        # 查找页面中的 JSON 数据
        json_match = re.search(r'window\.detailData\s*=\s*({.+?});', html)
        if json_match:
            data = json.loads(json_match.group(1))
            
            # 商品标题
            result["title"] = data.get("subject", "未知商品")
            
            # 价格信息
            price_info = data.get("priceInfo", {})
            if price_info:
                result["price_range"] = price_info.get("price", "")
                result["original_price"] = price_info.get("originalPrice", "")
            
            # 物流信息
            logistics = data.get("logistics", {})
            result["shipping"] = logistics.get("fee", "运费待议")
            
            # 销量
            result["sales"] = data.get("soldCount", "未知")
            
            # 厂家信息
            company = data.get("company", {})
            result["company_name"] = company.get("name", "未知")
            result["company_years"] = company.get("yearCount", "未知")
            
            return result
    except (json.JSONDecodeError, AttributeError) as e:
        pass
    
    # 备用：正则提取
    title_match = re.search(r'<title>([^<]+)</title>', html)
    if title_match:
        result["title"] = title_match.group(1).strip()
    
    # 价格正则
    price_match = re.search(r'"price":"([\d.-]+)"', html)
    if price_match:
        result["current_price"] = price_match.group(1)
    
    # 尝试获取价格范围
    price_range_match = re.search(r'¥([\d.]+)\s*-\s*¥([\d.]+)', html)
    if price_range_match:
        result["price_range"] = f"¥{price_range_match.group(1)} - ¥{price_range_match.group(2)}"
    
    return result

def search_1688(keyword: str, page: int = 1) -> List[Dict[str, Any]]:
    """
    搜索 1688 商品
    
    Args:
        keyword: 搜索关键词
        page: 页码
    
    Returns:
        商品列表
    """
    search_url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={keyword}&beginPage={page}"
    
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        html = response.text
        
        results = []
        
        # 提取商品列表
        item_pattern = r'href="https://detail\.1688\.com/offer/(\d+)\.html"[^>]*title="([^"]+)"'
        matches = re.findall(item_pattern, html)
        
        for item_id, title in matches[:10]:  # 限制返回 10 个
            results.append({
                "item_id": item_id,
                "title": title.replace("&quot;", '"').replace("&amp;", "&"),
                "url": f"https://detail.1688.com/offer/{item_id}.html",
            })
        
        return results
        
    except requests.RequestException as e:
        # 返回模拟数据用于演示
        return [
            {
                "item_id": "demo_001",
                "title": f"{keyword} - 厂家直销",
                "url": "https://detail.1688.com/offer/demo_001.html",
                "note": f"演示数据（请求失败：{str(e)}）",
            },
        ]

def calculate_profit(selling_price: float, cost_price: float, shipping: float = 5.0) -> Dict[str, Any]:
    """
    计算利润
    
    Args:
        selling_price: 售价
        cost_price: 成本价
        shipping: 运费
    
    Returns:
        利润分析
    """
    total_cost = cost_price + shipping
    profit = selling_price - total_cost
    profit_rate = (profit / selling_price * 100) if selling_price > 0 else 0
    
    return {
        "selling_price": selling_price,
        "cost_price": cost_price,
        "shipping": shipping,
        "total_cost": total_cost,
        "profit": profit,
        "profit_rate": f"{profit_rate:.1f}%",
    }

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
        print("""
🏭 1688 价格查询工具

用法：
  python3 query_price.py <命令> [参数]

命令：
  query <URL>          - 查询商品价格
  search <关键词>      - 搜索商品
  profit <售价> <成本> [运费]  - 计算利润

示例：
  python3 query_price.py query https://detail.1688.com/offer/123456789.html
  python3 query_price.py search "手机壳"
  python3 query_price.py profit 19.9 6.8 5
""")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == 'query':
        if len(sys.argv) < 3:
            print("请提供商品 URL")
            sys.exit(1)
        url = sys.argv[2]
        result = query_1688_price(url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif command == 'search':
        if len(sys.argv) < 3:
            print("请提供搜索关键词")
            sys.exit(1)
        keyword = sys.argv[2]
        results = search_1688(keyword)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif command == 'profit':
        if len(sys.argv) < 4:
            print("请提供售价和成本价")
            sys.exit(1)
        selling = float(sys.argv[2])
        cost = float(sys.argv[3])
        shipping = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
        result = calculate_profit(selling, cost, shipping)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        print(f"未知命令：{command}")
        print("使用 --help 查看帮助")
        sys.exit(1)

if __name__ == "__main__":
    main()
