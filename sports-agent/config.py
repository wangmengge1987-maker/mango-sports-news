# -*- coding: utf-8 -*-
"""体育新闻源配置 — 数据源、API、推送"""

from datetime import timedelta

# ─── 关注分类 ──────────────────────────────────────────────
CATEGORIES = {
    "NBA": {
        "keywords": [
            "NBA",
            "Lakers", "Warriors", "Celtics", "Nuggets", "Heat", "Bucks", "Suns",
            "Clippers", "Mavericks", "Knicks", "76ers", "Thunder", "Timberwolves",
            "Pelicans", "Kings", "Pacers", "Cavaliers", "Magic", "Rockets",
            "Trail Blazers", "Jazz", "Grizzlies", "Hornets", "Wizards", "Raptors",
            "Bulls", "Pistons", "Hawks",
            "湖人", "勇士", "凯尔特人", "掘金", "热火", "雄鹿", "太阳", "快船", "独行侠",
            "东契奇", "詹姆斯", "库里", "杜兰特", "字母哥", "约基奇",
        ]
    },
    "CBA": {
        "keywords": [
            "CBA",
            "辽宁", "广东", "新疆", "浙江", "广厦",
            "北京首钢", "上海久事", "龙狮", "深圳", "山东", "青岛",
            "北控", "吉林", "山西", "天津", "福建", "江苏", "四川", "宁波",
        ]
    },
    "英超": {
        "keywords": [
            "英超", "Premier League",
            "Manchester City", "Manchester United", "Liverpool", "Arsenal", "Chelsea",
            "Tottenham", "Newcastle", "Aston Villa", "West Ham", "Brighton",
            "Wolves", "Everton", "Crystal Palace", "Fulham", "Brentford",
            "Nottingham Forest", "Bournemouth",
            "曼城", "阿森纳", "利物浦", "曼联", "切尔西", "热刺", "纽卡斯尔",
            "哈兰德", "萨拉赫", "德布劳内",
        ]
    },
    "中超": {
        "keywords": [
            "中超", "Chinese Super League",
            "上海海港", "山东泰山", "北京国安", "成都蓉城", "上海申花",
            "浙江队", "天津津门虎", "长春亚泰", "河南队", "梅州客家",
            "青岛海牛", "南通支云", "大连人", "深圳队", "沧州雄狮", "武汉三镇",
        ]
    },
    "伤病": {
        "keywords": [
            "受伤", "伤病", "报销", "缺阵", "复出", "手术", "韧带", "肌肉", "骨折",
            "injury", "injured", "out for", "sidelined", "surgery", "torn", "strain",
            "sprain", "fracture", "hamstring", "ACL", "MCL",
        ]
    },
    "转会": {
        "keywords": [
            "转会", "签约", "续约", "加盟", "离队", "交易", "选秀", "自由球员",
            "transfer", "sign", "signing", "contract", "extend", "extension",
            "trade", "draft", "free agent", "loan", "move to", "join", "leave",
        ]
    },
}

# ─── RSS 数据源 ────────────────────────────────────────────
RSS_SOURCES = [
    {"name": "ESPN NBA",       "url": "https://www.espn.com/espn/rss/nba/news",       "hint": "NBA",  "lang": "en"},
    {"name": "ESPN Soccer",    "url": "https://www.espn.com/espn/rss/soccer/news",    "hint": "足球",  "lang": "en"},
    {"name": "BBC Sport",      "url": "http://feeds.bbci.co.uk/sport/rss.xml",        "hint": "综合",  "lang": "en"},
    {"name": "Sky Sports NBA", "url": "https://www.skysports.com/rss/12040",          "hint": "NBA",  "lang": "en"},
    {"name": "Sky Sports Football", "url": "https://www.skysports.com/rss/11095",     "hint": "足球",  "lang": "en"},
    {"name": "The Guardian Sport",  "url": "https://www.theguardian.com/uk/sport/rss","hint": "综合",  "lang": "en"},
    # 中文源（部分可能不稳定，视网络环境启用）
    {"name": "新浪体育 NBA",   "url": "https://rss.sina.com.cn/sports/basketball/nba.xml",    "hint": "NBA", "lang": "zh"},
    {"name": "新浪体育 综合",  "url": "https://rss.sina.com.cn/sports/general.xml",            "hint": "综合", "lang": "zh"},
]

# ─── 赛事比分 API（ESPN 公开接口，无需 Key）───────────────
SCORE_SOURCES = {
    "NBA": {
        "url": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
        "enabled": True,
    },
    "英超": {
        "url": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
        "enabled": True,
    },
    "中超": {
        "url": "https://site.api.espn.com/apis/site/v2/sports/soccer/chn.1/scoreboard",
        "enabled": True,
    },
    # CBA 暂无全球免费接口，后期可通过国内 API 接入
    "CBA": {"enabled": False},
}

# ─── 推送配置（PushPlus：pushplus.plus）───────────────────
# 优先从环境变量读取，如未设置则尝试改配置文件中的占位
PUSHPLUS_TOKEN = ""

# 推送开关：True = 默认启用推送（仍然需要 --push 参数触发）
PUSH_ENABLED = True

# ─── 简报输出配置 ──────────────────────────────────────────
OUTPUT_DIR = "output"
TIME_WINDOW = timedelta(hours=24)
MAX_ITEMS_PER_CATEGORY = 8   # 每类最多新闻条数
MAX_PUSH_LENGTH = 4000       # 推送内容截断长度（PushPlus 限制 32K，微信限制约 5K）

# 简报中展示的比赛结果天数范围
SCORE_LOOKBACK_DAYS = 2
