
> **🚨 IMPORTANT**  
> This project focuses on **early detection and classification of Brain Tumors using AI**, assisting radiologists in rapid decision-making through automated MRI screening.

---
## ⚡ Project Overview
**Brain Tumor MRI Classification System** là một hệ thống AI được xây dựng hoàn toàn từ đầu (build from scratch), giúp phân loại tự động các loại u não thông qua ảnh chụp cộng hưởng từ (MRI images).

💡 **Mục tiêu:**
* Phát triển và phân loại nhanh chóng 4 nhóm bệnh não: Glioma, Meningioma, Pituitary,  No Tumor
* Hỗ trợ các bác sĩ chuẩn đoán hình ảnh tăng độ chính xác
* Minh bạch hóa quyết định của AI thông qua bản đồ nhiệt  

> ### 📚 Giải thích về bệnh  
>  
> **1. Glioma**  
> - Là u não ác tính phổ biến nhất  
> - Phát triển từ tế bào thần kinh đệm  
> - ⚠️ Nguy hiểm, lan nhanh  
>  
> **2. Meningioma**  
> - U não xuất phát từ màng não  
> - Thường là lành tính  
> - Phát triển *chậm hơn* Glioma  
>  
> **3. Pituitary Tumor**  
> - U ở tuyến yên  
> - Ảnh hưởng đến **hormone**  
> - Có thể gây rối loạn nội tiết  
>  
> **4. No Tumor**  
> - Không có khối u  
> - Ảnh bình thường

---
## 🚀 Key Features
**🔍 1. AI-based Image Classification**
* Sử dụng mạng Custom CNN (Convolutional Neural Network) tự thiết kế.
* Phân loại đa lớp (Multi-class classification) với hàm kích hoạt Softmax.

**🧠 2. Model Training Pipeline**
* Tiền xử lý ảnh tĩnh: Crop viền, chuyển thang xám, chuẩn hóa pixel (Normalize).
* Tăng cường dữ liệu (Data Augmentation) để tránh Overfitting.
* Training + Validation chia tỷ lệ chuẩn (70/15/15).

**📊 3. Visualization & Evaluation**
* Đánh giá qua các chỉ số: Accuracy, Precision, Recall, F1-score.
* Vẽ biểu đồ Confusion Matrix và Loss/Accuracy Graph.
* Tích hợp **Grad-CAM** để giải thích vùng khối u AI đang chú ý.

**🌐 4. Deployable System**  
.......

----
 ## 🏗️ System Architecture
 ```
 
 Triển khai rồi mới biết được
 
 ```

 ---
 ## 🧪 Dataset

**Dataset sử dụng:** Brain Tumor Classification (MRI) từ Kaggle.  

📌 **Bao gồm:**
* Khoảng 3,264+ ảnh chụp cộng hưởng từ (MRI).
* Labels: `0: Glioma Tumor`, `1: Meningioma Tumor`, `2: Pituitary Tumor`, `3: No Tumor`.

---

## 📂 Project Structure

``` text```

---

## ⚙️ Installation 

**1. Clone repo**
```bash
git clone 

```

**2. Cài đặt thư viện**
```bash
pip install -r requirements.txt
```