import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 20 },  // Warm up
    { duration: '1m', target: 50 },   // Sustained load
    { duration: '30s', target: 100 }, // Stress spike
    { duration: '30s', target: 0 },   // Cool down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must be < 500ms
    http_req_failed: ['rate<0.01'],   // Error rate < 1%
  },
};

export default function () {
  // TARGET: Change this to your local running instance
  let res = http.get('http://127.0.0.1:8000/admin/login/');
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'protocol security': (r) => r.headers['X-Frame-Options'] !== undefined
  });
  sleep(1);
}
