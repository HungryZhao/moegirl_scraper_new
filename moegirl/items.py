# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class CategoryItem(scrapy.Item):
    # 分类名称
    name = scrapy.Field()
    # 父级分类名称列表
    parent_categories = scrapy.Field()
    # 子分类名称列表
    subcategories = scrapy.Field()

class ArticleItem(scrapy.Item):
    # 词条标题
    title = scrapy.Field()
    # 原始 wikitext 内容
    content = scrapy.Field()
    # 所属分类名称列表
    categories = scrapy.Field()