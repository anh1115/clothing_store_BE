# utils.py
import requests
import re
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def get_vietnamese_stopwords():
    url = "https://raw.githubusercontent.com/stopwords/vietnamese-stopwords/master/vietnamese-stopwords.txt"
    response = requests.get(url)
    stopwords = response.text.splitlines()

    stopwords = [word for word in stopwords if word.isalpha()]  # Chỉ giữ lại từ chứa chữ cái
    return stopwords

def clean_description(text):
    # Loại bỏ thẻ HTML
    soup = BeautifulSoup(text, "html.parser")
    text_without_html = soup.get_text()

    # Loại bỏ ký tự đặc biệt (chỉ giữ lại chữ cái và số)
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', text_without_html)

    return cleaned_text

def calculate_cosine_similarity(features, vietnamese_stopwords):
    tfidf = TfidfVectorizer(stop_words=vietnamese_stopwords)
    tfidf_matrix = tfidf.fit_transform(features)
    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
    return cosine_sim

def calculate_weighted_scores(cosine_sim, product, products):
    # Tính sự khác biệt về giá
    prices = [float(p.sell_price) for p in products]
    price_differences = np.abs(np.array(prices, dtype=float) - float(product.sell_price))

    max_price_diff = np.max(price_differences)
    if max_price_diff > 0:
        weighted_scores = cosine_sim.flatten() - (price_differences / max_price_diff)
    else:
        weighted_scores = cosine_sim.flatten()

    return weighted_scores
