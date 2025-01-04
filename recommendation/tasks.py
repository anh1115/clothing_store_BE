from celery import shared_task
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split
from surprise import accuracy
from products.models import Review  # Import mô hình Review của Django
import joblib
import pandas as pd
@shared_task
def train_recommendation_model():
    # Truy vấn dữ liệu từ cơ sở dữ liệu
    review_data = Review.objects.all().values('user_id', 'product_id', 'rating')
    # Chuyển dữ liệu thành DataFrame
    review_data_df = pd.DataFrame(list(review_data))
    # Kiểm tra nếu dữ liệu trống
    if review_data_df.empty:
        return "No data available to train the model."
    # Chuẩn bị dữ liệu cho Surprise
    reader = Reader(rating_scale=(1, 5))
    data = Dataset.load_from_df(review_data_df[['user_id', 'product_id', 'rating']], reader)
    # Chia dữ liệu thành tập huấn luyện và kiểm tra
    trainset, testset = train_test_split(data, test_size=0.2, random_state=42)
    # Huấn luyện mô hình SVD với tham số tối ưu
    model = SVD(n_factors=20, reg_all=0.1, lr_all=0.01)
    model.fit(trainset)
    # Đánh giá mô hình trên tập kiểm tra
    predictions = model.test(testset)
    rmse = accuracy.rmse(predictions)
    # Lưu mô hình sau khi huấn luyện
    joblib.dump(model, 'recommendation/svd_model.pkl')
    return f"Model trained with RMSE: {rmse}"