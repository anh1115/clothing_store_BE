import requests, re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from products.models import Product, Review
from django.db.models import Count, Avg
import joblib
from user.models import User


def get_vietnamese_stopwords():
    url = "https://raw.githubusercontent.com/stopwords/vietnamese-stopwords/master/vietnamese-stopwords.txt"
    response = requests.get(url)
    stopwords = response.text.splitlines()

    stopwords = [word for word in stopwords if word.isalpha()]
    return stopwords

def clean_description(text):
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return cleaned_text

def calculate_cosine_similarity(features, vietnamese_stopwords):
    tfidf = TfidfVectorizer(stop_words=vietnamese_stopwords)
    tfidf_matrix = tfidf.fit_transform(features)
    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
    return cosine_sim

def calculate_weighted_scores(cosine_sim, product, products):
    prices = [float(p.sell_price) for p in products]
    price_differences = np.abs(np.array(prices, dtype=float) - float(product.sell_price))

    max_price_diff = np.max(price_differences)
    if max_price_diff > 0:
        weighted_scores = cosine_sim.flatten() - (price_differences / max_price_diff)
    else:
        weighted_scores = cosine_sim.flatten()

    return weighted_scores

# Tải mô hình đã huấn luyện
model = joblib.load("recommendation/svd_model.pkl")

# Ánh xạ user_id và product_id thành chỉ mục
users = User.objects.values('user_id')
products = Product.objects.values('product_id')

user_id_to_index = {user['user_id']: idx for idx, user in enumerate(users)}
product_id_to_index = {product['product_id']: idx for idx, product in enumerate(products)}

def recommend_products(user_id, k=8):
    try:
        # Kiểm tra nếu model không tồn tại
        if not model:
            print("Model chưa được tải. Gợi ý sản phẩm phổ biến.")
            return recommend_popular_products(k)

        # Kiểm tra user_id có trong dữ liệu không
        if user_id not in user_id_to_index:
            print(f"user_id {user_id} không tồn tại. Gợi ý sản phẩm phổ biến.")
            return recommend_popular_products(k)

        # Lấy danh sách các sản phẩm hiện có
        all_products = Product.objects.all().values_list('product_id', flat=True)
        if not all_products.exists():
            print("Không có sản phẩm nào. Gợi ý sản phẩm phổ biến.")
            return recommend_popular_products(k)

        # Dự đoán điểm đánh giá cho tất cả sản phẩm
        predictions = [
            (product_id, model.predict(user_id, product_id).est)
            for product_id in all_products
        ]

        # Sắp xếp các sản phẩm theo điểm đánh giá dự đoán giảm dần
        predictions.sort(key=lambda x: x[1], reverse=True)
        # Lấy top K sản phẩm
        recommended_products = [product_id for product_id, _ in predictions[:k]]

        return recommended_products
    except Exception as e:
        print(f"Error in recommend_products: {e}")
        return recommend_popular_products(k)

def recommend_popular_products(k=8):
    try:
        # Tính sản phẩm phổ biến dựa trên đánh giá
        popular_products = Review.objects.values('product__product_id') \
            .annotate(avg_rating=Avg('rating'), review_count=Count('review_id')) \
            .order_by('-avg_rating', '-review_count')[:k]
        return [item['product__product_id'] for item in popular_products]
    except Exception as e:
        print(f"Error in recommend_popular_products: {e}")
        return []