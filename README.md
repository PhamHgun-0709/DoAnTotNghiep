# 📊 Ad Analytics — Big Data (Thesis)

Hệ thống demo cho phân tích và tối ưu chiến dịch quảng cáo bằng Apache Spark, FastAPI và Streamlit.

Luồng chính:

CSV dữ liệu → Spark ETL → PostgreSQL → FastAPI → Streamlit Dashboard

## 🚀 Khởi động nhanh

```powershell
cd e:\DoAnTotNghiep
./docker-up.ps1
```

Hoặc dùng Docker Compose trực tiếp:

```powershell
docker compose -f infra/docker/docker-compose.yml up -d
```

Sau đó mở:

- Dashboard: http://localhost:8501
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## 🧩 Cấu trúc chính

- api/: FastAPI backend, routes, services, ML, database
- spark/: ETL jobs và orchestrator
- data/: input, processed, curated, metadata
- giao-dien/: Streamlit dashboard
- infra/docker/: docker-compose và Dockerfiles
- tests/: test smoke cho API, Spark và model artifacts

## ⚙️ Lệnh hữu ích

```powershell
./docker-up.ps1                    # Khởi động
./docker-up.ps1 -Action "down"     # Dừng
./docker-up.ps1 -Action "build"    # Rebuild
./docker-up.ps1 -Action "logs"     # Xem logs
./docker-up.ps1 -Action "ps"       # Xem trạng thái
```

## ✅ Chức năng chính

- Dashboard KPI và biểu đồ phân tích chiến dịch
- Spark ETL cho dữ liệu quảng cáo
- API cho dashboard, pipeline và ML
- Quản lý active/history dataset
- Lịch sử upload và file processed được giữ lại theo phiên

## 🧪 Kiểm tra nhanh

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/summary
```

## 📝 Ghi chú

- File checksum `.crc` đã được dọn khỏi repo vì không cần cho code hoặc runtime.
- Một số script dev như `scripts/seed_admin_quick.py` và `scripts/run/*.ps1` chỉ phục vụ test/dev; nếu không dùng có thể loại khỏi bản nộp hoặc đưa vào thư mục archive.

Nếu cần, mình có thể bổ sung thêm phần API endpoints ngắn hoặc phần hướng dẫn triển khai chi tiết hơn. 

### Database connection failed
```bash
# Check PostgreSQL
docker ps | grep postgres

# Connect directly
docker exec -it adanalytics-db psql -U postgres -d ad_analytics
```

### Streamlit dashboard not loading
```bash
# Check container
docker ps | grep streamlit

# Restart
docker restart adanalytics-streamlit

# Verify API access
docker exec adanalytics-streamlit curl http://api:8000/health
```

---

## 📞 Support & Questions

1. **Check logs**: `docker logs <container_name>`
2. **API docs**: `http://localhost:8000/docs`
3. **System status**: `http://localhost:8000/health`
4. **All services running**: `docker compose ps`

---

## 📚 References

- [Apache Spark](https://spark.apache.org/docs/latest/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://docs.streamlit.io/)
- [Scikit-learn](https://scikit-learn.org/)
- [PostgreSQL](https://www.postgresql.org/docs/)

---

**Status**: ✅ Production-Ready for Demo & Thesis Defense  
**Last Updated**: May 7, 2026  
**Version**: 1.0.0  
**Author**: Ad Analytics Team
