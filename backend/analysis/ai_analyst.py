from openai import OpenAI
import anthropic
from typing import Dict, Optional
import json
from datetime import datetime
import logging

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class AIAnalyst:
    """AI-powered market analysis using Claude or DeepSeek API"""

    ANALYSIS_PROMPT = """你是一位专业的宏观经济分析师和投资策略师。请基于以下市场数据、技术指标和新闻信息，提供全面的分析报告。

## 当前市场数据
{market_data}

## 技术分析指标
{technical_data}

## 宏观经济指标
{macro_data}

## 近期新闻摘要
{news_summary}

## 历史预测表现反馈
{accuracy_feedback}

请提供以下分析：

1. **地缘政治风险评估** (0-100分)
   - 当前主要地缘政治风险
   - 对市场的潜在影响

2. **美联储政策走向分析**
   - 当前货币政策立场
   - 未来利率走势预判
   - 对各类资产的影响

3. **科技/AI发展趋势**
   - 对科技股的影响
   - 投资机会和风险

4. **市场情绪判断**
   - 当前市场情绪（贪婪/恐惧）
   - 短期市场方向预判

5. **资产配置建议**
   - 推荐的资产权重调整（请给出具体数值）
   - 具体理由

请以JSON格式返回分析结果。注意 adjustments 字段请返回具体的调整幅度数值（-0.10 到 +0.10），例如 0.05 表示增加5%权重，-0.03 表示减少3%权重：

{{
    "geopolitical_risk": {{
        "score": 0-100,
        "key_risks": ["风险1", "风险2"],
        "analysis": "详细分析..."
    }},
    "fed_policy": {{
        "stance": "hawkish/neutral/dovish",
        "rate_outlook": "up/stable/down",
        "analysis": "详细分析..."
    }},
    "tech_trend": {{
        "outlook": "bullish/neutral/bearish",
        "key_factors": ["因素1", "因素2"],
        "analysis": "详细分析..."
    }},
    "market_sentiment": {{
        "level": "extreme_fear/fear/neutral/greed/extreme_greed",
        "score": 0-100,
        "short_term_outlook": "详细分析..."
    }},
    "allocation_advice": {{
        "adjustments": {{
            "SPY": 0.00,
            "QQQ": 0.00,
            "GLD": 0.00,
            "BTC-USD": 0.00,
            "TLT": 0.00,
            "CASH": 0.00
        }},
        "reasoning": "调整理由...",
        "risk_level": "conservative/moderate/aggressive"
    }},
    "overall_risk_score": 0-100,
    "summary": "一段话总结当前市场环境和投资建议"
}}
"""

    def __init__(self):
        self.provider = settings.ai_provider
        self.client = None
        self.model = None

        if self.provider == "deepseek" and settings.deepseek_api_key:
            self.client = OpenAI(
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
            self.model = "deepseek-chat"
        elif self.provider == "anthropic" and settings.anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            self.model = "claude-3-5-sonnet-20241022"  # 使用稳定版本

    def _format_accuracy_feedback(self, stats: Optional[Dict]) -> str:
        """
        P4: 格式化历史预测准确率反馈

        将历史准确率数据转换为AI可理解的反馈，帮助模型调整预测倾向
        """
        if not stats or stats.get("evaluated", 0) == 0:
            return "暂无历史预测数据，这是首次分析。"

        feedback_parts = []

        # 总体准确率
        overall_acc = stats.get("accuracy")
        evaluated = stats.get("evaluated", 0)
        if overall_acc is not None:
            feedback_parts.append(
                f"过去30天共进行了 {evaluated} 次预测评估，"
                f"总体准确率为 {overall_acc * 100:.1f}%。"
            )

            # 根据准确率给出建议
            if overall_acc < 0.4:
                feedback_parts.append(
                    "⚠️ 历史预测准确率较低，建议采取更保守的调整幅度，"
                    "减少激进判断，增加 CASH 和 TLT 等安全资产权重。"
                )
            elif overall_acc < 0.5:
                feedback_parts.append(
                    "⚠️ 历史预测表现一般，建议降低单次调整幅度至 ±3% 以内。"
                )
            elif overall_acc > 0.6:
                feedback_parts.append(
                    "✓ 历史预测表现良好，可以维持正常调整幅度。"
                )

        # 按资产准确率反馈
        by_asset = stats.get("by_asset", {})
        if by_asset:
            weak_assets = []
            strong_assets = []
            for asset, asset_stats in by_asset.items():
                acc = asset_stats.get("accuracy", 0)
                total = asset_stats.get("total", 0)
                if total >= 3:  # 至少3次预测才有参考意义
                    if acc < 0.4:
                        weak_assets.append(f"{asset}({acc * 100:.0f}%)")
                    elif acc > 0.6:
                        strong_assets.append(f"{asset}({acc * 100:.0f}%)")

            if weak_assets:
                feedback_parts.append(
                    f"预测准确率较低的资产: {', '.join(weak_assets)}。"
                    "对这些资产应更谨慎，倾向于 'maintain' 或小幅调整。"
                )
            if strong_assets:
                feedback_parts.append(
                    f"预测表现较好的资产: {', '.join(strong_assets)}。"
                )

        # 按方向准确率反馈
        by_direction = stats.get("by_direction", {})
        if by_direction:
            for direction, dir_stats in by_direction.items():
                acc = dir_stats.get("accuracy", 0)
                total = dir_stats.get("total", 0)
                if total >= 5:  # 至少5次预测
                    dir_name = {"increase": "增加", "decrease": "减少", "maintain": "维持"}.get(direction, direction)
                    if acc < 0.4:
                        feedback_parts.append(
                            f"'{dir_name}'方向预测准确率仅 {acc * 100:.0f}%，建议减少此类预测。"
                        )

        return "\n".join(feedback_parts) if feedback_parts else "历史预测数据不足，暂无反馈。"

    async def analyze(
        self,
        market_data: Dict,
        macro_data: Dict,
        news_summary: Dict,
        technical_data: Optional[Dict] = None,  # P1: 添加技术指标
        accuracy_stats: Optional[Dict] = None  # P4: 历史准确率反馈
    ) -> Dict:
        """Run comprehensive AI analysis on market data"""
        if not self.client:
            return self._get_mock_analysis()

        # P1: 格式化技术指标数据
        tech_str = "暂无技术指标数据"
        if technical_data:
            tech_str = json.dumps(technical_data, indent=2, ensure_ascii=False)

        # P4: 格式化历史准确率反馈
        accuracy_str = self._format_accuracy_feedback(accuracy_stats)

        prompt = self.ANALYSIS_PROMPT.format(
            market_data=json.dumps(market_data, indent=2, ensure_ascii=False),
            technical_data=tech_str,
            macro_data=json.dumps(macro_data, indent=2, ensure_ascii=False),
            news_summary=json.dumps(news_summary, indent=2, ensure_ascii=False),
            accuracy_feedback=accuracy_str
        )

        try:
            if self.provider == "deepseek":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4096,
                    temperature=0.7
                )
                response_text = response.choices[0].message.content
            else:
                # Anthropic
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = message.content[0].text

            # Extract JSON from response with robust parsing
            analysis = self._extract_json_from_response(response_text)
            if analysis is None:
                logger.warning("Failed to parse AI response, using mock")
                return self._get_mock_analysis()

            analysis["timestamp"] = datetime.now().isoformat()
            analysis["model"] = self.model
            analysis["provider"] = self.provider
            return analysis

        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return self._get_mock_analysis()

    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """
        从AI响应中提取JSON，支持多种格式

        尝试顺序：
        1. ```json ... ``` 代码块
        2. ``` ... ``` 代码块
        3. 直接解析整个响应
        4. 查找 { ... } 边界
        """
        import re

        # 尝试 ```json 代码块
        if "```json" in response_text:
            try:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                pass

        # 尝试 ``` 代码块
        if "```" in response_text:
            try:
                json_str = response_text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                pass

        # 尝试直接解析
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass

        # 查找 JSON 对象边界
        try:
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response_text[start:end + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        return None

    def _get_mock_analysis(self) -> Dict:
        """Return mock analysis when API is not available"""
        return {
            "geopolitical_risk": {
                "score": 45,
                "key_risks": ["中美关系紧张", "中东局势不稳", "欧洲能源问题"],
                "analysis": "地缘政治风险处于中等水平，需关注贸易政策变化"
            },
            "fed_policy": {
                "stance": "hawkish",
                "rate_outlook": "stable",
                "analysis": "美联储维持高利率环境，但加息周期接近尾声"
            },
            "tech_trend": {
                "outlook": "bullish",
                "key_factors": ["AI发展迅速", "云计算增长", "半导体需求强劲"],
                "analysis": "科技板块受AI热潮推动，但估值偏高需谨慎"
            },
            "market_sentiment": {
                "level": "greed",
                "score": 65,
                "short_term_outlook": "市场情绪偏乐观，但需警惕回调风险"
            },
            "allocation_advice": {
                "adjustments": {
                    "SPY": -0.02,
                    "QQQ": -0.03,
                    "GLD": 0.05,
                    "BTC-USD": -0.04,
                    "TLT": 0.03,
                    "CASH": 0.01
                },
                "reasoning": "建议增加防御性资产配置，减少高波动资产。黄金和国债可对冲地缘政治风险，降低比特币敞口以控制波动。",
                "risk_level": "moderate"
            },
            "overall_risk_score": 55,
            "summary": "当前市场处于高利率环境，科技股表现强劲但估值偏高。建议保持均衡配置，适当增加黄金和债券以对冲潜在风险。",
            "timestamp": datetime.now().isoformat(),
            "is_mock": True
        }

    async def get_allocation_recommendation(self, analysis: Dict) -> Dict[str, float]:
        """Convert AI analysis into specific allocation weights"""
        advice = analysis.get("allocation_advice", {})
        adjustments = advice.get("adjustments", {})
        risk_level = advice.get("risk_level", "moderate")

        # Base allocations based on risk level
        base_allocations = {
            "conservative": {
                "SPY": 0.20, "QQQ": 0.10, "GLD": 0.15,
                "BTC-USD": 0.05, "TLT": 0.30, "CASH": 0.20
            },
            "moderate": {
                "SPY": 0.30, "QQQ": 0.20, "GLD": 0.10,
                "BTC-USD": 0.10, "TLT": 0.20, "CASH": 0.10
            },
            "aggressive": {
                "SPY": 0.35, "QQQ": 0.30, "GLD": 0.05,
                "BTC-USD": 0.15, "TLT": 0.10, "CASH": 0.05
            }
        }

        allocation = base_allocations.get(risk_level, base_allocations["moderate"]).copy()

        # Apply adjustments - 支持字符串和数值两种格式
        legacy_values = {"increase": 0.05, "maintain": 0, "decrease": -0.05}
        for asset, adjustment in adjustments.items():
            if asset in allocation:
                # 判断调整值类型
                if isinstance(adjustment, str):
                    adj_value = legacy_values.get(adjustment, 0)
                elif isinstance(adjustment, (int, float)):
                    adj_value = float(adjustment)
                else:
                    adj_value = 0

                allocation[asset] += adj_value
                allocation[asset] = max(
                    settings.assets[asset]["min_weight"],
                    min(settings.assets[asset]["max_weight"], allocation[asset])
                )

        # Normalize to sum to 1
        total = sum(allocation.values())
        allocation = {k: round(v / total, 4) for k, v in allocation.items()}

        return allocation

    # 大师视角分析的详细 prompt 模板
    MASTER_PERSPECTIVES_PROMPT = """你需要扮演两位投资大师，对以下资产配置方案进行深度分析和点评。

## 当前资产配置
{allocation}

## 市场数据
{market_data}

## 宏观环境
{macro_data}

---

# 塔勒布视角分析

## 塔勒布核心思维框架（必须运用）：

1. **非对称风险思维**：永远先看下行风险的代价。在Extremistan里，一个极端事件可以主宰一切。不问「最可能发生什么」，问「最坏能坏到什么程度，我能承受吗」。

2. **反脆弱偏好**：三个层级——脆弱（被波动伤害）→ 鲁棒（不受影响）→ 反脆弱（从波动中获益）。评估这个配置：波动性增加时会变好还是变差？

3. **Skin in the Game检验**：谁在承担风险？如果配置者的利益和组合不对齐，观点打五折。

4. **杠铃策略**：90%极度保守 + 10%极度冒险。中间地带是最危险的位置——看似安全，实则在积累隐性尾部风险。

5. **遍历性检验**：100人去赌场和1人去赌场100次完全不同。问：这个策略重复一万次，会在某一次彻底出局吗？

6. **火鸡问题**：过去的稳定不能预测未来。火鸡在感恩节前每天都很快乐。

## 塔勒布表达风格：
- 格言体为主，一句话一个段落，不解释
- 先砸结论，不铺垫
- 确定性极高，很少说「我不确定」
- 用古典引用（汉谟拉比法典、Seneca）
- 攻击性是feature不是bug
- 用「OK?」结尾表示居高临下的教师口吻
- 自创术语：IYI、Fragilista、Mediocristan/Extremistan

---

# 芒格视角分析

## 芒格核心思维框架（必须运用）：

1. **逆向思考**：不问「这个配置的好处是什么」，先问「这个配置怎么会让我亏光」。避开所有灾难路径。"All I want to know is where I'm going to die, so I'll never go there."

2. **Lollapalooza效应**：多种心理偏误同时发力、相互强化，产生极端非线性结果。检测：社会认同（别人都在买）+ 过度乐观（只涨不跌）+ 被剥夺超级反应（FOMO）= 危险。

3. **能力圈纪律**：知道自己不知道什么。"I never allow myself to have an opinion on anything that I don't know the other side's argument better than they do."

4. **激励机制决定一切**：不要听他说什么，看他被什么奖励。"Show me the incentive and I'll show you the outcome."

5. **三筐分类法**：Yes（确信）、No（确信不做）、Too Hard（太复杂，放弃）。大部分事情属于第三筐。

6. **葡萄干与粪便法则**：如果其中有一个致命缺陷，整体就是有毒的。"If you mix raisins with turds, they're still turds."

## 芒格表达风格：
- 极短句优先，一个判断用一句话
- 否定句 > 肯定句
- 不铺垫，先给结论
- 极端词不回避：stupid、evil、insanity
- 干燥幽默（dry humor）：用严肃语气说荒诞内容
- 经典回应："I have nothing to add." / "It's outside my circle of competence."
- 向下类比：粪便、老鼠药、看牙医

---

请以JSON格式返回分析结果：
{{
    "taleb": {{
        "verdict": "反脆弱/脆弱/中性",
        "risk_score": 0-100,
        "key_concerns": ["尾部风险关注点1", "关注点2", "关注点3"],
        "analysis": "详细分析（200-300字，用塔勒布的语气和思维框架）",
        "barbell_suggestion": "杠铃策略建议"
    }},
    "munger": {{
        "verdict": "明智/愚蠢/需要更多思考",
        "confidence": 0-100,
        "cognitive_biases": ["可能存在的认知偏误1", "偏误2"],
        "analysis": "详细分析（200-300字，用芒格的语气和逆向思考）",
        "inversion": "逆向思考：怎样会让这个配置失败？"
    }},
    "consensus": {{
        "agree_on": ["两位大师都同意的点"],
        "disagree_on": ["两位大师观点不同的点"],
        "final_advice": "综合建议（一句话）"
    }}
}}
"""

    async def analyze_master_perspectives(
        self,
        allocation: Dict[str, float],
        market_data: Dict,
        macro_data: Dict
    ) -> Dict:
        """
        使用塔勒布和芒格的完整思维框架分析当前资产配置
        """
        if not self.client:
            return self._get_mock_master_perspectives(allocation)

        prompt = self.MASTER_PERSPECTIVES_PROMPT.format(
            allocation=json.dumps(allocation, indent=2, ensure_ascii=False),
            market_data=json.dumps(market_data, indent=2, ensure_ascii=False),
            macro_data=json.dumps(macro_data, indent=2, ensure_ascii=False)
        )

        try:
            if self.provider == "deepseek":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2048,
                    temperature=0.8
                )
                response_text = response.choices[0].message.content
            else:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = message.content[0].text

            result = self._extract_json_from_response(response_text)
            if result is None:
                logger.warning("Failed to parse master perspectives response")
                return self._get_mock_master_perspectives(allocation)

            result["timestamp"] = datetime.now().isoformat()
            result["provider"] = self.provider
            return result

        except Exception as e:
            logger.error(f"Master perspectives analysis error: {e}")
            return self._get_mock_master_perspectives(allocation)

    def _get_mock_master_perspectives(self, allocation: Dict) -> Dict:
        """返回模拟的大师视角分析"""
        btc_weight = allocation.get("BTC-USD", 0)
        stock_weight = allocation.get("SPY", 0) + allocation.get("QQQ", 0)

        return {
            "taleb": {
                "verdict": "脆弱" if btc_weight > 0.15 else "中性",
                "risk_score": 65,
                "key_concerns": [
                    "加密货币敞口存在遍历性风险",
                    "科技股集中度可能导致尾部损失",
                    "缺乏真正的反脆弱资产"
                ],
                "analysis": "让我直说：你的组合在Extremistan里玩Mediocristan的游戏。"
                           f"BTC占{btc_weight*100:.0f}%——这不是投资，这是赌博。"
                           "一个真正的杠铃策略应该是90%在最安全的资产，10%在最疯狂的赌注。"
                           "你现在是中间地带，最脆弱的位置。记住：火鸡在感恩节前的每一天都很快乐。",
                "barbell_suggestion": f"建议：将CASH提高到20%，TLT提高到30%，BTC保留但控制在5%以内。"
            },
            "munger": {
                "verdict": "需要更多思考",
                "confidence": 55,
                "cognitive_biases": [
                    "近因偏误 - 可能过度基于近期表现",
                    "社会认同 - AI/科技热潮影响",
                    "过度自信 - 对模型优化的信任"
                ],
                "analysis": f"股票占{stock_weight*100:.0f}%，问题不在于多少，而在于你是否理解你买的是什么。"
                           "大多数人买QQQ是因为别人在赚钱，这是最蠢的理由。"
                           "我的问题是：如果科技股跌50%，你能说出为什么吗？如果不能，你就在能力圈外面。",
                "inversion": "逆向思考：这个配置在以下情况会失败：1)利率持续上升 2)AI泡沫破裂 3)地缘冲突升级。你对这三种情况有对冲吗？"
            },
            "consensus": {
                "agree_on": [
                    "当前配置缺乏足够的防御性",
                    "需要更清晰地认识风险来源"
                ],
                "disagree_on": [
                    "塔勒布倾向极端杠铃，芒格更看重理解能力圈"
                ],
                "final_advice": "减少投机敞口，增加你真正理解的资产，保持足够现金以应对黑天鹅。"
            },
            "timestamp": datetime.now().isoformat(),
            "is_mock": True
        }
