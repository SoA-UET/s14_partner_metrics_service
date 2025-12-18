# Quick Start Guide - S14 Partner Metrics Service

## Bắt đầu nhanh (Vietnamese)

### 1. Cài đặt dependencies
```bash
uv pip install -e .
```

### 2. Cấu hình môi trường
```bash
# Copy file cấu hình mẫu
cp .env.example .env

# Chỉnh sửa .env với các giá trị thực tế
# Tối thiểu cần thiết:
# - PARTNER_ID: ID của partner này
# - RABBITMQ_URL: URL kết nối RabbitMQ
# - IDENTITY_SERVICE_URL: URL của Identity Service để xác thực JWT
```

### 3. Chạy service
```bash
python -m app
```

Service sẽ khởi động trên port 5014 (mặc định).

### 4. Kiểm tra health
```bash
curl http://localhost:5014/api/v1/partner/metrics/health
```

## API Endpoints

### Lấy thống kê cuộc hội thoại
```bash
curl -X GET "http://localhost:5014/api/v1/partner/metrics/conversations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Lấy tỷ lệ hài lòng
```bash
curl -X GET "http://localhost:5014/api/v1/partner/metrics/satisfaction-rate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Lấy tỷ lệ offload
```bash
curl -X GET "http://localhost:5014/api/v1/partner/metrics/offload-rate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Cấu hình quan trọng

| Biến môi trường | Mô tả | Giá trị mặc định |
|-----------------|-------|------------------|
| PARTNER_ID | ID của partner (BẮT BUỘC) | - |
| FLASK_PORT | Port của HTTP server | 5014 |
| RABBITMQ_URL | URL kết nối RabbitMQ | amqp://guest:guest@localhost:5672/ |
| IDENTITY_SERVICE_URL | URL của Identity Service | http://localhost:5001 |
| S08_EVENTS_QUEUE | Queue nhận events từ S08 | s08_events_queue |
| S14_S08_REQUESTS_QUEUE | Queue gửi requests tới S08 | s14_s08_requests_queue |
| S14_S08_RESPONSES_QUEUE | Queue nhận responses từ S08 | s14_s08_responses_queue |

## Kiến trúc

Service hoạt động theo 2 chế độ:

1. **Background processing**: Nhận events real-time từ S08 qua RabbitMQ
   - `conversation_start_by_partner` - Cuộc hội thoại mới bắt đầu
   - `conversation_changed_status_by_partner` - Thay đổi trạng thái
   - `conversation_satisfaction_change_by_partner` - Cập nhật đánh giá

2. **HTTP API**: Phục vụ các truy vấn từ Partner Portal
   - H30.1: Thống kê cuộc hội thoại
   - H30.2: Tỷ lệ hài lòng khách hàng
   - H30.3: Tỷ lệ offload (AI xử lý thành công)

## Troubleshooting

### Service không khởi động được
- Kiểm tra PARTNER_ID đã được cấu hình trong .env
- Kiểm tra RabbitMQ server đang chạy
- Kiểm tra các dependencies đã được cài đặt

### Không nhận được events
- Kiểm tra S08_EVENTS_QUEUE đúng tên
- Kiểm tra partner_id trong events có khớp với PARTNER_ID
- Xem logs để kiểm tra lỗi kết nối RabbitMQ

### HTTP API trả về 401 Unauthorized
- Kiểm tra JWT token hợp lệ
- Kiểm tra IDENTITY_SERVICE_URL có thể truy cập được
- Kiểm tra JWKS endpoint: {IDENTITY_SERVICE_URL}/.well-known/jwks.json

### Metrics không cập nhật real-time
- Kiểm tra event consumer thread đang chạy (xem logs)
- Kiểm tra S08 có đang publish events không
- Kiểm tra partner_id trong events có đúng không

## Tài liệu chi tiết

- [README.md](README.md) - Tài liệu đầy đủ
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Tóm tắt implementation
- [docs/services/partner/S14_Partner_Metrics_Service.md](docs/services/partner/S14_Partner_Metrics_Service.md) - Spec chi tiết
- [docs/api_groups/H30.md](docs/api_groups/H30.md) - HTTP API spec
- [docs/api_groups/A17a.md](docs/api_groups/A17a.md) - Event API spec
- [docs/api_groups/A17b.md](docs/api_groups/A17b.md) - Method API spec
