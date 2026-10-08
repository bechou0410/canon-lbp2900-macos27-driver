# Cài, cấu hình và gỡ patch

Tài liệu này mô tả **patch-only 0.1.0**. Với bộ cài tích hợp runtime riêng, xem [driver LBP2900/2900B CAPT](standalone-capt.md).

Đây là bản thử nghiệm. Xem [trạng thái nghiệm thu](native-capt-acceptance.md) trước khi dùng thay queue đang hoạt động. Build và test trong repository không tự cài hệ thống.

## Chuẩn bị

1. Chạy `python3 tools/capt-project.py build` tại thư mục project.
2. Mở `artifacts/canon-source/LICENSE-CAPT-UK.rtf`, rồi cài `artifacts/canon-source/MacOSX/Canon_CAPT_Installer.pkg` bằng Installer của macOS. Đây là bộ gốc có chữ ký/notarization của Canon.
3. Nếu từng dùng patch cũ tắt BackGrounder, khôi phục dịch vụ đó trước. Patch mới báo lỗi và dừng nếu còn file `jp.co.canon.CUPSCAPT2.BG.plist.disabled-by-lbp2900-patcher`; không tự xóa dấu vết cấu hình cũ.
4. Cài `artifacts/Canon-LBP2900-CAPT-10.0.10-patch-0.1.0.pkg`. Script chỉ thêm monitor và PPD riêng, không tự tạo queue. PKG này chưa có chữ ký Developer ID/notarization.

Không tắt SIP/Gatekeeper. Với gói tự build đã kiểm tra, có thể cài bằng Terminal:

```sh
sudo installer -pkg artifacts/Canon-LBP2900-CAPT-10.0.10-patch-0.1.0.pkg -target /
```

## Tạo queue native

Cắm và bật LBP2900, lấy URI USB thực:

```sh
lpinfo -v
```

Dùng đúng URI được trả về, không dùng serial ví dụ:

```sh
sudo '/Library/Application Support/CanonLBP2900CAPTPatch/configure-native-queue' 'usb://Canon/LBP2900?serial=SERIAL_THUC_TE'
```

Lệnh tạo `Canon_LBP2900_CAPT`, sử dụng backend `cnbma2`, và bật/nạp Canon BackGrounder cho người đang đăng nhập desktop. Bước này xử lý cả dấu tắt dịch vụ `launchctl` còn sót từ patch cũ. Không đổi máy in mặc định và không sửa queue khác. Không gửi đồng thời job qua queue cũ và queue mới của cùng máy in. Nếu queue cũ có job, hoàn thành hoặc chủ động hủy chúng trước khi thử.

Kiểm tra:

```sh
lpstat -v Canon_LBP2900_CAPT
lpstat -p Canon_LBP2900_CAPT
open '/Library/Printers/Canon/CUPSCAPT2/StatusMonitor/StatusMonitor.app'
```

Mở Print Center của macOS, chọn **Canon LBP2900 CAPT** (device name `Canon_LBP2900_CAPT`). Tiện ích Canon vẫn dùng profile LBP3000 nội bộ; tên LBP3000 có thể xuất hiện trong cửa sổ utility. Chỉ đổi tên hiển thị không làm tăng khả năng phần cứng.

Trong hộp thoại in của ứng dụng, chọn **Canon LBP2900 CAPT** → **Printer Options** để mở Finishing, Paper Source và Quality. Quality Settings có Halftones, Toner Density và Use Toner Save; Color Settings có Brightness/Contrast. Bảng About hiển thị Version 10.0.10. Print Center có thể hiển thị Driver Version 10.0.2 vì đó là `FileVersion` của PPD gốc Canon, được giữ nguyên.

Print Center quản lý job trước khi chuyển sang CCPD. Trong phép thử thực, backend Canon kết thúc job CUPS ngay sau khi chuyển dữ liệu, kể cả lúc máy còn chờ giấy. Sau thời điểm đó, dùng **Canon CAPT Printer Utility** để xem trạng thái thực và hủy job. Có thể mở utility qua Print Center → Printer Info → Utility → Open Printer Utility. Không coi trạng thái completed của CUPS là bằng chứng đã ra giấy.

Khi in nhiều bản từ CLI, Canon đọc trường print ticket macOS. Ví dụ: `lp -d Canon_LBP2900_CAPT -n 2 -o com.apple.print.PrintSettings.PMCopies..n.=2 document.pdf`. Trong phép render độc lập bằng filter gốc, chỉ tăng đối số copies hoặc `copies=2` không đổi đầu ra, còn trường print ticket đổi đúng dữ liệu. Khuyến nghị dùng hộp thoại in của ứng dụng cho lựa chọn in thông thường.

Nếu tiến trình quản trị báo `Operation not permitted` khi đọc bộ cài trong Documents, chép bộ cài đã xác minh sang một thư mục tạm riêng dưới `/private/tmp`, kiểm tra lại checksum rồi cài từ đó. Không thay đổi SIP, Gatekeeper hay quyền riêng tư. Xóa bản sao tạm sau khi hoàn thành. Log lỗi script Installer nằm ở `/var/log/install.log`.

## Gỡ patch

Hoàn thành hoặc hủy các job của queue thử nghiệm bằng Print Center. Sau đó:

```sh
sudo lpadmin -x Canon_LBP2900_CAPT
sudo '/Library/Application Support/CanonLBP2900CAPTPatch/capt-patch' remove
```

Lệnh `remove` kiểm tra checksum trước khi xóa hai file patch đã thêm. Driver, tiện ích, dịch vụ Canon gốc, queue cũ và máy in khác được giữ nguyên. Các script/checksum nhỏ trong `Library/Application Support/CanonLBP2900CAPTPatch` vẫn còn để kiểm tra hoặc cài lại; đây không phải bộ gỡ toàn bộ driver Canon.

Nếu đã đổi tên queue thử nghiệm hoặc tạo thêm queue dùng PPD mới, xóa các queue đó trước khi gỡ. Không dùng bộ clean-uninstaller cũ của project vì bộ đó thuộc luồng triển khai trước.
