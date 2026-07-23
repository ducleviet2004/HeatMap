import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 2,
  duration: "10s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
  },
};

const baseUrl = __ENV.BASE_URL || "http://localhost:8000";

export default function () {
  const response = http.get(`${baseUrl}/api/v1/health`);
  check(response, {
    "health responds 200": (r) => r.status === 200,
    "health response is semantic": (r) => r.json("status") === "ok",
  });
  sleep(1);
}

