# IUH LMS Blog Bot

Bot theo dõi blog cá nhân trên LMS IUH, phát hiện mẫu kích hoạt trong bài viết, gửi nội dung câu hỏi đến AI và đăng câu trả lời dưới dạng comment.

## 1. Chạy bot

Chạy file:

```text
START_BOT.bat
```

File BAT sẽ:

1. Kiểm tra thư mục `.venv`.
2. Nếu chưa có thì tự tạo môi trường Python riêng.
3. Kiểm tra/cài Playwright và Groq SDK trong `.venv`.
4. Chạy `lms_blog_bot.py`.

Không cài package vào Python global.

---

## 2. File cấu hình

Toàn bộ cấu hình nằm trong:

```text
config.json
```

Ví dụ:

```json
{
  "lms_base_url": "https://lms.iuh.edu.vn",
  "username": "...",
  "password": "...",
  "provider": "groq",
  "groq_api_key": "...",
  "ai_model": "",
  "detect_pattern": "@bot",
  "default_system_prompt": "Trả lời đúng trọng tâm câu hỏi, rõ ràng, tự nhiên và hữu ích. Không nhắc đến mẫu kích hoạt hoặc việc bạn là bot. không dùng latex hay markdown mà chỉ trả lời kiểu text",
  "poll_interval_seconds": 6,
  "max_posts_per_scan": 10,
  "max_answer_length": 6000,
  "retry_count": 2,
  "retry_delay_seconds": 2,
  "cooldown_seconds": 0,
  "only_new_posts": true,
  "trigger_position": "title",
  "debug": true,
  "headless": true,
  "commands": {
    "#short": {
      "system_prompt": "Trả lời thật ngắn gọn, chỉ nêu ý chính cần thiết. Không nhắc đến lệnh kích hoạt hoặc việc bạn là bot."
    },
    "#code": {
      "system_prompt": "Ưu tiên giải thích theo hướng lập trình. Nếu phù hợp, đưa ra code hoàn chỉnh, dễ đọc, kèm giải thích ngắn về ý tưởng và độ phức tạp. Không nhắc đến lệnh kích hoạt hoặc việc bạn là bot."
    },
	"#nocmt": {
      "system_prompt": "Nếu trả lời code thì không có phần giải thích kiểu cmt, chỉ đưa ra câu trả lời trực tiếp. Không nhắc đến lệnh kích hoạt hoặc việc bạn là bot."
    }
  }
}
```

---

## 3. Các option

### `lms_base_url`

Địa chỉ gốc của LMS.

```json
"lms_base_url": "https://lms.iuh.edu.vn"
```

Thông thường không cần đổi.

---

### `username`

Tài khoản đăng nhập LMS.

```json
"username": "..."
```

Bot dùng tài khoản này để tự đăng nhập.

---

### `password`

Mật khẩu LMS.

```json
"password": "..."
```

Không chia sẻ file `config.json` vì file này chứa thông tin đăng nhập.

---

### `provider`

Nhà cung cấp AI.

Hiện tại bot hỗ trợ:

```json
"provider": "groq"
```

---

### `groq_api_key`

API key của Groq.

```json
"groq_api_key": "gsk_..."
```

Không đưa API key lên GitHub hoặc gửi cho người khác.

---

### `ai_model`

Model AI dùng để trả lời.

Nếu để trống:

```json
"ai_model": ""
```

bot mặc định dùng:

```text
openai/gpt-oss-120b
```

Có thể nhập model khác nếu Groq hỗ trợ.

---

### `detect_pattern`

Mẫu kích hoạt chính của bot.

Ví dụ:

```json
"detect_pattern": "#bot"
```

Khi đó bài viết:

```text
#bot
Giải thích Dijkstra cho tôi.
```

sẽ được bot xử lý.

Có thể đổi thành:

```json
"detect_pattern": "[[BOT]]"
```

hoặc:

```json
"detect_pattern": "@ai"
```

Sau khi đổi config nên restart bot.

---

### `default_system_prompt`

System prompt mặc định.

Nó được dùng khi bài chỉ có `detect_pattern`, không có command phụ.

Ví dụ:

```text
#bot
Giải thích Dijkstra cho tôi.
```

Bot sẽ dùng:

```json
"default_system_prompt": "..."
```

---

### `commands`

Các lệnh phụ để thay đổi system prompt.

Ví dụ:

```json
"commands": {
  "#short": {
    "system_prompt": "Trả lời thật ngắn gọn."
  },
  "#code": {
    "system_prompt": "Ưu tiên trả lời theo hướng lập trình."
  }
}
```

Ví dụ dùng:

```text
#bot
#short
Giải thích Dijkstra.
```

Bot sẽ dùng system prompt của `#short`.

Ví dụ:

```text
#bot
#code
Viết Dijkstra bằng C++.
```

Bot sẽ dùng system prompt của `#code`.

Nếu không có command phụ:

```text
#bot
Giải thích Dijkstra.
```

bot dùng `default_system_prompt`.

Có thể tự thêm command mới:

```json
"#math": {
  "system_prompt": "Giải bài toán từng bước, ưu tiên công thức và lập luận toán học."
}
```

---

### `trigger_position`

Quy định bot tìm `detect_pattern` ở đâu.

Có 3 giá trị:

```text
content
title
both
```

Ví dụ:

```json
"trigger_position": "content"
```

Ý nghĩa:

- `content`: chỉ tìm trong nội dung bài.
- `title`: chỉ tìm trong tiêu đề.
- `both`: tìm cả tiêu đề và nội dung.

Khuyến nghị:

```json
"trigger_position": "content"
```

---

### `poll_interval_seconds`

Khoảng thời gian giữa hai lần bot kiểm tra LMS.

Ví dụ:

```json
"poll_interval_seconds": 5
```

Nghĩa là cứ 5 giây bot kiểm tra lại một lần.

Bot hiện giới hạn tối thiểu khoảng 2 giây.

Không nên đặt quá thấp để tránh gửi request quá dày đến LMS.

---

### `max_posts_per_scan`

Số bài tối đa bot kiểm tra trong mỗi vòng quét.

```json
"max_posts_per_scan": 10
```

Thông thường để 10 là đủ.

---

### `max_answer_length`

Giới hạn số ký tự tối đa của câu trả lời AI trước khi comment.

```json
"max_answer_length": 6000
```

Ví dụ muốn câu trả lời ngắn hơn:

```json
"max_answer_length": 2000
```

---

### `retry_count`

Số lần thử lại khi gọi AI bị lỗi.

```json
"retry_count": 2
```

Ví dụ request đầu tiên lỗi, bot có thể thử thêm 2 lần.

---

### `retry_delay_seconds`

Thời gian chờ giữa các lần retry API.

```json
"retry_delay_seconds": 2
```

Nghĩa là chờ 2 giây trước khi thử lại.

---

### `cooldown_seconds`

Thời gian nghỉ thêm sau khi bot vừa trả lời thành công một bài.

```json
"cooldown_seconds": 0
```

Nếu đặt:

```json
"cooldown_seconds": 3
```

bot sẽ nghỉ thêm 3 giây sau mỗi comment thành công.

---

### `only_new_posts`

Quy định bot có bỏ qua các bài đã tồn tại trước lúc bot khởi động hay không.

```json
"only_new_posts": false
```

- `false`: bot vẫn có thể xử lý bài cũ nếu chưa có trong `processed.json`.
- `true`: khi vừa bật bot, các bài hiện có sẽ được đánh dấu bỏ qua; bot chỉ xử lý bài xuất hiện sau đó.

Khi test nên để:

```json
"only_new_posts": false
```

---

### `debug`

Bật log chi tiết.

```json
"debug": false
```

Khi cần tìm lỗi:

```json
"debug": true
```

Sau khi bot chạy ổn định có thể để lại `false`.

---

### `headless`

Quy định có hiện cửa sổ Chrome/Edge hay không.

```json
"headless": false
```

- `false`: hiện trình duyệt.
- `true`: chạy trình duyệt ẩn.

Trong giai đoạn test nên dùng:

```json
"headless": false
```

Khi bot đã ổn định có thể thử `true`.

---

## 4. Bot xác định blog của ai?

Không cần cấu hình `userid` thủ công.

Sau khi đăng nhập, bot tìm URL Profile của tài khoản đang đăng nhập, lấy:

```text
?id=XXXX
```

sau đó tự tạo URL blog:

```text
https://lms.iuh.edu.vn/blog/index.php?userid=XXXX
```

Vì vậy nếu đổi tài khoản LMS trong `config.json`, bot sẽ tự theo blog của tài khoản mới.

---

## 5. processed.json

File:

```text
processed.json
```

lưu ID các bài đã được bot xử lý thành công.

Mục đích là tránh bot comment lặp lại cùng một bài.

Nếu muốn test lại một bài cũ, có thể chạy:

```text
RESET_PROCESSED.bat
```

Sau đó restart bot.

---

## 6. Ví dụ sử dụng

### Trả lời mặc định

Bài đăng:

```text
#bot
Dijkstra hoạt động như thế nào?
```

Bot:

1. Phát hiện `#bot`.
2. Lấy phần sau `#bot` làm câu hỏi.
3. Dùng `default_system_prompt`.
4. Gọi Groq.
5. Comment câu trả lời.

### Trả lời ngắn

```text
#bot
#short
Dijkstra là gì?
```

Bot dùng system prompt của `#short`.

### Trả lời code

```text
#bot
#code
Viết Dijkstra bằng C++.
```

Bot dùng system prompt của `#code`.

---

## 7. Log khi chạy

Khi khởi động, bot sẽ hiện tương tự:

```text
=== IUH LMS BLOG BOT ===
Mau kich hoat: '#bot'; scan moi 5s
Lenh phu: #short, #code
AI provider: groq; model: openai/gpt-oss-120b
```

Nếu thấy:

```text
Phat hien '#bot' o entry ...
```

nghĩa là bot đã nhận được mẫu kích hoạt.

---

## 8. Lưu ý bảo mật

`config.json` hiện chứa:

- tài khoản LMS;
- mật khẩu LMS;
- Groq API key.

Không:

- upload `config.json` lên GitHub công khai;
- gửi file cho người khác;
- chụp màn hình phần API key/mật khẩu rồi đăng công khai.

Nếu sau này đưa project lên Git, nên thêm `config.json` vào `.gitignore`.
