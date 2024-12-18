import os
import requests
import xml.etree.ElementTree as ET
import json
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
import json
import re
from datetime import datetime
import pymongo
import scrapy
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup


# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables for database and API configuration
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME')
COLLECTION_FLOWER_DATA = os.getenv('DB_COLLECTION_DATA')

mongoClient = pymongo.MongoClient(MONGODB_URI)
mongoFlowerDB = mongoClient[DB_NAME]
collectionFlowerData = mongoFlowerDB[COLLECTION_FLOWER_DATA]


# URLs of the sitemaps
sitemap_urls = [
    'https://hoatuoimymy.com/product-sitemap1.xml',
    'https://hoatuoimymy.com/product-sitemap2.xml'
]

all_urls = []

# Function to fetch and parse XML
def fetch_sitemap(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        root = ET.fromstring(response.content)
        # Extract all <loc> elements that contain the URLs
        for url_element in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
            all_urls.append(url_element.text)
    except Exception as e:
        print(f"Error fetching or parsing {url}: {e}")

# Fetch and parse both sitemaps
for sitemap_url in sitemap_urls:
    fetch_sitemap(sitemap_url)

# Specify the filename
filename = 'all_urls.json'
# Write the URLs to a JSON file
with open(filename, 'w') as f:
    json.dump(all_urls, f, indent=4)

print(f"Extracted {len(all_urls)} URLs and saved to all_urls.json")

# Load the all_urls list from the JSON file
with open(filename, 'r') as file:
    all_urls = json.load(file)

print(f"All URLs loaded from {filename}")


class CustomSpider(scrapy.Spider):
    name = 'custom_spider'
    start_urls = all_urls[:]

    # Initialize a counter
    request_count = 0

    def parse(self, response):
        self.request_count += 1  
        description = ""

        # Scraping the review title (h1 tag inside div.product_title)
        review_title = response.css('h1.product-title::text').get()

        if review_title:
            h1_tag = review_title.strip()
        else:
            h1_tag = ""

        # Now, h1_tag contains the content of the h1 tag
        print(h1_tag)

        # Lấy giá gốc
        original_price = response.css('del[aria-hidden="true"] bdi::text').get()
        if original_price:
            original_price = original_price.strip()
        else:
            original_price = ""

        # Lấy giá khuyến mãi
        discounted_price = response.css('ins[aria-hidden="true"] bdi::text').get()
        if discounted_price:
            discounted_price = discounted_price.strip()
        else:
            discounted_price = ""


        # Scraping the ck-content
        ck_contents = response.css('div.woocommerce-Tabs-panel--description')

        for ck_content in ck_contents:
            for element in ck_content.xpath('./*'):
                # Extract the text from h2 and h3 tags
                if element.root.tag == 'h2':
                    description += ' '.join(element.css('::text').getall()).strip() + "\n"
                elif element.root.tag == 'h3':
                    description += ' '.join(element.css('::text').getall()).strip() + "\n"

                # Extract the text from p tags
                elif element.root.tag == 'p':
                    description += ' '.join(element.css('::text').getall()).strip() + "\n"

                # Extract the list items from ul tags
                elif element.root.tag == 'ul':
                    li_tags = element.css('li')
                    for li_tag in li_tags:
                        description += f"- {' '.join(li_tag.css('::text').getall()).strip()}" + "\n"
        pattern = r"Hoa Tươi My My luôn là lựa chọn tốt nhất của những tín đồ yêu thích hoa[\s\S]*?Bạn có thể đặt hoa nhanh ship 2-3h tại zalo shop"
        description = re.sub(pattern, "", description).strip()

        # Initialize an empty array to hold image URLs
        image_urls = []

        # Select all the div elements with the specific class
        image_elements = response.css('div.woocommerce-product-gallery__image')

        # Loop through each image element to extract the URLs
        for element in image_elements:
            # Extract the main image URL from the 'data-large_image' attribute
            image_url = element.css('img::attr(data-large_image)').get()

            # Add the extracted image URL to the array
            if image_url:
                image_urls.append(image_url)

        data = {}

        if h1_tag and description:
            data = {
                "url": response.url,  
                "title": h1_tag, 
                "content": description,
                "original_price": original_price,
                "discounted_price": discounted_price,
                "image_urls": image_urls
            }

            yield data
        # Print out the current request count
        print('====> h1_tag', h1_tag)
        print('====>description', description)
        print('====>image_urls', image_urls)
        print('====>original_price', original_price)
        print('====>discounted_price', discounted_price)

        self.logger.info(f"Number of requests done: {self.request_count}")
        self.logger.info(f"Crawled: {response.url}")
        collectionFlowerData.insert_one(data)


# Initialize the Scrapy crawler process
process = CrawlerProcess({
    'LOG_LEVEL': 'INFO',
    'FEEDS': {
        'output.json': {
            'format': 'json',
            'encoding': 'utf8',
            'store_empty': False,
            'fields': None,
            'indent': 4,
        },
    },
    'CLOSESPIDER_TIMEOUT': 60000000000,  # Close the spider after 60 seconds (adjust as needed)
    'DOWNLOAD_DELAY': 3,  # Delay of 2 seconds between each request
})

# Start the spider
process.crawl(CustomSpider)
process.start()