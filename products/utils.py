import requests, re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd
from products.models import Review
from django.db.models import Count, Avg


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

# Tạo ma trận user-item từ bảng Review
def create_user_item_matrix():
    reviews = Review.objects.all()
    data = [(review.user.user_id, review.product.product_id, review.rating) for review in reviews]
    df = pd.DataFrame(data, columns=['user', 'product', 'rating'])
    
    # Chuyển đổi dữ liệu thành ma trận user-item
    user_item_matrix = df.pivot_table(index='user', columns='product', values='rating')
    return user_item_matrix

# Tính độ tương tự giữa các khách hàng và gợi ý sản phẩm
def recommend_products(user_id):
    user_item_matrix = create_user_item_matrix()

    # Kiểm tra nếu user_id không có trong ma trận thì gợi ý sản phẩm phổ biến
    if user_item_matrix.empty or user_id not in user_item_matrix.index:
        return recommend_popular_products()  
    user_item_matrix_filled = user_item_matrix.fillna(0)
    
    # Tính độ tương tự cosine giữa các khách hàng
    user_similarity = cosine_similarity(user_item_matrix_filled)
    user_similarity_df = pd.DataFrame(user_similarity, index=user_item_matrix_filled.index, columns=user_item_matrix_filled.index)
    similar_users = user_similarity_df[user_id].sort_values(ascending=False).drop(user_id)

    # Lấy các sản phẩm mà các khách hàng tương tự đã đánh giá
    recommended_products = []
    for similar_user in similar_users.index:
        similar_user_ratings = user_item_matrix.loc[similar_user]
        recommended_products += similar_user_ratings[similar_user_ratings > 3].index.tolist()
    recommended_products = list(set(recommended_products) - set(user_item_matrix.loc[user_id][user_item_matrix.loc[user_id] > 0].index.tolist()))

    return recommended_products[:8]  

def recommend_popular_products():
    try:
        reviews = Review.objects.all()
        if not reviews.exists():
            return []

        # Tính điểm đánh giá trung bình cho mỗi sản phẩm và đếm số lượt đánh giá
        product_counts = reviews.values('product__product_id') \
            .annotate(avg_rating=Avg('rating'), review_count=Count('product__product_id')) \
            .order_by('-avg_rating', '-review_count')
        popular_products = [item['product__product_id'] for item in product_counts[:8]]

        return popular_products
    except Exception as e:
        return []