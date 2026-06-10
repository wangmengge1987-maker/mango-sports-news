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
            "湖人", "勇士", "凯尔特人", "掘金", "热火", "雄鹿", "快船", "独行侠",
            # 注意：不用"太阳"（会误配韩国联赛"太阳神"），改用英文队名
            # 注意：不用"詹姆斯"（会误配CBA外援大卫-詹姆斯），改用英文名
            "东契奇", "LeBron", "库里", "杜兰特", "字母哥", "约基奇",
            "NBA总决赛", "NBA季后赛", "NBA选秀",
        ],
        # 来源名优先规则：如果来源名包含以下关键词，优先分到此类
        "source_priority": ["ESPN NBA", "Yahoo Sports NBA"],
        # 注意：Sky Sports NBA 的 RSS feed 实际返回混合体育内容（含足球），
        # 因此不列入 source_priority，避免足球新闻被错误归入 NBA
    },
    "CBA": {
        "keywords": [
            "CBA",
            "广东", "新疆", "浙江", "广厦",
            "北京首钢", "上海久事", "龙狮", "深圳", "山东", "青岛",
            "北控", "吉林", "山西", "天津", "福建", "江苏", "四川", "宁波",
            # 辽宁单独处理：不直接用"辽宁"（会误配中超辽宁铁人），用具体名称
            "辽宁本钢", "辽宁队", "辽宁男篮",
            "大卫-詹姆斯",  # CBA外援，避免被NBA分类误抢
            "KBL联赛",  # 韩国篮球联赛
            "NBL",
        ],
        "source_priority": ["懂球帝 CBA", "懂球帝 中国篮球"],
    },
    "英超": {
        "keywords": [
            "英超", "Premier League",
            "Manchester City", "Manchester United", "Liverpool", "Arsenal", "Chelsea",
            "Tottenham", "Newcastle", "Aston Villa", "West Ham", "Brighton",
            "Wolves", "Everton", "Crystal Palace", "Fulham", "Brentford",
            "Nottingham Forest", "Bournemouth",
            # 常见缩写
            "Man City", "Man Utd", "Man United",
            "Spurs", "NUFC", "WHU", "AVL",
            # 国际赛事（常见于足球 RSS 中）
            "World Cup", "世界杯", "Champions League", "UCL", "Europa League",
            "England", "Three Lions",
            "France", "Germany", "Spain", "Italy", "Brazil", "Argentina",
            "Euro 202", "World Cup 202",
            # 其他欧洲联赛（常见于综合足球 RSS）
            "La Liga", "Serie A", "Bundesliga", "Ligue 1",
            "Real Madrid", "Barcelona", "Atletico Madrid", "Bayern",
            "Juventus", "AC Milan", "Inter Milan", "Paris Saint-Germain", "PSG",
            "Ajax", "Porto", "Benfica", "Sporting",
            # 知名球员（英文名）
            "Harry Kane", "Kylian Mbappe", "Erling Haaland", "Mohamed Salah",
            "Bukayo Saka", "Jude Bellingham", "Vinicius Jr", "Lamine Yamal",
            # 足球通用术语
            "football", "soccer", "manager", "转会", "transfer",
            "goal", "goals", "striker", "midfielder", "defender", "goalkeeper",
            "captain", "captaincy", "substitute", "substitution",
            "曼城", "阿森纳", "利物浦", "曼联", "切尔西", "热刺", "纽卡斯尔",
            "哈兰德", "萨拉赫", "德布劳内",
        ],
        "source_priority": ["ESPN Soccer", "Sky Sports Football"],
    },
    "中超": {
        "keywords": [
            "中超", "Chinese Super League",
            "上海海港", "山东泰山", "北京国安", "成都蓉城", "上海申花",
            "浙江队", "天津津门虎", "长春亚泰", "河南队", "梅州客家",
            "青岛海牛", "南通支云", "大连人", "深圳队", "沧州雄狮", "武汉三镇",
            "辽宁铁人",  # 中超球队，区别于CBA的辽宁
            "重庆铜梁龙", "云南玉昆", "大连英博",
            "全中超", "中甲", "中乙",
        ],
        "source_priority": ["懂球帝 中超", "懂球帝 中国足球", "百度体育 中国足球"],
    },
    "伤病": {
        "keywords": [
            "受伤", "伤病", "报销", "缺阵", "复出", "手术", "韧带", "肌肉", "骨折",
            "injury", "injured", "out for", "sidelined", "surgery", "torn", "strain",
            "sprain", "fracture", "hamstring", "ACL", "MCL",
        ],
        "source_priority": [],
    },
    "转会": {
        "keywords": [
            "转会", "签约", "续约", "加盟", "离队", "交易", "选秀", "自由球员",
            "transfer", "sign", "signing", "contract", "extend", "extension",
            "trade", "draft", "free agent", "loan", "move to", "join", "leave",
        ],
        "source_priority": [],
    },
}

# 不感兴趣的内容关键词（满足任一即丢弃）
FILTER_KEYWORDS = [
    "中冠",  # 中国第四级别联赛
    "中乙",  # 中国第三级别联赛（除非用户关注）
]

# 硬性屏蔽的文章URL（不再推送这些确定过期的旧闻）
# 格式：baijiahao.baidu.com/s?id=数字
BLOCKED_ARTICLE_IDS = [
    "1863877836475759186",  # NBA ATELIER：热潮之后，城市里的「即刻上
    "1864042795544538064",  # NBA宣布：詹姆斯·哈登超越马努·吉诺比利
    "1864082050892842336",  # 里夫斯：我对詹姆斯说他疯了
    "1863947855008170668",  # 广东二沙体育训练中心：全红婵
    "1864209141726834449",  # 曼联3-2利物浦
    "1863684629595227106",  # 19岁弗拉格获NBA最佳新秀
    "1863952952132991651",  # NBA官方：黄蜂前锋穆萨-迪亚巴特
    "1864223821851216644",  # NBA-康宁汉姆32+12哈里斯30+9
    "1864118983652881313",  # 中超第九轮：成都蓉城逆转上海申花
    "1864039994083365518",  # 快评丨3比2绝杀上海申花
    "1864086111401107768",  # 新赛季女超三台主场首秀
    "1864081798358357483",  # 猛龙官方：英格拉姆因右脚跟炎症
]

# ─── RSS 数据源 ────────────────────────────────────────────
RSS_SOURCES = [
    {"name": "ESPN NBA",       "url": "https://www.espn.com/espn/rss/nba/news",       "hint": "NBA",  "lang": "en"},
    {"name": "ESPN Soccer",    "url": "https://www.espn.com/espn/rss/soccer/news",    "hint": "足球",  "lang": "en"},
    {"name": "BBC Sport",      "url": "http://feeds.bbci.co.uk/sport/rss.xml",        "hint": "综合",  "lang": "en"},
    {"name": "Sky Sports", "url": "https://www.skysports.com/rss/12040",               "hint": "综合",  "lang": "en"},
    {"name": "Sky Sports Football", "url": "https://www.skysports.com/rss/11095",     "hint": "足球",  "lang": "en"},
    {"name": "The Guardian Sport",  "url": "https://www.theguardian.com/uk/sport/rss","hint": "综合",  "lang": "en"},
    {"name": "Yahoo Sports NBA","url": "https://sports.yahoo.com/nba/rss.xml",         "hint": "NBA",  "lang": "en"},
    # 中文源
    {"name": "百度体育 中国足球", "url": "http://news.baidu.com/n?cmd=1&class=chinasoccer&tn=rss", "hint": "中超", "lang": "zh"},
    {"name": "百度体育 国际足球", "url": "http://news.baidu.com/n?cmd=1&class=worldsoccer&tn=rss",  "hint": "足球", "lang": "zh"},
    {"name": "百度体育 篮球",    "url": "http://news.baidu.com/n?cmd=1&class=nba&tn=rss",           "hint": "NBA/CBA", "lang": "zh"},
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

# ─── 懂球帝搜索 API（中文体育新闻，无需 Key）───────────────
DONGQIUDI_SOURCES = [
    {"name": "懂球帝 中超", "keywords": "中超", "enabled": True},
    {"name": "懂球帝 中超联赛", "keywords": "中超联赛", "enabled": True},
    {"name": "懂球帝 中超球队", "keywords": "上海海港 山东泰山 北京国安", "enabled": True},
    {"name": "懂球帝 CBA", "keywords": "CBA", "enabled": True},
    {"name": "懂球帝 中国篮球", "keywords": "篮球 CBA 中国男篮", "enabled": True},
]
DONGQIUDI_MAX_ITEMS = 10  # 每个关键词最多取前 N 条

# ─── 推送配置（PushPlus：pushplus.plus）───────────────────
# 优先从环境变量读取，如未设置则尝试改配置文件中的占位
PUSHPLUS_TOKEN = ""

# 推送开关：True = 默认启用推送（仍然需要 --push 参数触发）
PUSH_ENABLED = True

# ─── 简报输出配置 ──────────────────────────────────────────
OUTPUT_DIR = "output"
TIME_WINDOW = timedelta(hours=24)
MAX_ITEMS_PER_CATEGORY = 8   # 每类最多新闻条数
HISTORY_PRUNE_DAYS = 45      # 文章历史保留天数（从14延长到45，减少旧新闻周期性复活）
MAX_PUSH_LENGTH = 6000       # 推送内容截断长度
# PushPlus API 限制: 32KB（~32000 中文字符）
# 微信展示限制: 约 5000-8000 字符（过长会被微信折叠）
# 设为 6000 在 WeChat 展示范围 + PushPlus 范围内
# 截断方式: 在行边界截断（而非字符位置），见 pusher.py / generator.py

# 简报中展示的比赛结果天数范围
SCORE_LOOKBACK_DAYS = 2
