BOOK_FORMATS = {
    "新書",
    "文庫",
    "単行本",
    "ハードカバー",
    "雑誌",
    "電子書籍",
    "その他",
}

DEFAULT_BOOK_FORMAT = "その他"

DEFAULT_CATEGORY_ID = "other"
DEFAULT_CATEGORY_NAME = "その他"

DEFAULT_CATEGORIES = (
    {"categoryId": "technology", "name": "技術書", "sortOrder": 10, "color": "#4C8BF5"},
    {"categoryId": "novel", "name": "小説", "sortOrder": 20, "color": "#7D6CF2"},
    {"categoryId": "business", "name": "ビジネス", "sortOrder": 30, "color": "#35A271"},
    {"categoryId": "design", "name": "デザイン", "sortOrder": 40, "color": "#F08B45"},
    {"categoryId": "history", "name": "歴史", "sortOrder": 50, "color": "#8C6B4F"},
    {"categoryId": "statistics", "name": "統計", "sortOrder": 60, "color": "#3B8EA5"},
    {"categoryId": "hobby", "name": "趣味", "sortOrder": 70, "color": "#C36CA7"},
    {"categoryId": "manga", "name": "漫画", "sortOrder": 80, "color": "#D75C5C"},
    {
        "categoryId": DEFAULT_CATEGORY_ID,
        "name": DEFAULT_CATEGORY_NAME,
        "sortOrder": 90,
        "color": "#8FA2B6",
    },
)
