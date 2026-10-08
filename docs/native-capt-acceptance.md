# Nghiệm thu đầy đủ tính năng

Tài liệu này mô tả **patch-only 0.1.0**. Với bộ cài tích hợp runtime riêng, xem [driver LBP2900/2900B CAPT](standalone-capt.md).

Mục tiêu do người dùng xác nhận: Canon LBP2900/2900B trên Apple Silicon/macOS 27.2, giữ Canon StatusMonitor/Printer Utility và Print Center. Ngày 2026-10-08 đã thử LBP2900 thật trên arm64/macOS 27.2 (26B5091g), với tối đa 4 tờ được người dùng cho phép. Người dùng xác nhận cả 4 tờ đúng nội dung, gồm một job 3 trang đúng thứ tự. Đây vẫn là bản thử nghiệm; **chưa chứng nhận mọi chức năng trong mọi tình huống**.

| Hạng mục | Kết quả / phần còn lại |
|---|---|
| Cài bộ gốc + patch | Đạt: Installer thành công, CCPD nạp `captmonlbp2900`, chữ ký và hash gốc hợp lệ |
| Utility | Đạt: mở trực tiếp và qua Print Center → Utility; trạng thái máy thay đổi đúng theo thao tác thật |
| In cơ bản | Đạt: 1 trang A4, người dùng xác nhận nội dung/bố cục đúng |
| Nhiều trang | Đạt: 3 trang A4, đủ và đúng thứ tự, Utility về Ready khi xong |
| Lựa chọn in | Mọi tùy chọn PPD/PDE được giữ. Đã mở bảng Finishing/Paper Source/Quality/Color Settings trong Preview; About xác nhận V10.0.10. Render thực đã kiểm A4/Letter, toner save/density/halftone/media, 2 copies qua print ticket macOS; output khớp driver gốc. Chưa đo từng lựa chọn trên giấy |
| Quản lý job | Đạt: Print Center pause/resume queue và hủy job còn chờ; Canon Utility pause/resume/cancel job sau khi chuyển sang CCPD; job tiếp theo in được |
| Hết giấy | Đạt: Utility báo Out of Paper, hủy được. Job sau tự tiếp tục khi nạp giấy, in đủ 3 trang. CUPS completed chỉ xác nhận bàn giao cho CCPD, không xác nhận giấy đã ra |
| Mở nắp / kẹt giấy | Mở nắp: đạt Top Cover Open và phục hồi khi đóng. Chưa kiểm tình huống kẹt giấy; không cố tạo kẹt giấy |
| Offline / reconnect | Đạt với rút/cắm USB: Communication Error → Ready, job tiếp theo in được. Chưa thử tắt/bật nguồn giữa job |
| Tiện ích máy in | Status và điều khiển job đã thử; menu Cleaning có mặt nhưng chưa chạy vì đã dùng đủ 4 tờ được phép |
| Khởi động lại | Đạt khi dừng rồi khởi động mới BackGrounder/CCPD/monitor: Utility tự về Ready. Chưa logout/reboot toàn máy hoặc in thêm sau restart dịch vụ |
| Rollback | Đạt trong integration test dùng payload thật: apply/reapply/remove, từ chối file sửa ngoài, phục hồi khi publish lỗi. Chưa gỡ hệ thống đang dùng |

LBP2900B là biến thể mục tiêu, chưa được xác nhận chỉ từ thiết bị LBP2900 hiện có. Các chức năng không có trên phần cứng (ví dụ duplex tự động, in màu) không thuộc lời hứa hỗ trợ.

Chi tiết: [báo cáo thực nghiệm](verification.md). Không thay cơ chế native bằng backend khác chỉ để Print Center giữ job lâu hơn; sau bước bàn giao, dùng Canon Utility để quản lý job thực.

Ghi kết quả từng mục, macOS/kiến trúc, thiết bị, tài liệu thử, quan sát bản in và log trong `plans/reports/`. Không đưa serial, dữ liệu bản in cá nhân hoặc log chưa kiểm tra vào commit công khai.
