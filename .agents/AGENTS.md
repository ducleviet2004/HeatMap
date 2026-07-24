# Agent Guidelines — Route Deviation Heatmap Analytics System (PRD V4)

Dự án **Route Deviation Heatmap Analytics** tuân thủ nghiêm ngặt các quy tắc kiến trúc, quy chuẩn code style, kiểm thử và quy trình quản lý task tự động dưới đây. Mọi AI Agent (Antigravity, Cursor, Cline, Copilot) tham gia phát triển dự án PHẢI tuân thủ $100\%$ các nguyên tắc này.

---

## 1. Quy Trình Làm Việc & Quản Lý Nhánh Git (Mandatory Git Workflow)

### 🔴 QUY TẮC NHÁNH CÁ NHÂN & ĐỒNG BỘ CODE BẮT BUỘC:

1. **Pull & Merge Code từ `develop` BẮT BUỘC Trước Khi Làm Task Mới**:
   - Trước khi bắt đầu bất kỳ Task mới nào, Agent **BẮT BUỘC** phải thực hiện các lệnh:
     ```bash
     git fetch origin
     git merge origin/develop --no-edit
     # Hoặc: git pull origin develop
     ```
   - Giải quyết mọi xung đột (conflict) nếu có và đảm bảo tất cả test cases vẫn **PASS 100%** trước khi triển khai code cho task mới.

2. **Chỉ Push Code Lên Nhánh Cá Nhân Riêng Biệt**:
   - Mỗi thành viên trong nhóm **chỉ được phép push code lên nhánh cá nhân của mình** trên GitHub remote (`origin <nhánh_cá_nhân>`):
     - **Nguyễn Văn Đoan** -> Push duy nhất lên nhánh `Doan` (`git push origin Doan`)
     - **Nguyễn Văn Sáng** -> Push duy nhất lên nhánh `Sang` (`git push origin Sang`)
     - **Lê Việt** -> Push duy nhất lên nhánh `VietLe` (`git push origin VietLe`)
   - **TUYỆT ĐỐI KHÔNG** push trực tiếp lên `main`, `develop` hoặc nhánh của thành viên khác.

3. **Commit & Push Code Ngay Sau Khi Hoàn Thành Mỗi Task**:
   - Ngay sau khi hoàn thành và kiểm thử 1 task, **BẮT BUỘC** phải `git add`, `git commit` và `git push origin <nhánh_cá_nhân>`.
   - Đặt commit message theo chuẩn **Conventional Commits**:
     - `feat(component): ...` (Tính năng mới)
     - `fix(component): ...` (Sửa lỗi)
     - `style(component): ...` (Format, linting)
     - `docs(component): ...` (Cập nhật tài liệu/walkthrough)
     - `ci(component): ...` (Cấu hình CI/CD)

4. **Cập Nhật Tiến Độ trên Google Sheet**:
   - Ngay sau khi push code, tự động cập nhật trạng thái Task tương ứng trên Google Sheet `WBS_Tasks_Roadmap` sang **`Hoàn thành`** (Progress tự động thành **`100%`**).

5. **Tạo Walkthrough Báo Cáo**:
   - Tạo hoặc cập nhật file `walkthrough.md` tổng kết các file thay đổi, lệnh đã test và kết quả kiểm thử.

---

## 2. Quy Chuẩn Codebase & Quality Gates (Bắt Buộc Pass 100%)

### Backend (Python 3.12 / FastAPI / SQLAlchemy 2.0 / PostGIS)

- **Formatting**: Bắt buộc chạy `ruff format backend/` (Không thừa thiếu khoảng trắng, tuân thủ PEP8).
- **Linting**: Bắt buộc chạy `ruff check backend/` (Sắp xếp imports, loại bỏ import thừa, không dùng datetime thiếu timezone).
- **Static Type Check**: Tuân thủ `mypy app` không có lỗi type annotations.
- **ORM Standard**: Sử dụng SQLAlchemy 2.0 `Mapped[...]` type annotations và `mapped_column()`.
- **Unit & Integration Tests**: Đảm bảo tất cả các test cases trong `pytest` chạy **PASS 100%** trước khi commit.

### Frontend (React 19 / TypeScript / Vite / MapLibre / Deck.gl)

- **Formatting**: Bắt buộc chạy `npx prettier --write frontend/`.
- **Linting**: Bắt buộc chạy `npm --prefix frontend run lint` (ESLint 9+ flat config).
- **Type Checking**: Bắt buộc chạy `npm --prefix frontend run typecheck` (`tsc -b`).
- **Tests**: Đảm bảo `vitest` và `vite build` tạo bundle thành công không có warning/error nghiêm trọng.

---

## 3. Quy Chuẩn GIS & Cơ Sở Dữ Liệu (PostGIS & H3 Grid)

1. **Hệ Tọa Độ Spatial Standard**:
   - Luôn luôn dùng **WGS84 EPSG:4326** cho mọi cột Geometry (`Point`, `LineString`).
   - Cấu trúc tọa độ GeoJSON & OSRM: `[longitude, latitude]` (kinh độ trước, vĩ độ sau).

2. **Spatial Indexing**:
   - Tất cả các cột Geometry trong PostGIS (`gps_events.raw_geometry`, `planned_routes.route_geometry`, `matched_segments.geometry`, `trip_bypass_segments.geometry`) **BẮT BUỘC** phải có index **GiST** (`using='gist'`).

3. **H3 Spatial Index**:
   - Độ phân giải H3 Grid sử dụng cho Heatmap: Resolution **9** đến **12**.
   - Bảng `trip_route_hexes` và `h3_aggregates` bắt buộc dùng Primary Key tổng hợp `(hex_id, ...)` để đảm bảo Deduplication rule (1 trip chỉ tính heat_weight 1 lần trên 1 hex).

---

## 4. Cấu Hình Service Local & OSRM

- **OSRM Self-Hosted**: Sử dụng Docker container `ghcr.io/project-osrm/osrm-backend:v5.27.1` với MLD algorithm.
- **PBF Snapshot Pinning**: Mọi bản đồ OSM sử dụng cho routing đều phải được ghim phiên bản tại `osrm/data/routing_metadata.json`.
- **OSRM Latency SLA**: Endpoint Map matching & Routing qua `OsrmClient` phải đảm bảo phản hồi dưới **50ms**.
