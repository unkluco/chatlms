# IUH LMS Blog Bot

Bot theo dõi Blog cá nhân trên LMS IUH, tìm bài có mẫu kích hoạt, gửi câu hỏi và nội dung file đính kèm sang AI Groq, sau đó đăng câu trả lời dưới dạng comment ngay trên LMS.

## Tính năng hiện tại

- Tự đăng nhập LMS bằng tài khoản trong `config.json`.
- Giữ session bằng profile riêng `.browser_profile`; nếu session còn sống thì dùng lại.
- Tự đăng nhập lại khi session hết hạn hoặc bị văng khỏi LMS.
- Tự reconnect và tạo lại browser khi mất mạng/browser lỗi; host không tự dừng vì một lỗi tạm thời.
- Tự xác định `userid` của tài khoản đang đăng nhập, không cần nhập ID Blog thủ công.
- Quét Blog theo chu kỳ và chỉ xử lý bài có mẫu kích hoạt.
- Hỗ trợ tìm mẫu kích hoạt trong tiêu đề, nội dung hoặc cả hai.
- Hỗ trợ lệnh phụ cấu hình được như `#short`, `#code`, `#nocmt`.
- Đọc file đính kèm: PDF, DOCX, XLSX, CSV và nhiều định dạng text/code.
- Giới hạn số file, dung lượng và lượng text trích xuất để tránh prompt quá lớn.
- Lưu `processed.json` để tránh comment lặp lại cùng bài.
- Chống chạy hai bot cùng tài khoản trên Windows bằng single-instance mutex.
- Chạy trong Windows Job Object: đóng cửa sổ launcher thì Python và browser của bot cũng dừng theo.
- Tự tạo `.venv` và tự cài dependency cần thiết khi chạy `START_BOT.bat`.

## Thay đổi gần đây

- Sửa logic nhận diện trạng thái đăng nhập: không còn nhầm trang `/login/index.php` là đã logout khi session thực tế vẫn còn.
- Thêm tự đăng nhập lại khi session hết và tự reconnect khi browser/mạng lỗi.
- Thêm đọc nội dung file đính kèm trực tiếp từ bài Blog.
- Thêm `in_progress` + single-instance mutex để giảm nguy cơ comment trùng.
- Thêm Windows Job Object để đóng launcher là dừng luôn Python và browser của bot.
- Sửa `only_new_posts` để baseline chỉ tạo một lần trong mỗi lần chạy, kể cả sau reconnect.

---

## 1. Cài đặt từ GitHub

```bash
git clone https://github.com/unkluco/chatlms.git
cd chatlms
```

Yêu cầu khuyến nghị:

- Windows 10/11.
- Python 3 đã cài trên máy.
- Google Chrome hoặc Microsoft Edge.
- Tài khoản LMS IUH hợp lệ.
- Groq API key.

Sau khi clone:

1. Tạo `config.json` trong thư mục project.
2. Điền tài khoản LMS, mật khẩu và Groq API key.
3. Chạy `START_BOT.bat`.
4. Lần đầu bot sẽ tự tạo `.venv` và cài thư viện cần thiết.

`config.json`, `.browser_profile`, `.attachments`, `processed.json` và `.venv` đều là dữ liệu local và đã được bỏ qua trong Git.

---

## 2. Chạy bot

Chạy:

```text
START_BOT.bat
```

Launcher hiện thực hiện các bước:

1. Kiểm tra `.venv`; nếu lỗi hoặc chưa có thì tự tạo lại.
2. Kiểm tra `pip`.
3. Cài/kiểm tra `playwright`.
4. Cài/kiểm tra `groq`.
5. Cài/kiểm tra `pypdf`, `python-docx`, `openpyxl`.
6. Gọi `RUN_BOT_JOB.ps1` để chạy bot trong Windows Job Object.

Khi đóng cửa sổ `START_BOT.bat`, Job Object sẽ dừng cả Python và browser con của bot, tránh tình trạng bot vẫn chạy ngầm.

---

## 3. Cấu hình đầy đủ

Ví dụ cấu hình đang phù hợp với phiên bản hiện tại:

```json
{
  "lms_base_url": "https://lms.iuh.edu.vn",
  "username": "YOUR_LMS_USERNAME",
  "password": "YOUR_LMS_PASSWORD",
  "provider": "groq",
  "groq_api_key": "gsk_...",
  "ai_model": "",
  "detect_pattern": "@bot",
  "trigger_position": "title",
  "default_system_prompt": "Trả lời đúng trọng tâm câu hỏi, rõ ràng, tự nhiên và hữu ích.",
  "poll_interval_seconds": 6,
  "max_posts_per_scan": 10,
  "max_answer_length": 6000,
  "retry_count": 2,
  "retry_delay_seconds": 2,
  "cooldown_seconds": 0,
  "only_new_posts": true,
  "debug": true,
  "headless": true,
  "reconnect_delay_seconds": 5,
  "login_retry_seconds": 5,
  "commands": {
    "#short": {
      "system_prompt": "Trả lời thật ngắn gọn, chỉ nêu ý chính cần thiết."
    },
    "#code": {
      "system_prompt": "Ưu tiên giải thích theo hướng lập trình và đưa code khi phù hợp."
    },
    "#nocmt": {
      "system_prompt": "Nếu trả lời code thì chỉ đưa câu trả lời trực tiếp, không thêm phần giải thích kiểu comment."
    }
  },
  "attachments": {
    "enabled": true,
    "max_file_size_mb": 15,
    "max_files_per_post": 3,
    "max_extracted_chars_per_file": 20000,
    "max_total_attachment_chars": 40000,
    "delete_after_processing": true
  }
}
```

### Các option chính

`lms_base_url`: URL gốc của LMS. Với IUH hiện dùng `https://lms.iuh.edu.vn`.

`username`, `password`: thông tin đăng nhập LMS. Bot dùng để tự đăng nhập và tự đăng nhập lại khi session hết.

`provider`: hiện code hỗ trợ `groq`.

`groq_api_key`: API key Groq. Không commit key lên GitHub.

`ai_model`: model Groq. Nếu để rỗng, bot mặc định dùng `openai/gpt-oss-120b`.

`detect_pattern`: chuỗi kích hoạt chính, ví dụ `@bot`.

`trigger_position` có 3 giá trị:

- `title`: tìm mẫu kích hoạt trong tiêu đề.
- `content`: tìm trong nội dung bài.
- `both`: tìm cả hai.

Nếu dùng `title`, phần nội dung sau mẫu kích hoạt trong tiêu đề sẽ được ghép với toàn bộ nội dung bài để làm prompt.

`poll_interval_seconds`: số giây giữa hai lần quét Blog. Code ép tối thiểu 2 giây.

`max_posts_per_scan`: số entry tối đa lấy trong mỗi vòng quét.

`max_answer_length`: giới hạn số ký tự của câu trả lời trước khi comment.

`retry_count`: số lần retry thêm khi gọi AI lỗi.

`retry_delay_seconds`: thời gian chờ giữa các lần retry AI.

`cooldown_seconds`: thời gian nghỉ thêm sau khi comment thành công.

`debug`: bật log chi tiết như URL profile được phát hiện và lỗi retry AI.

`headless`:

- `true`: browser chạy ẩn.
- `false`: hiện cửa sổ browser, phù hợp khi debug.

`reconnect_delay_seconds`: thời gian chờ trước khi bot tạo lại phiên browser sau lỗi kết nối/browser.

`login_retry_seconds`: thời gian chờ giữa các lần thử đăng nhập LMS.

---

## 4. Cơ chế đăng nhập và tự phục hồi

Bot dùng `.browser_profile` làm persistent browser profile.

Luồng hoạt động:

```text
Khởi động
  ↓
Mở Chrome → nếu lỗi thử Edge → nếu lỗi thử Chromium của Playwright
  ↓
Mở trang login LMS
  ↓
Có form username + password?
  ├─ Không → session vẫn còn → dùng tiếp
  └─ Có → tự điền config.json và đăng nhập
  ↓
Tự xác định userid
  ↓
Mở Blog và bắt đầu quét
```

Điểm quan trọng: bot **không còn kết luận logout chỉ vì URL chứa `/login/`**. Moodle có thể mở `/login/index.php` ngay cả khi người dùng đã đăng nhập. Bot chỉ xem là logout khi form `username` và `password` thực sự xuất hiện.

Nếu trong lúc chạy:

- Session LMS hết → bot tự đăng nhập lại và tiếp tục quét.
- Browser bị đóng/kết nối Playwright chết → bot tạo lại browser.
- Mạng/LMS lỗi tạm thời → bot giữ host sống, chờ `reconnect_delay_seconds` rồi thử lại.
- CAPTCHA/MFA xuất hiện hoặc giao diện LMS thay đổi lớn → có thể cần cập nhật code.

---

## 5. Mẫu kích hoạt và lệnh phụ

Ví dụ cấu hình:

```json
"detect_pattern": "@bot",
"trigger_position": "title"
```

Bạn có thể tạo tiêu đề:

```text
@bot #code
```

và nội dung bài:

```text
Viết Dijkstra bằng C++ và phân tích độ phức tạp.
```

Bot sẽ:

1. Phát hiện `@bot`.
2. Tìm lệnh phụ trong prompt.
3. Xóa tag lệnh phụ khỏi prompt.
4. Dùng `system_prompt` tương ứng.
5. Gọi Groq.
6. Comment câu trả lời lên bài.

Các lệnh phụ **không hard-code**; bạn có thể thêm/sửa/xóa trong object `commands` của `config.json`.

Nếu nhiều tag cùng xuất hiện, code hiện chọn một tag đầu tiên theo thứ tự ưu tiên nội bộ (tag dài hơn được xét trước). Nên dùng một lệnh phụ cho mỗi bài để hành vi rõ ràng.

---

## 6. Đọc file đính kèm

Bật bằng:

```json
"attachments": {
  "enabled": true,
  "max_file_size_mb": 15,
  "max_files_per_post": 3,
  "max_extracted_chars_per_file": 20000,
  "max_total_attachment_chars": 40000,
  "delete_after_processing": true
}
```

Bot chỉ lấy link file thuộc chính host LMS và nằm trong đường dẫn Moodle `pluginfile.php` hoặc `draftfile.php`.

Định dạng hỗ trợ:

- Tài liệu: `.pdf`, `.docx`.
- Bảng dữ liệu: `.xlsx`, `.csv`.
- Text/code: `.txt`, `.md`, `.py`, `.java`, `.c`, `.cpp`, `.h`, `.cs`, `.js`, `.ts`, `.tsx`, `.jsx`, `.html`, `.css`, `.json`, `.xml`, `.yaml`, `.yml`, `.sql`, `.sh`, `.bat`, `.ps1`, `.go`, `.rs`, `.php`, `.rb`, `.kt`, `.swift` và một số extension text tương tự.

Cách đọc:

- PDF: trích text theo từng trang.
- DOCX: đọc paragraph và bảng.
- XLSX: đọc giá trị của từng sheet.
- CSV: đọc theo hàng.
- Text/code: đọc trực tiếp với fallback encoding.

File được tải tạm vào:

```text
.attachments/<entry_id>/
```

Sau khi xử lý, nếu `delete_after_processing=true`, thư mục tạm của entry sẽ được xóa.

Giới hạn:

- Không OCR PDF scan/ảnh.
- Không phân tích ảnh đính kèm.
- Chưa hỗ trợ PPT/PPTX.
- File vượt `max_file_size_mb` sẽ bị bỏ qua.
- Tổng text file đưa vào AI bị giới hạn bởi `max_total_attachment_chars`.

Nếu tải file trả về HTML thay vì file thật, bot xem đó là dấu hiệu session có thể đã hết và kích hoạt quy trình đăng nhập lại.

---

## 7. Chống xử lý trùng

Bot có hai lớp bảo vệ:

### `processed.json`

Lưu `entryid` của các bài đã comment thành công. Khi quét lại, các entry này được bỏ qua.

Muốn test lại bài cũ:

```text
RESET_PROCESSED.bat
```

File này sẽ xóa `processed.json`.

### `in_progress`

Trong một phiên chạy, entry đang xử lý được giữ trong bộ nhớ để không bị chạy đồng thời/lặp do vòng quét.

### Single instance trên Windows

Bot tạo mutex dựa trên:

```text
lms_base_url + username
```

Nếu mở bot lần thứ hai với cùng tài khoản, instance mới sẽ tự dừng thay vì cùng comment vào một bài.

---

## 8. `only_new_posts`

Nếu:

```json
"only_new_posts": true
```

khi khởi động, bot lấy tối đa `max_posts_per_scan` bài đang có và đánh dấu chúng là đã biết. Sau đó chỉ bài mới xuất hiện mới được xử lý.

Mốc baseline này chỉ được tạo **một lần trong mỗi lần chạy bot**. Nếu mất mạng rồi reconnect, bot không tạo lại baseline nên không vô tình bỏ qua bài vừa xuất hiện.

Nếu muốn bot có thể xử lý bài cũ chưa có trong `processed.json`:

```json
"only_new_posts": false
```

---

## 9. AI / Groq

Hiện provider được hỗ trợ trong code là:

```json
"provider": "groq"
```

Nếu `ai_model` để trống, model mặc định là:

```text
openai/gpt-oss-120b
```

Bot gọi Groq với:

- `temperature=0.3`.
- `reasoning_effort="low"`.
- `include_reasoning=false`.
- Timeout SDK khoảng 90 giây.
- Số completion token được suy ra từ `max_answer_length` và giới hạn tối đa 4096.
- Câu trả lời cuối cùng bị cắt theo `max_answer_length`.

Groq:

- Console: https://console.groq.com/
- API Keys: https://console.groq.com/keys
- Docs: https://console.groq.com/docs/

---

## 10. Bot xác định Blog của ai?

Sau khi đăng nhập, bot tìm link profile dạng:

```text
/user/profile.php?id=XXXX
```

rồi lấy `XXXX` để tạo:

```text
https://lms.iuh.edu.vn/blog/index.php?userid=XXXX
```

Do đó không cần cấu hình `userid`. Nếu đổi tài khoản trong `config.json`, bot sẽ theo Blog của tài khoản mới.

---

## 11. Log khi chạy

Log bình thường có dạng:

```text
=== IUH LMS BLOG BOT ===
Mau kich hoat: '@bot'; scan moi 6s
Lenh phu: #short, #code, #nocmt
AI provider: groq; model: openai/gpt-oss-120b
Tu dong reconnect sau 5s neu mat ket noi.
File dinh kem: ON | toi da 3 file/bai | 15 MB/file
Mo trinh duyet chrome...
Da co phien dang nhap LMS.
Da xac dinh blog cua tai khoan dang nhap.
```

Khi phát hiện bài:

```text
Phat hien '@bot' o entry ...; mode=#code. Dang goi AI...
Entry ...: AI tra loi ... ky tu. Dang gui binh luan...
Entry ...: Da gui binh luan.
```

Khi session hết:

```text
Phien LMS da het/bi vang. Dang tu dong dang nhap lai...
Dang nhap lai thanh cong. Tiep tuc quet.
```

Khi browser/mạng lỗi:

```text
Can khoi tao lai phien browser.
Host van dang chay. Cho 5s roi ket noi lai...
```

---

## 12. Cấu trúc project

```text
lms_bot/
├─ lms_blog_bot.py       # Logic chính
├─ START_BOT.bat         # Launcher, tạo venv + dependency
├─ RUN_BOT_JOB.ps1       # Windows Job Object, quản lý process con
├─ RESET_PROCESSED.bat   # Xóa trạng thái bài đã xử lý
├─ config.json           # Secret/local config, không commit
├─ processed.json        # Runtime state, không commit
├─ .browser_profile/     # Cookie/session browser, không commit
├─ .attachments/         # File LMS tải tạm, không commit
├─ .venv/                # Python virtual environment
└─ README.md
```

---

## 13. Lưu ý bảo mật

`config.json` chứa:

- tài khoản LMS;
- mật khẩu LMS;
- Groq API key.

Không commit, upload hoặc gửi công khai file này.

Repository hiện đã ignore:

```text
config.json
auth.json
.env
.env.*
processed.json
.browser_profile/
.attachments/
.venv/
```

Nếu API key từng bị lộ ở nơi công khai, hãy revoke key cũ và tạo key mới.

---

## 14. Giới hạn hiện tại

- Chỉ có provider Groq.
- Selector phụ thuộc giao diện Moodle/LMS IUH hiện tại; LMS đổi UI có thể cần cập nhật.
- CAPTCHA/MFA không được tự vượt qua.
- Chưa xử lý ảnh và OCR.
- Chưa đọc PPT/PPTX.
- Bot comment qua UI của LMS; nếu chức năng comment bị tắt hoặc selector đổi, bot sẽ báo không tìm thấy ô/nút comment.
- `processed.json` chỉ ghi bài sau khi comment thành công; nếu AI hoặc comment lỗi, bài có thể được thử lại ở vòng quét sau.

---

## 15. Quy trình sử dụng gợi ý

1. Chạy `START_BOT.bat`.
2. Chờ log báo đã xác định Blog.
3. Tạo bài Blog theo `trigger_position`.
4. Thêm `@bot` và lệnh phụ nếu cần.
5. Đính kèm file nếu muốn AI đọc file.
6. Lưu bài.
7. Bot phát hiện → gọi AI → đăng comment.
8. Đóng cửa sổ launcher khi muốn dừng toàn bộ bot.
