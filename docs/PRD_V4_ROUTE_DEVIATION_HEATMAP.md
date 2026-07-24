# PRD V4 — Route Deviation Heatmap Analytics System

## 0. Thông tin tài liệu

- **Trạng thái**: Baseline để xây dựng dự án mới
- **Phiên bản**: 4.0
- **Ngày**: 23/07/2026
- **Thời gian phát triển**: 6 tuần
- **Đội ngũ**: 3 thành viênt
- **Mục tiêu tải bắt buộc**: duy trì tối thiểu 1.000 request/giây theo workload chuẩn

Tài liệu này là nguồn yêu cầu chính thức cho codebase mới. Khi có mâu thuẫn với PRD V2.1, V3 hoặc tài liệu MVP cũ, PRD V4 được ưu tiên. Thay đổi business rule phải được ghi lại bằng quyết định kiến trúc (ADR), cập nhật test và tăng `algorithm_version` nếu ảnh hưởng kết quả phân tích.

---

## 1. Tóm tắt sản phẩm

Route Deviation Heatmap là hệ thống tiếp nhận hành trình GPS, so sánh tuyến thực tế với tuyến dự kiến, xác định các đoạn đường dự kiến bị chuyến xe bỏ qua và tổng hợp thành heatmap H3.

Heatmap chính trả lời:

> Khu vực hoặc đoạn đường nào đang bị nhiều chuyến xe bỏ qua nhất?

Heatmap không tự kết luận:

- Tài xế gian lận.
- Bản đồ sai.
- Đang có tắc đường hoặc đường cấm.
- Một khu vực có chất lượng tuyến kém chỉ vì tỷ lệ bypass cao trên mẫu nhỏ.

Các kết luận nguyên nhân cần thêm dữ liệu và quy trình điều tra riêng.

## 2. Mục tiêu sản phẩm

1. Phát hiện bypass đáng tin cậy, hạn chế false positive do GPS drift, đường song song, cầu/hầm và mất tín hiệu.
2. Ưu tiên khu vực theo số chuyến bị ảnh hưởng.
3. Cho phép đội vận hành kiểm tra ngược từ heatmap về trip và route liên quan.
4. Lọc kết quả theo thời gian và tài xế.
5. Tiếp nhận GPS mà không chờ map matching hoàn tất.
6. Đạt tối thiểu 1.000 req/s theo workload và điều kiện benchmark tại mục 14.
7. Có khả năng tái xử lý khi thuật toán hoặc dữ liệu routing thay đổi.

## 3. Người dùng

| Người dùng         | Nhu cầu                                                                |
| ------------------ | ---------------------------------------------------------------------- |
| Operations Manager | Tìm khu vực ảnh hưởng nhiều chuyến để ưu tiên điều tra                 |
| GIS/Data Analyst   | Phân tích route, confidence, H3 và chất lượng GPS                      |
| Fleet Supervisor   | Xem lịch sử deviation theo tài xế nhưng không tự động kết luận vi phạm |
| Product/Map Team   | Phát hiện khu vực có khả năng cần cải thiện routing/map                |
| Developer/SRE      | Theo dõi ingestion, queue, OSRM, finalization và API                   |

## 4. Phạm vi

### 4.1. Trong phạm vi 6 tuần

- Tiếp nhận GPS theo event contract có idempotency.
- Lưu GPS thô bất biến.
- Làm sạch GPS theo rule cấu hình.
- Map matching bằng OSRM self-hosted.
- Lưu route dự kiến cùng phiên bản.
- So sánh ordered road-edge sequence.
- Geometry corridor fallback có nhãn rõ ràng.
- Kết quả `provisional` khi chuyến đang chạy và `final` khi kết thúc.
- Chuyển đoạn planned route bị bỏ qua đã xác nhận sang H3.
- Tổng hợp distinct trip/driver.
- Dashboard H3, heat blur, filter và route comparison.
- REST API, OpenAPI, migration, Docker Compose và CI.
- Unit, integration, spatial correctness và load test.
- Monitoring kỹ thuật cơ bản.

### 4.2. Ngoài phạm vi

- Tự động kết luận gian lận hoặc xử phạt tài xế.
- Tự động phân loại nguyên nhân bypass bằng ML.
- Kafka, Kubernetes, data lake hoặc microservices nếu benchmark chưa chứng minh cần thiết.
- Tự động reroute hoặc thay đổi giá cước.
- Mobile app cho tài xế.
- Sử dụng routing API công cộng cho production.

---

## 5. Business rules bắt buộc

### BR-01 — Nguồn sự thật của bypass

Nguồn sự thật là sự khác nhau giữa **ordered road-edge sequence** của planned route và actual matched route.

H3 mismatch, khoảng cách GPS và point severity chỉ là candidate hoặc diagnostic, không tự đủ để xác nhận bypass.

### BR-02 — Điều kiện xác nhận bypass

Một contiguous planned-edge run được xác nhận bypass khi:

1. Không xuất hiện tương ứng trong actual ordered edge sequence.
2. Planned và actual dùng cùng `routing_data_version`.
3. Map-match confidence đạt ngưỡng cấu hình.
4. Độ dài đoạn thiếu đạt `minimum_missing_run_m`.
5. Geometry/corridor check loại được trường hợp cùng hành lang đường nhưng khác biểu diễn graph.
6. Đoạn không nằm hoàn toàn trong GPS gap hoặc trace mơ hồ.

Nếu thiếu graph metadata, hệ thống có thể dùng geometry fallback nhưng phải lưu:

```text
detection_method = geometry_fallback
```

### BR-03 — Đơn vị heatmap

Đơn vị nhiệt là chuyến đi:

```text
heat_weight = bypass_trip_count
```

Một trip chỉ được cộng tối đa một lần trong cùng một `(hex_id, h3_resolution)`.

Không được dùng số GPS point làm heat weight.

### BR-04 — Eligible population

Một trip chỉ thuộc mẫu của hex nếu planned route có hiệu lực của trip đi qua hex đó.

```text
bypass_rate = bypass_trip_count / eligible_trip_count
```

`bypass_rate` là metric phân tích, không phải heat weight chính.

### BR-05 — Display weight

Độ đậm hiển thị:

```text
display_weight = log(1 + bypass_trip_count)
```

Không normalize theo giá trị lớn nhất của riêng response vì một trip duy nhất không được hiển thị như điểm nóng nhất.

Ngưỡng màu khởi đầu:

| Bypass trips | Màu               |
| -----------: | ----------------- |
|          1–2 | Xanh da trời nhạt |
|          3–5 | Vàng              |
|         6–10 | Cam               |
|        11–20 | Đỏ                |
|          ≥21 | Tím               |

Các ngưỡng phải cấu hình và version hóa.

### BR-06 — Filter semantics

Khi filter theo tài xế, thời gian hoặc resolution, toàn bộ metric phải được tính trên đúng tập trip đã lọc. Không được chỉ lọc polygon sau khi lấy aggregate toàn cục.

### BR-07 — Provisional và final

- `provisional`: kết quả khi chuyến đang chạy; được phép thay đổi.
- `final`: kết quả sau khi chuyến kết thúc và toàn bộ segment đủ chất lượng đã được match lại.
  Chỉ kết quả `final` được cập nhật heatmap chính thức.

### BR-08 — GPS gap

- Không tạo GPS giả để lấp khoảng trống.
- Không nối thẳng hai đầu gap rồi coi là actual route.
- Gap dài hoặc bất khả thi phải tách trace thành segment.
- Vùng không quan sát không làm tăng `bypass_trip_count`.
- Kết quả mơ hồ phải có reason code.

### BR-09 — Versioning

Mọi kết quả dẫn xuất phải truy được:

- `planned_route_version`
- `routing_data_version`
- `algorithm_version`
- `threshold_config_version`
- `h3_resolution`
- `detection_method`
- `map_match_confidence`
- thời điểm xử lý

Kết quả từ hai routing dataset khác nhau không được so sánh trực tiếp.

### BR-10 — Dữ liệu và quyền riêng tư

- Raw GPS là immutable.
- Cleaned và matched coordinates lưu riêng.
- Dashboard tổng hợp không trả raw GPS nếu người dùng không có quyền.
- Truy cập route chi tiết phải có audit log.
- Retention và anonymization phải cấu hình theo chính sách doanh nghiệp.

---

## 6. Kiến trúc mục tiêu

```text
GPS Client
    |
    v
FastAPI Ingestion API
    |
    +--> PostgreSQL/PostGIS (system of record)
    |
    +--> Redis Streams (durable processing queue)
              |
              +--> Cleaning/Window Worker
              |
              +--> OSRM Match Worker
              |
              +--> Trip Finalization Worker
              |
              +--> Bypass + H3 Aggregation Worker

React Dashboard --> Query API --> PostgreSQL aggregates/cache
                                --> Redis query cache (chỉ khi cần)
```

### Vai trò Redis

- Redis Streams được dùng làm queue xử lý bất đồng bộ trong phạm vi dự án.
- PostgreSQL/PostGIS vẫn là system of record.
- Redis query cache là tùy chọn và chỉ bật sau profiling.
- Không có dữ liệu duy nhất chỉ tồn tại trong Redis.

### Backpressure và lỗi

- Giới hạn concurrency của OSRM worker độc lập với ingestion rate.
- Retry với exponential backoff và jitter.
- Sự kiện lỗi vĩnh viễn đi vào dead-letter stream.
- Khi OSRM lỗi, ingestion vẫn nhận và lưu GPS để xử lý bù.

---

## 7. Tech stack đã chốt

| Layer             | Công nghệ                               |
| ----------------- | --------------------------------------- |
| Frontend          | React, TypeScript, Vite                 |
| State/server data | TanStack Query                          |
| Map               | MapLibre GL JS và Deck.gl H3 layer      |
| Backend           | Python 3.12, FastAPI, Pydantic          |
| ORM/Migration     | SQLAlchemy 2, GeoAlchemy2, Alembic      |
| Database          | PostgreSQL 16, PostGIS 3.4+             |
| Queue/cache       | Redis 7, Redis Streams                  |
| Routing/matching  | OSRM self-hosted, OSM snapshot được pin |
| Spatial grid      | H3, resolution khởi đầu 9–12            |
| Backend test      | pytest                                  |
| Frontend test     | Vitest, Testing Library                 |
| Load test         | k6                                      |
| Packaging         | Docker Compose                          |
| CI                | GitHub Actions                          |

Không thay đổi framework chính trong 6 tuần nếu chưa có ADR được cả nhóm duyệt.

---

## 8. Data model logic

Schema chi tiết phải được triển khai bằng Alembic. Các bảng tối thiểu:

### 8.1. `drivers`

```text
id UUID PK
external_id TEXT UNIQUE
display_name TEXT
status TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### 8.2. `trips`

```text
id UUID PK
external_id TEXT UNIQUE
driver_id UUID FK
status TEXT
started_at TIMESTAMPTZ
ended_at TIMESTAMPTZ NULL
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### 8.3. `planned_routes`

```text
id UUID PK
trip_id UUID FK
route_version TEXT
routing_data_version TEXT
route_source TEXT
geom geometry(LineString, 4326)
ordered_edge_ids JSONB hoặc bảng con chuẩn hóa
valid_from TIMESTAMPTZ
valid_to TIMESTAMPTZ NULL
created_at TIMESTAMPTZ
UNIQUE(trip_id, route_version)
```

### 8.4. `gps_events`

```text
id BIGINT PK
event_id UUID UNIQUE
trip_id UUID FK
driver_id UUID FK
sequence_no BIGINT
recorded_at TIMESTAMPTZ
received_at TIMESTAMPTZ
raw_geom geometry(Point, 4326)
accuracy_m DOUBLE PRECISION
speed_kmh DOUBLE PRECISION
heading DOUBLE PRECISION
payload_metadata JSONB
UNIQUE(trip_id, sequence_no)
```

Index tối thiểu:

- B-tree `(trip_id, sequence_no)`
- B-tree `(driver_id, recorded_at)`
- BRIN hoặc B-tree `recorded_at`, chọn theo benchmark
- GiST `raw_geom`

### 8.5. `matched_segments`

```text
id UUID PK
trip_id UUID FK
segment_no INTEGER
result_state TEXT               -- provisional/final
routing_data_version TEXT
algorithm_version TEXT
confidence DOUBLE PRECISION
geom geometry(LineString, 4326)
ordered_edge_ids JSONB hoặc bảng con chuẩn hóa
gap_before BOOLEAN
match_status TEXT
reason_code TEXT NULL
processed_at TIMESTAMPTZ
```

### 8.6. `trip_bypass_segments`

```text
id UUID PK
trip_id UUID FK
planned_route_id UUID FK
matched_segment_id UUID FK
result_state TEXT
detection_method TEXT
algorithm_version TEXT
threshold_config_version TEXT
routing_data_version TEXT
confidence DOUBLE PRECISION
missing_length_m DOUBLE PRECISION
average_deviation_distance_m DOUBLE PRECISION
geom geometry(LineString, 4326)
reason_code TEXT NULL
created_at TIMESTAMPTZ
```

### 8.7. `trip_route_hexes`

Lưu planned eligible hex và bypass hex đã deduplicate:

```text
trip_id UUID FK
planned_route_id UUID FK
hex_id TEXT
h3_resolution SMALLINT
is_bypass BOOLEAN
algorithm_version TEXT
created_at TIMESTAMPTZ
PRIMARY KEY(
  trip_id,
  planned_route_id,
  hex_id,
  h3_resolution,
  algorithm_version
)
```

### 8.8. `h3_aggregates`

Là bảng materialized tùy chọn, không phải nguồn sự thật:

```text
bucket_start TIMESTAMPTZ
bucket_size TEXT
hex_id TEXT
h3_resolution SMALLINT
eligible_trip_count BIGINT
bypass_trip_count BIGINT
unique_driver_count BIGINT
bypass_unique_driver_count BIGINT
average_deviation_distance_m DOUBLE PRECISION
algorithm_version TEXT
refreshed_at TIMESTAMPTZ
```

Không đặt cột H3 deviation trên từng GPS point để tránh quay lại cách đếm point-level.

---

## 9. GPS processing và map matching

### 9.1. Cleaning rules ban đầu

- Loại hoặc gắn cờ điểm có `accuracy_m > 30`.
- Gắn cờ vận tốc suy ra bất khả thi; ngưỡng khởi đầu `120 km/h`.
- Không hard-code threshold trong service.
- Moving Average/Kalman chỉ áp dụng trên cleaned view, không sửa raw GPS.

### 9.2. Windowing

- Gom 30–100 điểm mỗi trip.
- Flush sau 10–30 giây nếu chưa đủ điểm.
- Overlap 5–10 điểm giữa hai window.
- Chấp nhận reorder trong cửa sổ cấu hình 5–15 giây.
- OSRM request có giới hạn số điểm và concurrency.

### 9.3. GPS gap khởi đầu

- `<15 giây`: có thể tiếp tục cùng segment nếu vận tốc/khoảng cách hợp lý.
- `15–120 giây`: thử match nhưng gắn cờ gap và yêu cầu confidence cao.
- `>120 giây` hoặc di chuyển bất khả thi: tách segment.

Đây là giá trị khởi đầu, phải hiệu chỉnh bằng dữ liệu gán nhãn.

---

## 10. API contract tối thiểu

### System

- `GET /api/v1/health`
- `GET /api/v1/health/ready`
- `GET /api/v1/version`

### Ingestion

- `POST /api/v1/gps/events`
- `POST /api/v1/gps/events/batch`

Ingestion trả ACK sau khi event đã được lưu bền vững/ghi queue, không chờ OSRM.

### Trips

- `POST /api/v1/trips`
- `POST /api/v1/trips/{trip_id}/planned-routes`
- `POST /api/v1/trips/{trip_id}/complete`
- `GET /api/v1/trips`
- `GET /api/v1/trips/{trip_id}`
- `GET /api/v1/trips/{trip_id}/route-comparison`

### Heatmap

- `GET /api/v1/heatmap?start_time=&end_time=&driver_id=&resolution=`
- `GET /api/v1/heatmap/{hex_id}/details?start_time=&end_time=&driver_id=&resolution=`

Heatmap trả GeoJSON `FeatureCollection`. Khi không có dữ liệu:

```json
{
  "type": "FeatureCollection",
  "features": []
}
```

Mỗi feature có tối thiểu:

```json
{
  "hex_id": "8928308280fffff",
  "eligible_trip_count": 100,
  "bypass_trip_count": 30,
  "bypass_rate": 0.3,
  "unique_driver_count": 80,
  "bypass_unique_driver_count": 24,
  "average_deviation_distance": 68.4,
  "heat_weight": 30,
  "display_weight": 3.433,
  "h3_resolution": 9,
  "algorithm_version": "v1"
}
```

Tất cả list endpoint phải có giới hạn, pagination hoặc time-range bắt buộc.

---

## 11. Dashboard

Dashboard tối thiểu gồm:

- Map H3 polygon có thể audit.
- Heat blur overview dùng cùng `bypass_trip_count`.
- Bộ lọc thời gian, tài xế và H3 resolution.
- Legend dùng ngưỡng volume tuyệt đối.
- Tooltip hiển thị đầy đủ volume, rate, driver count và distance.
- Bật/tắt planned route và actual route độc lập.
- Trip detail hiển thị GPS gap, confidence và detection method.
- Loading, empty và error state rõ ràng.
- Không tải raw GPS cho màn hình tổng hợp.
  Mục tiêu tương tác dashboard: filter hợp lệ cập nhật trong dưới 2 giây; API p95 vẫn tuân theo mục 14.

---

## 12. Dữ liệu mẫu và đánh giá thuật toán

### Demo profile

- Tối thiểu 50.000 GPS point.
- Deterministic và idempotent.
- Chạy offline, không phụ thuộc routing API công cộng.
- Có normal route, true bypass, GPS noise, parallel road, bridge/tunnel và GPS gap.

### Benchmark profile

- Tối thiểu 1 triệu GPS point.
- Có đủ driver, trip và time bucket.
- Tỷ lệ read/write gần với workload chuẩn.
- Seed tái lập bằng random seed cố định.

### Labeled evaluation set

Đo precision/recall trên tập riêng, không dùng chính training/tuning fixtures. Báo cáo phải tách:

- GPS tốt và GPS xấu.
- Đường song song.
- Cầu/hầm.
- Gap ngắn/dài.
- Routing version mismatch.
- Geometry fallback.

Chỉ công bố độ chính xác trên 90% khi dataset, ground truth và script đánh giá được lưu phiên bản.

---

## 13. Testing và chất lượng

### Test bắt buộc

- 1/1, 9/10, 30/100 và 100/10.000.
- Một trip có nhiều GPS point trong cùng hex.
- Nhiều trip của cùng một tài xế.
- Planned/actual cùng corridor nhưng khác H3.
- Actual thực sự đi đường khác.
- Đường song song, cầu và hầm.
- Low confidence.
- GPS gap.
- Routing version mismatch.
- Planned route thay đổi giữa chuyến.
- Filter driver/time/resolution.
- Retry ingestion không tạo event trùng.
- Empty FeatureCollection.
- Finalization chạy lại không đếm trùng.

### Quality gate

- Ruff format/lint pass.
- mypy pass cho backend application code.
- ESLint, Prettier và TypeScript check pass.
- Unit/integration test pass.
- Coverage logic cốt lõi tối thiểu 80%.
- Alembic upgrade từ database trống và downgrade gần nhất hoạt động.
- Không có secret, dữ liệu GPS thật hoặc đường dẫn máy cá nhân.

---

## 14. SLO và mục tiêu 1.000 req/s

### Điều kiện nghiệm thu

- Throughput duy trì: **≥1.000 req/s trong ít nhất 15 phút**.
- Warm-up: 2 phút.
- Error rate: `<1%`.
- Ingestion ACK: `p95 <200 ms`.
- API read: `p95 <500 ms`.
- Không mất event đã ACK.
- Queue lag phải trở về ngưỡng bình thường sau khi dừng tải.

### Workload k6 chuẩn

| Tỷ trọng | Request                                       |
| -------: | --------------------------------------------- |
|      50% | GPS event ingestion với event mới/idempotency |
|      30% | Heatmap query theo time range và resolution   |
|      10% | Heatmap filter theo driver                    |
|      10% | Trip/route detail                             |

Không được dùng riêng health check, response tĩnh, mock repository, dữ liệu rỗng hoặc chỉ warm-cache để tuyên bố đạt mục tiêu.

### Báo cáo benchmark

Phải ghi:

- Commit SHA.
- Cấu hình máy và mạng.
- Số API instance, worker và OSRM instance.
- Database size, connection pool và cache state.
- Dataset/seed version.
- Test duration và virtual users.
- Throughput, p50, p95, p99 và error rate.
- CPU, RAM, DB connections, queue lag và OSRM latency.
- Cold-cache và warm-cache riêng.
- Kết quả theo từng nhóm endpoint, không chỉ số tổng hợp.

---

## 15. Observability, security và retention

### Metrics

- Ingestion rate/error/duplicate.
- Queue lag và dead-letter count.
- OSRM latency/error/unmatched.
- Low-confidence và GPS-gap ratio.
- Finalization lag.
- Heatmap API latency/cache hit.
- Database connections và slow queries.

### Logging

- Structured log.
- Request/correlation ID xuyên ingestion và worker.
- Không log secret hoặc raw GPS ngoài nhu cầu điều tra được kiểm soát.

### Security

- Secret qua environment/secret manager, không commit.
- Validate range của latitude, longitude, time và batch size.
- Rate limit/quota theo client khi đưa ra môi trường thật.
- RBAC tối thiểu cho aggregate view và trip-detail view.
- Audit log cho truy cập dữ liệu hành trình.

### Retention

Phải có cấu hình riêng cho:

- Raw GPS.
- Cleaned/matched trace.
- Bypass results.
- H3 aggregates.
- Application/audit logs.

---

## 16. Phân công nhóm 3 người

### Thành viên A — Backend và API

- FastAPI foundation.
- API contract, validation và error handling.
- Trip lifecycle và ingestion endpoints.
- Query API và backend tests.

### Thành viên B — GIS, database và algorithm

- PostGIS schema và Alembic.
- GPS cleaning, OSRM matching.
- Ordered edge comparison, corridor confirmation và H3.
- Spatial correctness/evaluation tests.

### Thành viên C — Frontend, platform và performance

- React/MapLibre/Deck.gl dashboard.
- Docker Compose và CI.
- Redis Streams, observability.
- k6 test và performance report.

Ownership không tạo silo. Mỗi PR cần ít nhất một người khác review. API contract, migration, Docker Compose và business rule cần review chéo.

---

## 17. Roadmap 6 tuần

| Tuần | Mục tiêu                  | Kết quả nghiệm thu                                                                                    |
| ---- | ------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1    | Foundation và contract    | Repo chạy bằng Docker Compose; PostGIS/Redis/OSRM health; migration; CI; API skeleton; demo seed v1   |
| 2    | Vertical slice offline    | Một trip đi từ planned route + GPS → match → bypass → H3 → GeoJSON → dashboard                        |
| 3    | Ingestion và finalization | Idempotent events, Redis Streams, window worker, GPS gap, provisional/final                           |
| 4    | Correctness và dashboard  | Road-edge/corridor logic, filters, trip audit view, labeled tests và semantics pass                   |
| 5    | Scale và hardening        | Dataset ≥1 triệu, index/profile, optional query cache/pre-aggregation, observability, security cơ bản |
| 6    | Nghiệm thu                | ≥1.000 req/s, SLO pass, regression test, tài liệu, demo và báo cáo tái lập                            |

Mỗi tuần phải có một increment chạy end-to-end. Không để đến tuần cuối mới tích hợp frontend, backend và GIS.

---

## 18. Definition of Done

Một task chỉ hoàn thành khi:

- Đúng business rule và acceptance criteria.
- Có test phù hợp.
- Lint, type-check và test pass.
- Migration được kiểm tra nếu có.
- API/docs được cập nhật nếu contract thay đổi.
- Metrics/log cần thiết đã có.
- Không chứa secret hoặc dữ liệu cá nhân.
- Được ít nhất một thành viên khác review.

Một milestone chỉ hoàn thành khi chạy được end-to-end trên môi trường sạch.

---

## 19. Acceptance criteria cuối cùng

1. `docker compose up --build` khởi động được frontend, backend, PostgreSQL/PostGIS, Redis và OSRM.
2. Migration chạy được từ database trống.
3. GPS retry không tạo dữ liệu trùng và event đã ACK không bị mất.
4. Raw GPS không bị ghi đè bởi dữ liệu clean/matched.
5. Bypass được xác định theo ordered road-edge, confidence, version và corridor rules.
6. GPS gap, low confidence và routing mismatch không tạo false bypass chính thức.
7. Một trip chỉ được tính một lần trong cùng hex/resolution.
8. Heatmap dùng `bypass_trip_count`; tooltip có volume và rate.
9. Filter tính lại đúng toàn bộ metric.
10. API không có dữ liệu trả FeatureCollection rỗng.
11. Có thể truy từ hex về trip, route và algorithm version.
12. Dashboard có H3, blur, filter và route comparison.
13. Test semantics, integration và spatial correctness pass.
14. Coverage logic cốt lõi đạt ít nhất 80%.
15. Duy trì ≥1.000 req/s trong 15 phút với error rate `<1%`.
16. Ingestion ACK p95 `<200 ms`, API read p95 `<500 ms`.
17. Báo cáo benchmark và accuracy có thể tái lập.
18. README cho phép thành viên mới setup mà không cần hướng dẫn ngoài.

---

## 20. Rủi ro chính và biện pháp

| Rủi ro                                   | Biện pháp                                                                 |
| ---------------------------------------- | ------------------------------------------------------------------------- |
| OSRM edge identity thay đổi theo dataset | Pin OSM snapshot, lưu `routing_data_version`, không so chéo version       |
| GPS urban canyon tạo false deviation     | Accuracy filter, window matching, confidence gate, corridor check         |
| GPS gap bị hiểu là bypass                | Tách segment, reason code, chỉ final đủ quan sát mới aggregate            |
| 1.000 req/s gây nghẽn DB/OSRM            | ACK bất đồng bộ, backpressure, index, pre-aggregation/cache sau profiling |
| Một tài xế làm nóng cả vùng              | Hiển thị `bypass_unique_driver_count` cùng trip volume                    |
| Scope quá lớn cho 3 người                | Vertical slice sớm, tech stack cố định, không thêm hạ tầng ngoài phạm vi  |
| Kết quả không tái lập                    | Version algorithm/config/data, immutable raw data, deterministic seed     |
