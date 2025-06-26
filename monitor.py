#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import datetime
import json

# 从环境变量获取配置信息
DINGTALK_WEBHOOK_URL = os.getenv('DINGTALK_WEBHOOK_URL')
SENSORS_API_SECRET = os.getenv('SENSORS_API_SECRET')

# 预警阈值设置
CLICK_RATE_THRESHOLD = 10.0  # 单词-考研标签点击率同比增长率阈值（%）
CONVERSION_RATE_THRESHOLD = -40.0  # 单词考研标签转化率同比增长率阈值（%）
TRAINING_REVENUE_THRESHOLD = -10.0  # 训练营总营收同比增长率阈值（%）
TRAINING_CONVERSION_THRESHOLD = -10.0  # 训练营总转化率同比增长率阈值（%）

def send_dingtalk_alert(message):
    """发送钉钉预警消息"""
    if not DINGTALK_WEBHOOK_URL:
        print("❌ 错误：未设置DINGTALK_WEBHOOK_URL环境变量")
        return
        
    try:
        payload = {
            "msgtype": "text",
            "text": {
                "content": "【数据预警】" + message
            },
            "at": {
                "isAtAll": False
            }
        }
        
        response = requests.post(DINGTALK_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                print(f"✅ 钉钉预警发送成功: {message}")
            else:
                print(f"❌ 钉钉预警发送失败: {result.get('errmsg', '未知错误')}")
        else:
            print(f"❌ 钉钉预警请求失败，状态码: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 发送钉钉预警异常: {e}")

def get_yesterday_date():
    """获取昨天的日期，格式为YYYY-MM-DD"""
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")

def get_last_year_date():
    """获取去年同期的日期，格式为YYYY-MM-DD"""
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    last_year = yesterday.replace(year=yesterday.year - 1)
    return last_year.strftime("%Y-%m-%d")

def get_training_data():
    """获取训练营相关数据"""
    if not SENSORS_API_SECRET:
        print("❌ 错误：未设置SENSORS_API_SECRET环境变量")
        return None
        
    # 获取昨天的日期和去年同期日期
    yesterday = get_yesterday_date()
    last_year_date = get_last_year_date()
    
    # 请求的URL
    url = "https://sa.shanbay.com:8443/api/events/report"
    
    # 请求头
    headers = {
        'sensorsdata-token': SENSORS_API_SECRET,
        'Content-Type': 'application/json',
        'sensorsdata-project': 'production'
    }
    
    # 请求数据
    payload = {
        "measures": [
            {
                "event_name": "web_KY_liulan",
                "aggregator": "unique",
                "name": "考研训练营页面曝光（21～26）的用户数"
            },
            {
                "event_name": "kaoyan_paid",
                "aggregator": "unique",
                "name": "考研正课付费合集的用户数"
            },
            {
                "event_name": "kaoyan_paid",
                "aggregator": "SUM",
                "name": "训练营总营收",
                "field": "event.kaoyan_paid.amount_yuan",
                "editName": "训练营总营收"
            },
            {
                "events": ["kaoyan_paid", "web_KY_liulan"],
                "expression": "uniqcount(event.kaoyan_paid)/uniqcount(event.web_KY_liulan)|%2p",
                "format": "%2p",
                "expression_denominator_without_group": False,
                "name": "训练营总转化率",
                "subjectIdIsUserId": False,
                "expression_filters": [{}, {}],
                "editName": "训练营总转化率"
            }
        ],
        "from_date": yesterday,
        "to_date": yesterday,
        "unit": "day",
        "detail_and_rollup": True,
        "enable_detail_follow_rollup_by_values_rank": True,
        "sub_task_type": "SEGMENTATION",
        "time_zone_mode": "",
        "server_time_zone": "",
        "bookmarkid": "38142",
        "fromDash": {"id": 3083, "type": "normal", "size": "normal"},
        "compare_to_date": last_year_date,
        "rangeText": "1 day",
        "compareKey": "last year",
        "compare_from_date": last_year_date,
        "use_cache": True
    }
    
    try:
        # 发送请求
        print(f"正在获取训练营数据 {yesterday} 与 {last_year_date} 的同比数据...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # 检查响应状态码
        if response.status_code != 200:
            print(f"训练营数据请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
        
        # 解析JSON响应
        data = response.json()
        
        # 指标名称映射
        metric_names = [
            "考研训练营页面曝光（21～26）的用户数",
            "考研正课付费合集的用户数",
            "训练营总营收",
            "训练营总转化率"
        ]
        
        # 从返回的数据中解析所有指标的当期和同期数据
        try:
            # 当期数据（昨天）
            current_values = data[0]['detail_result']['rows'][0]['values'][0]
            # 同期数据（去年同期）
            compare_values = data[1]['detail_result']['rows'][0]['values'][0]
            
            results = []
            for i, metric_name in enumerate(metric_names):
                current_value = current_values[i]
                compare_value = compare_values[i]
                
                # 计算同比增长率
                if compare_value != 0:
                    growth_rate = ((current_value - compare_value) / compare_value) * 100
                else:
                    growth_rate = 0 if current_value == 0 else float('inf')
                
                results.append({
                    'metric': metric_name,
                    'current': current_value,
                    'compare': compare_value,
                    'growth_rate': growth_rate
                })
            
            return {
                'current_date': yesterday,
                'compare_date': last_year_date,
                'metrics': results
            }
        except (KeyError, IndexError, TypeError) as e:
            print(f"解析训练营数据失败: {e}")
            print(f"返回的数据结构: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"训练营数据网络请求异常: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"训练营数据JSON解析失败: {e}")
        print(f"响应内容: {response.text}")
        return None
    except Exception as e:
        print(f"训练营数据未知错误: {e}")
        return None

def get_dau_data():
    """获取DAU及其他指标的同比数据"""
    if not SENSORS_API_SECRET:
        print("❌ 错误：未设置SENSORS_API_SECRET环境变量")
        return None
        
    # 获取昨天的日期和去年同期日期
    yesterday = get_yesterday_date()
    last_year_date = get_last_year_date()
    
    # 请求的URL
    url = "https://sa.shanbay.com:8443/api/events/report"
    
    # 请求头
    headers = {
        'sensorsdata-token': SENSORS_API_SECRET,
        'Content-Type': 'application/json',
        'sensorsdata-project': 'production'
    }
    
    # 请求数据
    payload = {
        "measures": [
            {
                "event_name": "$AppStart",
                "aggregator": "unique",
                "name": "App 启动的用户数",
                "filter": {
                    "conditions": [
                        {
                            "field": "event.$Anything.$app_name",
                            "function": "equal",
                            "params": ["扇贝单词英语版", "扇贝单词"],
                            "$$searchValue": "应用名称",
                            "$$render_index": 1
                        }
                    ]
                }
            },
            {
                "event_name": "web_KY_liulan",
                "aggregator": "unique",
                "name": "考研训练营页面曝光（21～26）的用户数",
                "filter": {
                    "conditions": [
                        {
                            "field": "event.$Anything.$app_name",
                            "function": "equal",
                            "params": ["扇贝单词英语版", "扇贝单词"],
                            "$$searchValue": "应用名称",
                            "$$render_index": 1
                        }
                    ]
                }
            },
            {
                "event_name": "kaoyan_paid",
                "aggregator": "unique",
                "name": "考研正课付费合集的用户数",
                "filter": {
                    "conditions": [
                        {
                            "field": "event.$Anything.$app_name",
                            "function": "equal",
                            "params": ["扇贝单词英语版", "扇贝单词"],
                            "$$searchValue": "应用名称",
                            "$$render_index": 1
                        }
                    ]
                }
            },
            {
                "events": ["web_KY_liulan", "$AppStart"],
                "expression": "uniqcount(event.web_KY_liulan)/uniqcount(event.$AppStart)|%2p",
                "format": "%2p",
                "expression_denominator_without_group": False,
                "name": "单词-考研标签点击率",
                "subjectIdIsUserId": False,
                "editName": "单词-考研标签点击率",
                "expression_filters": [
                    {
                        "conditions": [
                            {
                                "field": "event.$Anything.$app_name",
                                "function": "equal",
                                "params": ["扇贝单词英语版", "扇贝单词"],
                                "$$searchValue": "应用名称",
                                "$$render_index": 0
                            }
                        ]
                    },
                    {
                        "conditions": [
                            {
                                "field": "event.$Anything.$app_name",
                                "function": "equal",
                                "params": ["扇贝单词英语版", "扇贝单词"],
                                "$$searchValue": "应用名称",
                                "$$render_index": 0
                            }
                        ]
                    }
                ]
            },
            {
                "events": ["kaoyan_paid", "web_KY_liulan"],
                "expression": "uniqcount(event.kaoyan_paid)/uniqcount(event.web_KY_liulan)|%2p",
                "format": "%2p",
                "expression_denominator_without_group": False,
                "name": "单词考研标签转化率",
                "subjectIdIsUserId": False,
                "editName": "单词考研标签转化率",
                "expression_filters": [
                    {
                        "conditions": [
                            {
                                "field": "event.$Anything.$app_name",
                                "function": "equal",
                                "params": ["扇贝单词英语版", "扇贝单词"],
                                "$$searchValue": "应用名称",
                                "$$render_index": 0
                            }
                        ]
                    },
                    {
                        "conditions": [
                            {
                                "field": "event.$Anything.$app_name",
                                "function": "equal",
                                "params": ["扇贝单词英语版", "扇贝单词"],
                                "$$searchValue": "应用名称",
                                "$$render_index": 0
                            }
                        ]
                    }
                ]
            }
        ],
        "from_date": yesterday,
        "to_date": yesterday,
        "unit": "day",
        "detail_and_rollup": True,
        "enable_detail_follow_rollup_by_values_rank": True,
        "sub_task_type": "SEGMENTATION",
        "time_zone_mode": "",
        "server_time_zone": "",
        "compare_to_date": last_year_date,
        "compareKey": "last year",
        "filter": {
            "conditions": [
                {
                    "field": "user.user_group_dchykyyhryj@dynamic",
                    "function": "isTrue",
                    "params": [],
                    "$$searchValue": "单词-活跃考研用户real-永久",
                    "$$render_index": 1
                }
            ]
        },
        "bookmarkid": "38153",
        "fromDash": {"id": 2820, "type": "normal", "size": "normal"},
        "rangeText": "1 day",
        "compare_from_date": last_year_date,
        "use_cache": True
    }
    
    try:
        # 发送请求
        print(f"正在获取单词数据 {yesterday} 与 {last_year_date} 的同比数据...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # 检查响应状态码
        if response.status_code != 200:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            # 发送钉钉预警
            send_dingtalk_alert("获取神策数据失败，请检查脚本！")
            return None
        
        # 解析JSON响应
        data = response.json()
        
        # 指标名称映射
        metric_names = [
            "App 启动的用户数",
            "考研训练营页面曝光（21～26）的用户数", 
            "考研正课付费合集的用户数",
            "单词-考研标签点击率",
            "单词考研标签转化率"
        ]
        
        # 从返回的数据中解析所有指标的当期和同期数据
        try:
            # 当期数据（昨天）
            current_values = data[0]['detail_result']['rows'][0]['values'][0]
            # 同期数据（去年同期）
            compare_values = data[1]['detail_result']['rows'][0]['values'][0]
            
            results = []
            for i, metric_name in enumerate(metric_names):
                current_value = current_values[i]
                compare_value = compare_values[i]
                
                # 计算同比增长率
                if compare_value != 0:
                    growth_rate = ((current_value - compare_value) / compare_value) * 100
                else:
                    growth_rate = 0 if current_value == 0 else float('inf')
                
                results.append({
                    'metric': metric_name,
                    'current': current_value,
                    'compare': compare_value,
                    'growth_rate': growth_rate
                })
            
            return {
                'current_date': yesterday,
                'compare_date': last_year_date,
                'metrics': results
            }
        except (KeyError, IndexError, TypeError) as e:
            print(f"解析数据失败: {e}")
            print(f"返回的数据结构: {json.dumps(data, indent=2, ensure_ascii=False)}")
            # 发送钉钉预警
            send_dingtalk_alert("获取神策数据失败，请检查脚本！")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"网络请求异常: {e}")
        # 发送钉钉预警
        send_dingtalk_alert("获取神策数据失败，请检查脚本！")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        print(f"响应内容: {response.text}")
        # 发送钉钉预警
        send_dingtalk_alert("获取神策数据失败，请检查脚本！")
        return None
    except Exception as e:
        print(f"未知错误: {e}")
        # 发送钉钉预警
        send_dingtalk_alert("获取神策数据失败，请检查脚本！")
        return None

def check_all_metrics_and_alert(word_results, training_results):
    """检查所有关键指标并发送预警"""
    # 检查单词相关指标
    if word_results:
        click_rate_metric = None
        conversion_rate_metric = None
        
        # 找到对应的指标
        for metric in word_results['metrics']:
            if "单词-考研标签点击率" in metric['metric']:
                click_rate_metric = metric
            elif "单词考研标签转化率" in metric['metric']:
                conversion_rate_metric = metric
        
        # 检查单词-考研标签点击率同比
        if click_rate_metric:
            growth_rate = click_rate_metric['growth_rate']
            if growth_rate != float('inf') and growth_rate < CLICK_RATE_THRESHOLD:
                deficit = CLICK_RATE_THRESHOLD - growth_rate
                alert_message = f"单词-考研标签点击率同比增长为 {growth_rate:.2f}%，低于阈值 {deficit:.2f}个百分点，请关注！"
                send_dingtalk_alert(alert_message)
            else:
                print(f"单词-考研标签点击率同比正常: {growth_rate:.2f}%")
        
        # 检查单词考研标签转化率同比
        if conversion_rate_metric:
            growth_rate = conversion_rate_metric['growth_rate']
            if growth_rate != float('inf') and growth_rate < CONVERSION_RATE_THRESHOLD:
                deficit = CONVERSION_RATE_THRESHOLD - growth_rate
                alert_message = f"单词考研标签转化率同比增长为 {growth_rate:.2f}%，低于阈值 {deficit:.2f}个百分点，请关注！"
                send_dingtalk_alert(alert_message)
            else:
                print(f"单词考研标签转化率同比正常: {growth_rate:.2f}%")
    
    # 检查训练营相关指标
    if training_results:
        training_revenue_metric = None
        training_conversion_metric = None
        
        # 找到对应的指标
        for metric in training_results['metrics']:
            if "训练营总营收" in metric['metric']:
                training_revenue_metric = metric
            elif "训练营总转化率" in metric['metric']:
                training_conversion_metric = metric
        
        # 检查训练营总营收同比
        if training_revenue_metric:
            growth_rate = training_revenue_metric['growth_rate']
            if growth_rate != float('inf') and growth_rate < TRAINING_REVENUE_THRESHOLD:
                deficit = TRAINING_REVENUE_THRESHOLD - growth_rate
                alert_message = f"训练营总营收同比增长为 {growth_rate:.2f}%，低于阈值 {deficit:.2f}个百分点，请关注！"
                send_dingtalk_alert(alert_message)
            else:
                print(f"训练营总营收同比正常: {growth_rate:.2f}%")
        
        # 检查训练营总转化率同比
        if training_conversion_metric:
            growth_rate = training_conversion_metric['growth_rate']
            if growth_rate != float('inf') and growth_rate < TRAINING_CONVERSION_THRESHOLD:
                deficit = TRAINING_CONVERSION_THRESHOLD - growth_rate
                alert_message = f"训练营总转化率同比增长为 {growth_rate:.2f}%，低于阈值 {deficit:.2f}个百分点，请关注！"
                send_dingtalk_alert(alert_message)
            else:
                print(f"训练营总转化率同比正常: {growth_rate:.2f}%")

def format_value(value, is_percentage=False, is_currency=False):
    """格式化数值显示"""
    if is_percentage:
        return f"{value}%"
    elif is_currency:
        return f"¥{value:,.2f}"
    elif isinstance(value, float):
        return f"{value:,.2f}"
    else:
        return f"{value:,}"

def print_results(results, title="数据报告"):
    """格式化打印结果"""
    if not results:
        return
    
    print(f"\n📊 {title} - {results['current_date']} 与 {results['compare_date']} 同比数据")
    print("=" * 80)
    
    for metric in results['metrics']:
        metric_name = metric['metric']
        current = metric['current']
        compare = metric['compare']
        growth_rate = metric['growth_rate']
        
        # 判断数值类型
        is_percentage = '率' in metric_name
        is_currency = '营收' in metric_name
        
        print(f"\n📈 {metric_name}:")
        print(f"   当期 ({results['current_date']}): {format_value(current, is_percentage, is_currency)}")
        print(f"   同期 ({results['compare_date']}): {format_value(compare, is_percentage, is_currency)}")
        
        if growth_rate == float('inf'):
            print(f"   同比增长: +∞% (去年同期为0)")
        elif growth_rate >= 0:
            print(f"   同比增长: +{growth_rate:.2f}%")
        else:
            print(f"   同比增长: {growth_rate:.2f}%")

def main():
    """主函数"""
    yesterday = get_yesterday_date()
    last_year_date = get_last_year_date()
    print(f"查询日期: {yesterday} (同比 {last_year_date})")
    print(f"预警阈值设置:")
    print(f"  - 单词-考研标签点击率同比: < {CLICK_RATE_THRESHOLD}%")
    print(f"  - 单词考研标签转化率同比: < {CONVERSION_RATE_THRESHOLD}%")
    print(f"  - 训练营总营收同比: < {TRAINING_REVENUE_THRESHOLD}%")
    print(f"  - 训练营总转化率同比: < {TRAINING_CONVERSION_THRESHOLD}%")
    
    # 获取同比数据
    word_results = get_dau_data()
    training_results = get_training_data()
    
    # 检查指标并发送预警
    check_all_metrics_and_alert(word_results, training_results)
    
    # 打印结果
    if word_results:
        print(f"\n✅ 成功获取单词相关数据")
        print_results(word_results, "单词相关指标")
    else:
        print(f"\n❌ 获取单词相关数据失败")
    
    if training_results:
        print(f"\n✅ 成功获取训练营相关数据")
        print_results(training_results, "训练营相关指标")
    else:
        print(f"\n❌ 获取训练营相关数据失败")

if __name__ == "__main__":
    main() 